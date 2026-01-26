"""Refactored by Temuulen"""

import logging

import numpy as np

from dronewq.utils.data_types import Base_Compute_Method, Image
from dronewq.utils.images import load_imgs
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class StdMasking(Base_Compute_Method):
    """
    Mask sun glint pixels using statistical threshold based on NIR values.

    This function identifies and masks pixels contaminated by specular sun glint
    by applying a statistical threshold to near-infrared (NIR) reflectance values.
    The mean and standard deviation of NIR values are calculated from a random
    subset of images, and any pixel with NIR reflectance exceeding
    mean + std * mask_std_factor is masked across all bands. This approach assumes
    that glint-contaminated pixels have elevated NIR reflectance compared to
    glint-free water.

    Parameters
    ----------
    num_images : int, optional
        Number of images to randomly sample for calculating NIR statistics
        (mean and standard deviation). More images provide more robust statistics
        but increase computation time. Default is 10.
    mask_std_factor : float, optional
        Multiplier for the standard deviation to set the masking threshold.
        Lower values result in more aggressive masking (more pixels masked).
        Higher values are more conservative (fewer pixels masked). Typical
        values range from 0.5 to 2.0. Default is 1.

    Returns
    -------
    None

    Raises
    ------
    LookupError
        If main_dir is not set in settings.

    Notes
    -----
    The function produces masked Rrs GeoTIFF files in settings.masked_rrs_dir where
    glint-contaminated pixels are set to NaN across all bands.

    The masking threshold is calculated as:
        threshold = mean(Rrs_NIR) + std(Rrs_NIR) * mask_std_factor

    Pixels where Rrs(NIR) > threshold are masked in all 5 bands.

    The method assumes:
    - Sun glint causes elevated NIR reflectance
    - The sampled images are representative of the dataset
    - NIR values follow an approximately normal distribution for glint-free pixels

    Recommended mask_std_factor values:
    - 0.5-1.0: Aggressive masking for highly glint-contaminated data
    - 1.0-1.5: Moderate masking for typical conditions
    - 1.5-2.0: Conservative masking to preserve more pixels
    """

    def __init__(
        self,
        num_images=10,
        mask_std_factor=1,
        save_images: bool = False,
    ):
        super().__init__(save_images=save_images)

        self.std_factor = mask_std_factor
        self.rrs_nir_mean, self.rrs_nir_std = self.__calculate_rrs_nir(
            num_images,
            mask_std_factor,
        )

    def __call__(
        self,
        rrs_img: Image,
    ):
        """
        Process a single Rrs file to mask sun glint pixels based on NIR threshold.

        Worker function that reads a remote sensing reflectance (Rrs) raster file,
        identifies pixels likely contaminated by sun glint using NIR values exceeding
        a statistical threshold, masks these pixels across all bands by setting them
        to NaN, and writes the masked result to a new file.

        Parameters
        ----------
        rrs_img : Image
            Image object containing the Rrs raster file.

        Notes
        -----
        Pixels are masked where: Rrs(NIR) > rrs_nir_mean + rrs_nir_std * mask_std_factor

        The masking is applied to all 5 bands based on the NIR (band 5) threshold.
        Masked pixels are set to NaN across all bands.
        Output files maintain the same basename as input files.

        Raises
        ------
        Exception
            If file processing fails for any reason (logged as warning and re-raised).
        """
        try:
            # write new stacked tifrrs = rrs_img.data  # shape: (5, H, W) (or generally (bands, ...))
            rrs = rrs_img.data
            thr = self.rrs_nir_mean + self.rrs_nir_std * self.std_factor
            mask = rrs[4] > thr  # True where you want to NaN-out (based on NIR)

            stacked_rrs_deglint = rrs.copy()  # avoid mutating original
            stacked_rrs_deglint[:, mask] = np.nans
            masked_rrs_img = Image.from_image(
                rrs_img, data=stacked_rrs_deglint, method=self.__class__.__name__
            )
            logger.info(
                "Threshold Masking: Successfully processed: %s",
                rrs_img.file_name,
            )
            return masked_rrs_img
        except Exception as e:
            raise RuntimeError(f"File {rrs_img.file_path!s} failed: {e!s}")

    def __calculate_rrs_nir(
        self,
        num_images=10,
        mask_std_factor=1,
    ):
        if settings.rrs_dir is None:
            raise ValueError("Please set the rrs_dir path.")

        # grab the first num_images images,
        # finds the mean and std of NIR,
        # then anything times the glint factor
        # is classified as glint
        rrs_imgs_gen = load_imgs(
            settings.rrs_dir,
            count=num_images,
            start=0,
            altitude_cutoff=0,
            random=True,
        )
        rrs_imgs = np.array(list(rrs_imgs_gen))
        # mean of NIR band
        rrs_nir_mean = np.nanmean(rrs_imgs, axis=(0, 2, 3))[4]
        # std of NIR band
        rrs_nir_std = np.nanstd(rrs_imgs, axis=(0, 2, 3))[4]
        logger.info(
            "The mean and std of Rrs from first N images is: %d, %d",
            rrs_nir_mean,
            rrs_nir_std,
        )
        logger.info(
            "Pixels will be masked where Rrs(NIR) > %d",
            rrs_nir_mean + rrs_nir_std * mask_std_factor,
        )
        return rrs_nir_mean, rrs_nir_std
