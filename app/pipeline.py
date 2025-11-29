import os
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dronewq
from dronewq.utils.settings import Settings

mpl.use("Agg")  # non-interactive backend — no GUI windows will open


class Pipeline:
    """Interface for the whole workflow."""

    def __init__(self, settings: dict[str, str]) -> None:
        self.settings = Settings()
        folder_path = settings["main_dir"]
        if Path(folder_path).exists():
            self.settings = self.settings.configure(**settings)
        else:
            msg = f"{folder_path} does not exist."
            raise LookupError(msg)

    def water_metadata(self):
        dronewq.write_metadata_csv(
            self.settings.raw_water_dir,
            self.settings.main_dir,
        )

    def point_samples(self):
        if self.settings.mask_method:
            rrs_imgs = dronewq.load_imgs(
                img_dir=self.settings.masked_rrs_dir,
            )
            img_metadata = dronewq.load_metadata(
                img_dir=self.settings.masked_rrs_dir,
            )
        else:
            rrs_imgs = dronewq.load_imgs(
                img_dir=self.settings.rrs_dir,
            )
            img_metadata = dronewq.load_metadata(
                img_dir=self.settings.rrs_dir,
            )

        # Compute per-image median for first 5 bands (shape -> (n_images, 5))
        # We take median across spatial dims (H, W)
        medians = []
        for img in rrs_imgs:
            medians.append(np.nanmedian(img[:5, :, :], axis=(1, 2)))

        # Build dataframe safely and assign median band values
        df = img_metadata[["dirname", "Latitude", "Longitude"]].copy()
        df[["rrs_blue", "rrs_green", "rrs_red", "rrs_rededge", "rrs_nir"]] = medians

        out_path = Path(self.settings.main_dir) / "median_rrs.csv"
        df.to_csv(out_path, index=False)

    def flight_plan(self):
        output_folder = Path(self.settings.main_dir) / "result"
        Path(output_folder).mkdir(exist_ok=True)
        if not Path(self.settings.metadata).exists():
            msg = "Metadata file not found."
            raise FileNotFoundError(msg)

        img_metadata = pd.read_csv(self.settings.metadata)
        fig, ax = plt.subplots(1, 3, figsize=(10, 3), layout="tight")

        ax[0].plot(list(range(len(img_metadata))), img_metadata["Altitude"])
        ax[0].set_ylabel("Altitude (m)")

        ax[1].scatter(img_metadata["Longitude"], img_metadata["Latitude"])
        ax[1].set_ylabel("Latitude")
        ax[1].set_xlabel("Longitude")

        ax[2].plot(list(range(len(img_metadata))), img_metadata["Yaw"])
        ax[2].set_ylabel("Yaw")

        out_path = output_folder / "flight_plan.png"
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)

    def run(self):
        nir_threshold = self.settings.mask_args.get("nir_threshold", 0.01)
        green_threshold = self.settings.mask_args.get("green_threshold", 0.005)
        mask_std_factor = self.settings.mask_args.get("mask_std_factor", 1)
        dronewq.process_raw_to_rrs(
            output_csv_path=self.settings.main_dir,
            lw_method=self.settings.lw_method,
            ed_method=self.settings.ed_method,
            pixel_masking_method=self.settings.mask_method,
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            mask_std_factor=mask_std_factor,
            random_n=10,
            # NOTE: Should probably ask this from user
            clean_intermediates=False,
            overwrite_lt_lw=False,
            num_workers=4,
        )

    def wq_run(self):
        csv_path = Path(self.settings.main_dir) / "median_rrs_and_wq.csv"

        if not csv_path.exists():
            csv_path = Path(self.settings.main_dir) / "median_rrs.csv"

        df = pd.read_csv(csv_path)
        columns = df.columns.to_list()

        algs = {
            "chl_hu": dronewq.chl_hu,
            "chl_ocx": dronewq.chl_ocx,
            "chl_hu_ocx": dronewq.chl_hu_ocx,
            "chl_gitelson": dronewq.chl_gitelson,
            "tsm_nechad": dronewq.tsm_nechad,
        }

        # Filter to only algorithms not already in dataframe
        wq_algs_to_compute = [
            alg for alg in self.settings.wq_algs if alg not in columns
        ]

        if wq_algs_to_compute:
            if self.settings.mask_method:
                rrs_imgs = dronewq.load_imgs(
                    img_dir=self.settings.masked_rrs_dir,
                )
                rrs_dir = self.settings.masked_rrs_dir
            else:
                rrs_imgs = dronewq.load_imgs(
                    img_dir=self.settings.rrs_dir,
                )
                rrs_dir = self.settings.rrs_dir

            wq_results = defaultdict(list)

            for img in rrs_imgs:
                for wq_alg in wq_algs_to_compute:
                    result = algs[wq_alg](img)
                    results_array = np.array(result)
                    median = np.nanmedian(results_array, axis=(0, 1))
                    wq_results[wq_alg].append(median)

            # HACK: This could be more efficiently done.
            # For example, saving images in the loop above
            dronewq.save_wq_imgs(rrs_dir=rrs_dir, wq_algs=wq_algs_to_compute)

            for wq_alg in wq_results:
                results_array = np.array(wq_results[wq_alg])
                df[wq_alg] = results_array

        out_csv_path = Path(self.settings.main_dir) / "median_rrs_and_wq.csv"

        df.to_csv(out_csv_path)

    def plot_wq(self, plot_args: dict[str, dict]):
        output_folder = Path(self.settings.main_dir) / "result"

        colors = {
            "chl_hu": "Greens",
            "chl_ocx": "Greens",
            "chl_hu_ocx": "Greens",
            "chl_gitelson": "Greens",
            "tsm_nechad": "YlOrRd",
        }
        labels = {
            "chl_hu": "Chlorophyll a (mg $m^{-3}$)",
            "chl_ocx": "Chlorophyll a (mg $m^{-3}$)",
            "chl_hu_ocx": "Chlorophyll a (mg $m^{-3}$)",
            "chl_gitelson": "Chlorophyll a (mg $m^{-3}$)",
            "tsm_nechad": "TSM (mg/L)",
        }

        csv_path = Path(self.settings.main_dir) / "median_rrs_and_wq.csv"

        df = pd.read_csv(csv_path)
        for alg in plot_args:
            vmin = plot_args[alg]["vmin"]
            vmax = plot_args[alg]["vmax"]
            fig, ax = plt.subplots(1, 1, figsize=(4, 3), layout="tight")
            g = ax.scatter(
                df["Latitude"],
                df["Longitude"],
                c=df[alg],
                cmap=colors[alg],
                vmin=vmin,
                vmax=vmax,
            )

            cbar = fig.colorbar(g, ax=ax)
            cbar.set_label(labels[alg], rotation=270, labelpad=12)
            out_path = output_folder / (alg + "_plot.png")
            fig.savefig(
                out_path,
                dpi=300,
                bbox_inches="tight",
                transparent=False,
            )
            plt.close(fig)

    def plot_essentials(self, count: int = 25):
        self.rrs_plot(count=count)
        self.lt_plot(count=count)
        self.ed_plot(count=count)
        if self.settings.mask_method:
            self.masked_rrs_plot(count=count)

    def rrs_plot(self, count: int = 25):
        output_folder = Path(self.settings.main_dir) / "result"
        output_folder.mkdir(exist_ok=True)
        rrs_imgs_gen = dronewq.load_imgs(
            img_dir=self.settings.rrs_dir,
            count=count,
        )

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0, 1, count))

        total_mean = []
        for i, img in enumerate(rrs_imgs_gen):
            img_mean = np.nanmean(img[:5, :, :], axis=(1, 2))
            total_mean.append(img_mean)
            plt.plot(
                wv,
                img_mean,
                marker="o",
                color=colors[i],
                label="",
            )
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$R_{rs}\ (sr^{-1})$")
        plt.plot(
            wv,
            np.mean(total_mean, axis=0),
            marker="o",
            color="black",
            linewidth=5,
            label="Mean",
        )

        plt.legend(frameon=False)

        out_path = os.path.join(output_folder, "rrs_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)

    def lt_plot(self, count: int = 25):
        output_folder = os.path.join(self.settings.main_dir, "result")
        os.makedirs(output_folder, exist_ok=True)
        lt_imgs_gen = dronewq.load_imgs(
            img_dir=self.settings.lt_dir,
            count=count,
        )

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0, 1, count))

        total_mean = []
        for i, img in enumerate(lt_imgs_gen):
            img_mean = np.nanmean(img[0:5, :, :], axis=(1, 2))
            total_mean.append(img_mean)
            plt.plot(
                wv,
                img_mean,
                marker="o",
                color=colors[i],
                label="",
            )
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$L_{t}\ (mW\ cm^{-2}\ nm^{-1}\ sr^{-1})$")
        plt.plot(
            wv,
            np.mean(total_mean, axis=0),
            marker="o",
            color="black",
            linewidth=5,
            label="Mean",
        )

        plt.legend(frameon=False)

        out_path = os.path.join(output_folder, "lt_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)

    def ed_plot(self, count: int = 25):
        output_folder = os.path.join(self.settings.main_dir, "result")
        os.makedirs(output_folder, exist_ok=True)

        ed = pd.read_csv(self.settings.main_dir + "/dls_ed.csv")

        wv = [475, 560, 668, 717, 842]
        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        colors = plt.cm.viridis(np.linspace(0, 1, len(ed)))

        for i in range(len(ed)):
            plt.plot(wv, ed.iloc[i, 1:6], marker="o", color=colors[i])
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$E_d\ (mW\ m^2\ nm^{-1}$)")
        plt.plot(
            wv,
            ed.iloc[:, 1:6].mean(axis=0),
            marker="o",
            color="black",
            linewidth=5,
            label="Mean",
        )

        out_path = os.path.join(output_folder, "ed_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)

    def masked_rrs_plot(self, count: int = 25):
        output_folder = os.path.join(self.settings.main_dir, "result")
        os.makedirs(output_folder, exist_ok=True)
        masked_rrs_imgs_hedley = dronewq.load_imgs(
            img_dir=self.settings.masked_rrs_dir,
            count=count,
        )

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0, 1, count))

        total_mean = []
        for i, img in enumerate(masked_rrs_imgs_hedley):
            img_mean = np.nanmean(img[0:5, :, :], axis=(1, 2))
            total_mean.append(img_mean)

            plt.plot(
                wv,
                img_mean,
                marker="o",
                color=colors[i],
                label="",
            )
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$R_{rs}\ (sr^{-1})$")
        plt.plot(
            wv,
            np.mean(total_mean, axis=0),
            marker="o",
            color="black",
            linewidth=5,
            label="Mean",
        )

        plt.legend(frameon=False)

        out_path = os.path.join(output_folder, "masked_rrs_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)
