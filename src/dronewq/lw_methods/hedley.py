"""Refactored by: Temuulen"""

import logging
import random
from pathlib import Path

import numpy as np
import rasterio
from numpy.polynomial import Polynomial

from dronewq.utils.data_types import Base_Compute_Method, Image
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)

BANDS = 5


class Hedley(Base_Compute_Method):
    def __init__(self, save_images: bool = False, random_n: int = 10):
        """
        Calculate water-leaving radiance using the Hedley deglinting method.

        This function implements the Hedley et al. deglinting algorithm to remove
        sun glint effects from water imagery. The method models a constant 'ambient'
        NIR brightness level representing glint-free water, which is calculated by
        averaging the minimum 10th percentile of Lt(NIR) across a random subset of
        images. A linear relationship between Lt(NIR) and visible bands is established
        for each image, and the slope of this relationship is used to remove glint
        contribution based on each pixel's deviation from the ambient NIR level.

        Parameters
        ----------
        save_images : bool, optional
            If True, saves the processed images to the specified output directory.
        random_n : int, optional
            Number of random images to sample for calculating the ambient NIR level.
            More images provide a more robust estimate but increase computation time.
            Default is 10.

        Returns
        -------
        None

        Raises
        ------
        LookupError
            If main_dir is not set in settings.

        Notes
        -----
        The function produces Lw GeoTIFF files with units of W/sr/nm in settings.lw_dir.

        The Hedley deglinting algorithm performs the following steps:
        1. Randomly samples `random_n` images from the Lt directory
        2. Calculates the 0.1th percentile (minimum 10%) of NIR values for each image
        3. Averages these minimum values to establish an ambient NIR level
        4. For each pixel in each image:
           - Fits a linear model between NIR and each visible band
           - Removes glint: Lw = Lt - slope * (Lt_NIR - ambient_NIR)
        5. Preserves the original NIR band in the output

        This method is effective for removing sun glint when:
        - Surface roughness is relatively uniform
        - The water body contains some glint-free pixels
        - Glint patterns are spatially coherent

        The algorithm processes 5 bands, with bands 0-3 being deglinted visible bands
        and band 4 being the unchanged NIR band.

        References
        ----------
        Hedley, J. D., Harborne, A. R., & Mumby, P. J. (2005). Simple and robust
        removal of sun glint for mapping shallow-water benthos. International Journal
        of Remote Sensing, 26(10), 2107-2112.
        """
        super().__init__(save_images=save_images)
        self.mean_min_lt_NIR = self.__mean_min_lt_nir(random_n)

    def __call__(self, lt_img: Image) -> Image:
        try:
            if lt_img.data.shape[0] < BANDS:
                msg = "Image must have at least 5 bands."
                raise ValueError(msg)
            lt = lt_img.data
            lt_reshape = lt.reshape(*lt.shape[:-2], -1)  # flatten last two dims

            lw_all = []
            for j in range(4):
                # Fit polynomial using new API
                p = Polynomial.fit(lt_reshape[4, :], lt_reshape[j, :], 1)
                # Extract slope coefficient (coefficient of x^1 term)
                slopes = p.convert().coef[1]
                # calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
                lw = lt[j, :, :] - slopes * (lt[4, :, :] - self.mean_min_lt_NIR)
                lw_all.append(lw)

            # Keep the original NIR band
            lw_all.append(lt[4, :, :])
            stacked_lw = np.stack(lw_all)

            lw_img = Image.from_image(
                lt_img,
                data=stacked_lw,
                method=self.__class__.__name__,
            )
            logger.info(
                "Lw Stage (Hedley): Successfully processed: %s",
                lt_img.file_name,
            )
            return lw_img
        except Exception as e:
            msg = f"File {lt_img.file_path!s} failed: {e!s}"
            raise RuntimeError(msg)

    def __mean_min_lt_nir(self, random_n=10) -> float:
        """Sample a mean minimum lt NIR value from all the lt images."""
        lt_dir = settings.lt_dir
        filepaths = list(Path(lt_dir).glob("*.tif"))

        lt_all = []
        rand = random.sample(filepaths, random_n)

        for im in rand:
            with rasterio.open(im, "r") as lt_src:
                lt = lt_src.read()
                lt_all.append(lt)

        stacked_lt = np.stack(lt_all)
        stacked_lt_reshape = stacked_lt.reshape(*stacked_lt.shape[:-2], -1)

        min_lt_NIR = []
        for i in range(len(rand)):
            min_lt_NIR.append(np.percentile(stacked_lt_reshape[i, 4, :], 0.1))

        mean_min_lt_NIR = np.mean(min_lt_NIR)

        return mean_min_lt_NIR
