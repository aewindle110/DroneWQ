"""Refactored by: Temuulen"""

import logging
import os

import numpy as np
import pandas as pd

from dronewq.micasense import imageset
from dronewq.utils.data_types import Base_Compute_Method, Image
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class Dls_ed(Base_Compute_Method):
    def __init__(
        self,
        output_csv_path: str,
        dls_corr: bool = False,
        save_images: bool = False,
    ):
        super().__init__(save_images=save_images)
        self.ed_row = self.__calculate_ed(dls_corr, output_csv_path)
        self.__ed_index = 0

    def __call__(
        self,
        lw_img: Image,
    ) -> Image:
        """
        Calculate remote sensing reflectance using downwelling light sensor data.

        This function computes remote sensing reflectance (Rrs) by dividing
        water-leaving radiance (Lw) by downwelling irradiance (Ed) derived from
        the downwelling light sensor (DLS). The DLS collects Ed measurements at
        every image capture. Optionally applies a correction factor derived from
        calibration panel measurements to compensate for DLS variability.

        Parameters
        ----------
        lw_img : Image
            Input Lt Image object containing total radiance data.

        Returns
        -------
        None

        Raises
        ------
        LookupError
            If required directory paths (main_dir, rrs_dir) are not set in settings.

        Notes
        -----
        This method performs best in overcast or completely cloudy conditions where
        light is relatively stable. Performance degrades under variable lighting
        such as partly cloudy conditions.

        The function produces two types of outputs:
        - Rrs GeoTIFF files with units of sr^-1 in the rrs_dir
        - CSV file(s) containing average Ed measurements in mW/m^2/nm

        When dls_corr=True, outputs 'dls_corr_ed.csv'; otherwise outputs 'dls_ed.csv'.

        The function processes 5 spectral bands centered at approximately:
        475nm, 560nm, 668nm, 717nm, and 842nm.
        """
        # Process Lw imagery: divide by Ed to get Rrs
        try:
            idx = self.__ed_index
            row = self.ed_row[idx]
            ed = np.array(row[1:6])
            stacked_rrs = lw_img.data[:5] / ed[:, None, None]
            self.__ed_index += 1
            rrs_img = Image.from_image(
                lw_img,
                stacked_rrs,
                method=self.__class__.__name__,
            )

            logger.info(
                "Ed Stage: Successfully processed: %s",
                lw_img.file_name,
            )
            return rrs_img

        except Exception as e:
            raise RuntimeError(f"File {lw_img.file_path!s} failed: {e!s}")

    def __calculate_ed(self, dls_corr: bool, output_csv_path: str) -> list:
        if settings.main_dir is None:
            raise LookupError("Please set the main_dir path.")

        panel_dir = settings.panel_dir
        rrs_dir = settings.rrs_dir
        raw_water_dir = settings.raw_water_dir

        # Validate rrs_dir
        if rrs_dir is None:
            raise LookupError("Please set the rrs_dir path in settings.")

        ed_data = []
        ed_columns = ["image", "ed_475", "ed_560", "ed_668", "ed_717", "ed_842"]

        if dls_corr:
            panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures

            panel_ed_data = []
            dls_ed_data = []

            for i, capture in enumerate(panel_imgset):
                # calculate panel Ed from every panel capture
                panel_ed = capture.panel_irradiance()
                panel_ed[3], panel_ed[4] = (
                    panel_ed[4],
                    panel_ed[3],
                )  # flip last two bands
                panel_ed_row = (
                    ["capture_" + str(i + 1)]
                    + [np.mean(panel_ed[0])]
                    + [np.mean(panel_ed[1])]
                    + [np.mean(panel_ed[2])]
                    + [np.mean(panel_ed[3])]
                    + [np.mean(panel_ed[4])]
                )
                panel_ed_data.append(panel_ed_row)

                # calculate DLS Ed from every panel capture
                dls_ed = capture.dls_irradiance()
                dls_ed[3], dls_ed[4] = dls_ed[4], dls_ed[3]  # flip last two bands
                dls_ed_row = (
                    ["capture_" + str(i + 1)]
                    + [np.mean(dls_ed[0] * 1000)]
                    + [np.mean(dls_ed[1] * 1000)]
                    + [np.mean(dls_ed[2] * 1000)]
                    + [np.mean(dls_ed[3] * 1000)]
                    + [np.mean(dls_ed[4] * 1000)]
                )
                dls_ed_data.append(dls_ed_row)

            dls_ed_corr = np.array(panel_ed) / (np.array(dls_ed[0:5]) * 1000)

            # DLS ed corrected by the panel correction factor
            capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
            for i, capture in enumerate(capture_imgset):
                ed = capture.dls_irradiance()
                ed = (ed[0:5] * dls_ed_corr) * 1000
                ed = np.append(ed, [0])
                dls_ed_corr_row = (
                    ["capture_" + str(i + 1)]
                    + [ed[0]]
                    + [ed[1]]
                    + [ed[2]]
                    + [ed[3]]
                    + [ed[4]]
                )
                ed_data.append(dls_ed_corr_row)

            dls_ed_corr_data_df = pd.DataFrame.from_records(
                ed_data,
                index="image",
                columns=ed_columns,
            )
            dls_ed_corr_data_df.to_csv(os.path.join(output_csv_path, "dls_corr_ed.csv"))
            del dls_ed_corr_data_df

        else:
            capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
            for i, capture in enumerate(capture_imgset):
                ed = capture.dls_irradiance()
                ed[3], ed[4] = ed[4], ed[3]  # flip last two bands
                ed_row = (
                    ["capture_" + str(i + 1)]
                    + [np.mean(ed[0] * 1000)]
                    + [np.mean(ed[1] * 1000)]
                    + [np.mean(ed[2] * 1000)]
                    + [np.mean(ed[3] * 1000)]
                    + [np.mean(ed[4] * 1000)]
                )
                ed_data.append(ed_row)

            ed_data_df = pd.DataFrame.from_records(
                ed_data,
                index="image",
                columns=ed_columns,
            )
            ed_data_df.to_csv(os.path.join(output_csv_path, "dls_ed.csv"))

        return ed_data
