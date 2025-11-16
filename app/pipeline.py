import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import dronewq
from dronewq.utils.settings import Settings

matplotlib.use("Agg")  # non-interactive backend — no GUI windows will open


class Pipeline:
    def __init__(self, folder_path: str):
        self.settings = Settings()
        self.settings = self.settings.load(folder_path)

    def water_metadata(self):
        dronewq.write_metadata_csv(
            self.settings.raw_water_dir,
            self.settings.main_dir,
        )

    def point_samples_metadata(self):
        masked_rrs_imgs, img_metadata = dronewq.retrieve_imgs_and_metadata(
            img_dir=self.settings.masked_rrs_dir
        )

        if not isinstance(masked_rrs_imgs, np.ndarray):
            masked_rrs_imgs = np.stack(masked_rrs_imgs)

        # Compute per-image median for first 5 bands (shape -> (n_images, 5))
        # We take median across spatial dims (H, W)
        medians = np.nanmedian(masked_rrs_imgs[:, :5, :, :], axis=(2, 3))

        # Build dataframe safely and assign median band values
        df = img_metadata[["dirname", "Latitude", "Longitude"]].copy()
        df[["rrs_blue", "rrs_green", "rrs_red", "rrs_rededge", "rrs_nir"]] = medians

        out_path = os.path.join(self.settings.main_dir, "median_rrs.csv")
        df.to_csv(out_path, index=False)

    def flight_plan(self):
        output_folder = os.path.join(self.settings.main_dir, "result")
        os.makedirs(output_folder, exist_ok=True)
        if not os.path.exists(self.settings.metadata):
            raise FileNotFoundError("Metadata file not found.")

        img_metadata = pd.read_csv(self.settings.metadata)
        fig, ax = plt.subplots(1, 3, figsize=(10, 3), layout="tight")

        ax[0].plot(list(range(len(img_metadata))), img_metadata["Altitude"])
        ax[0].set_ylabel("Altitude (m)")

        ax[1].scatter(img_metadata["Longitude"], img_metadata["Latitude"])
        ax[1].set_ylabel("Latitude")
        ax[1].set_xlabel("Longitude")

        ax[2].plot(list(range(len(img_metadata))), img_metadata["Yaw"])
        ax[2].set_ylabel("Yaw")

        out_path = os.path.join(output_folder, "flight_plan.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)

    def run(self):
        mask_pixels = True if self.settings.mask_method else False
        dronewq.process_raw_to_rrs(
            lw_method=self.settings.lw_method,
            ed_method=self.settings.ed_method,
            mask_pixels=mask_pixels,
            pixel_masking_method=self.settings.mask_method,
            nir_threshold=0.02,
            random_n=10,
            # NOTE: Should probably ask this from user
            clean_intermediates=False,
            overwrite_lt_lw=False,
            num_workers=4,
        )

    def plot_essentials(self, count: int = 25):
        self.rrs_plot(count=count)
        self.lt_plot(count=count)
        self.ed_plot(count=count)
        self.masked_rrs_plot(count=count)

    def rrs_plot(self, count: int = 25):
        output_folder = os.path.join(self.settings.main_dir, "result")
        os.makedirs(output_folder, exist_ok=True)
        rrs_imgs, img_metadata = dronewq.retrieve_imgs_and_metadata(
            img_dir=self.settings.rrs_dir, count=count
        )

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0, 1, len(rrs_imgs)))

        for i in range(len(rrs_imgs)):
            plt.plot(
                wv,
                np.nanmean(rrs_imgs[i, 0:5, :, :], axis=(1, 2)),
                marker="o",
                color=colors[i],
                label="",
            )
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$R_{rs}\ (sr^{-1})$")
        plt.plot(
            wv,
            np.nanmean(rrs_imgs[:, 0:5, :, :], axis=(0, 2, 3)),
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
        lt_imgs, img_metadata = dronewq.retrieve_imgs_and_metadata(
            img_dir=self.settings.lt_dir, count=count
        )

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0, 1, len(lt_imgs)))

        for i in range(len(lt_imgs)):
            plt.plot(
                wv,
                np.nanmean(lt_imgs[i, 0:5, :, :], axis=(1, 2)),
                marker="o",
                color=colors[i],
                label="",
            )
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$L_{t}\ (mW\ cm^{-2}\ nm^{-1}\ sr^{-1})$")
        plt.plot(
            wv,
            np.nanmean(lt_imgs[:, 0:5, :, :], axis=(0, 2, 3)),
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
        masked_rrs_imgs_hedley, img_metadata = dronewq.retrieve_imgs_and_metadata(
            img_dir=self.settings.masked_rrs_dir, count=count
        )

        fig, ax = plt.subplots(1, 1, figsize=(6, 3))

        wv = [475, 560, 668, 717, 842]
        colors = plt.cm.viridis(np.linspace(0, 1, len(masked_rrs_imgs_hedley)))

        for i in range(len(masked_rrs_imgs_hedley)):
            plt.plot(
                wv,
                np.nanmean(masked_rrs_imgs_hedley[i, 0:5, :, :], axis=(1, 2)),
                marker="o",
                color=colors[i],
                label="",
            )
            plt.xlabel("Wavelength (nm)")
            plt.ylabel(r"$R_{rs}\ (sr^{-1})$")
        plt.plot(
            wv,
            np.nanmean(masked_rrs_imgs_hedley[:, 0:5, :, :], axis=(0, 2, 3)),
            marker="o",
            color="black",
            linewidth=5,
            label="Mean",
        )

        plt.legend(frameon=False)

        out_path = os.path.join(output_folder, "masked_rrs_plot.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", transparent=False)
        plt.close(fig)
