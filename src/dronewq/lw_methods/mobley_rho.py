"""Refactored by: Temuulen"""

import logging
import os

import numpy as np

from dronewq.utils.data_types import Base_Compute_Method, Image
from dronewq.utils.images import load_imgs
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class Mobley_rho(Base_Compute_Method):
    def __init__(self, save_images: bool = False, rho: float = 0.028):
        """
        Calculate water-leaving radiance using Mobley's constant rho method.

        This function computes water-leaving radiance (Lw) by removing surface-reflected
        sky radiance from total radiance measurements using a constant effective surface
        reflectance factor (rho). Sky radiance (Lsky) is calculated from a median of sky
        images and multiplied by rho to estimate the surface-reflected component, which
        is then subtracted from total radiance: Lw = Lt - rho * Lsky.

        Parameters
        ----------
        save_images : bool, optional
            Whether to save the processed output images to disk. Default is False.
        rho : float, optional
            Effective sea-surface reflectance of a wave facet. Typically 0.028 based
            on Mobley (1999) recommendations for wind speeds < 5 m/s.

        Returns
        -------
        Image
            New Image object containing water-leaving radiance (Lw) data.

        Raises
        ------
        LookupError
            If main_dir or sky_lt_dir are not set in settings.

        Warnings
        --------
        This method should only be used when:
        - Sky conditions are relatively stable during the flight
        - Wind speeds are less than 5 m/s
        - Sea surface roughness is relatively uniform

        Variable sky conditions or higher wind speeds may require spatially or temporally
        varying rho values for accurate results.

        Notes
        -----
        The function produces Lw GeoTIFF files with units of W/sr/nm.

        Sky radiance is computed from the first 10 or the available
        sky images in settings.sky_lt_dir, taking the median across
        all images for each band. This median Lsky assumes
        relatively stable sky conditions throughout the data collection period.

        The rho value of 0.028 corresponds to moderately rough sea surfaces under typical
        viewing and illumination geometries. This value may need adjustment for:
        - Very calm waters (lower rho, ~0.02)
        - Rough seas or high winds (higher rho, ~0.05)
        - Off-nadir viewing angles
        - Different solar zenith angles

        The function processes 5 spectral bands across all input images.

        References
        ----------
        Mobley, C. D. (1999). Estimation of the remote-sensing reflectance from
        above-surface measurements. Applied Optics, 38(7), 7442-7455.
        """
        super().__init__(save_images=save_images)
        self.rho = rho
        self.lsky_median = self.__lsky_median(settings.sky_lt_dir)

    def __call__(self, lt_img: Image) -> Image:
        try:
            stacked_lw = lt_img.data[:5] - (self.rho * self.lsky_median[:, None, None])
            lw_img = Image.from_image(
                lt_img, stacked_lw, method=self.__class__.__name__
            )
            logger.info(
                "Lw Stage (Mobley_rho): Successfully processed: %s",
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
