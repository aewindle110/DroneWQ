"""Refactored by: Temuulen"""

import logging
import os

import numpy as np

from dronewq.utils.data_types import Base_Compute_Method, Image
from dronewq.utils.images import load_imgs
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class Blackpixel(Base_Compute_Method):
    def __init__(self, save_images: bool = False):
        """
        Calculate water-leaving radiance using the black pixel assumption.

        This function computes water-leaving radiance (Lw) by applying the black pixel
        assumption, which assumes that Lw in the near-infrared (NIR) band is negligible
        due to strong water absorption. Under this assumption, total radiance (Lt) in
        the NIR is considered to be solely surface-reflected light (Lsr), which allows
        the surface reflectance factor (rho) to be calculated if sky radiance (Lsky)
        is known. This rho is then used to remove surface-reflected light from all bands.

        Parameters
        ----------
        save_images : bool, optional
            Whether to save the processed output images to disk. Default is False.

        Returns
        -------
        None

        Raises
        ------
        LookupError
            If main_dir is not set in settings.

        Warnings
        --------
        This method should only be used for Case 1 waters (clear oceanic waters)
        where there is little to no NIR signal. The black pixel assumption tends
        to fail in more turbid Case 2 waters where high concentrations of suspended
        particles enhance backscattering and produce significant Lw in the NIR.

        Notes
        -----
        The function produces Lw GeoTIFF files with units of W/sr/nm in settings.lw_dir.

        Sky radiance (Lsky) is computed from the first 10 sky images in settings.sky_lt_dir,
        taking the median across all images for each band. This median Lsky is then used
        for all water image processing.

        The NIR band (band 4) is used to calculate the surface reflectance factor:
        rho = Lt_NIR / Lsky_NIR

        This method assumes:
        - Negligible water-leaving radiance in the NIR
        - Spatially uniform surface reflectance properties
        - Stable sky conditions during data collection
        """
        super().__init__(save_images=save_images)
        self.lsky_median = self.__lsky_median(settings.sky_lt_dir)

    def __call__(self, lt_img: Image) -> Image:
        lsky_median = self.lsky_median

        if lt_img.data.shape[0] < 5:
            raise ValueError("Image must have at least 5 bands.")

        try:
            Lt_NIR = lt_img.data[3]
            Lsky_NIR = lsky_median[3]
            if Lsky_NIR == 0:
                raise ValueError("Lsky_NIR is zero, cannot compute rho.")
            rho = Lt_NIR / Lsky_NIR
            stacked_lw = lt_img.data[:5] - (rho * lsky_median[:5])
            lw_img = Image.from_image(
                lt_img, stacked_lw, method=self.__class__.__name__
            )
            logger.info(
                "Lw Stage (Blackpixel): Successfully processed: %s",
                lt_img.file_name,
            )
            return lw_img
        except Exception as e:
            raise RuntimeError(f"File {lt_img.file_path!s} failed: {e!s}")

    def __lsky_median(self, sky_lt_dir: str) -> np.ndarray:
        """Compute the median Lsky for all bands."""

        if sky_lt_dir is None:
            raise ValueError("Please set the sky_lt_dir path in settings.")

        if not os.path.exists(sky_lt_dir):
            raise LookupError(f"{sky_lt_dir!s} path does not exist!.")

        sky_imgs_filenames = os.listdir(sky_lt_dir)
        if not (sky_imgs_filenames):
            raise LookupError("There are no sky images in sky_lt_imgs folder.")

        # Grab the first ten sky images, average them, then delete from memory
        sky_imgs_gen = load_imgs(
            sky_lt_dir,
            count=min(len(sky_imgs_filenames), 10),
            start=0,
            altitude_cutoff=0,
        )

        sky_imgs = np.array(list(sky_imgs_gen))
        lsky_median = np.median(sky_imgs, axis=(0, 2, 3))

        return lsky_median
