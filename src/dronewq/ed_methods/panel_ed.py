"""Refactored by: Temuulen"""

import logging
import os

import numpy as np
import pandas as pd

from dronewq.micasense import imageset
from dronewq.utils.data_types import Base_Compute_Method, Image
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class Panel_ed(Base_Compute_Method):
    def __init__(self, output_csv_path: str, save_images: bool = False):
        super().__init__(save_images=save_images)
        self.output_csv_path = output_csv_path
        self.ed_row = self.__calculate_ed(output_csv_path)
        self.__ed_index = 0

    def __call__(self, lw_img: Image) -> Image:
        """
        Calculate remote sensing reflectance using calibrated reflectance panel.

        This function computes remote sensing reflectance (Rrs) by dividing
        water-leaving radiance (Lw) by downwelling irradiance (Ed) calculated
        from a calibrated reflectance panel. The panel is imaged during data
        collection to provide a reference for Ed measurements. This method
        performs best under clear, sunny conditions with stable lighting.

        Parameters
        ----------
        lw_img : Image
            Input Lw Image object containing total radiance data.

        Returns
        -------
        None

        Raises
        ------
        LookupError
            If main_dir is not set in settings.

        Notes
        -----
        This method does not perform well under variable lighting conditions such
        as partly cloudy days. It is recommended for use on clear, sunny days with
        stable illumination.

        The function produces two types of outputs:
        - Rrs GeoTIFF files with units of sr^-1 in settings.rrs_dir
        - CSV file 'panel_ed.csv' containing average Ed measurements in mW/m^2/nm
          calculated from calibrated reflectance panel captures

        The function processes 5 spectral bands centered at approximately:
        475nm, 560nm, 668nm, 717nm, and 842nm. Note that bands 4 and 5 (717nm and
        842nm) are swapped during processing to correct band ordering.

        The panel_irradiance() method automatically finds the panel albedo and
        uses it to calculate Ed, otherwise raises an error if the panel cannot
        be detected.
        """
        try:
            idx = self.__ed_index
            stacked_rrs = lw_img.data[:5] / self.ed_row[idx][1:6]
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

    def __calculate_ed(self, output_csv_path):
        if os.path.exists(settings.panel_dir):
            raise LookupError("Please set the panel_dir path.")

        panel_dir = settings.panel_dir

        panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
        panels = np.array(panel_imgset)

        ed = []
        ed_columns = ["image", "ed_475", "ed_560", "ed_668", "ed_717", "ed_842"]

        for i in range(len(panels)):
            # calculate panel Ed from every panel capture
            ed = np.array(
                panels[i].panel_irradiance(),
            )
            # this function automatically finds the panel albedo
            # and uses that to calcuate Ed, otherwise raises an error
            # flip last two bands
            ed[3], ed[4] = ed[4], ed[3]
            ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(ed[0])]
                + [np.mean(ed[1])]
                + [np.mean(ed[2])]
                + [np.mean(ed[3])]
                + [np.mean(ed[4])]
            )
            ed.append(ed_row)

        # now divide the lw_imagery by Ed to get rrs
        # go through each Lt image in the dir and divide it by the lsky
        ed_data = pd.DataFrame.from_records(
            ed,
            index="image",
            columns=ed_columns,
        )
        ed_data.to_csv(os.path.join(output_csv_path, "panel_ed.csv"))

        return ed
