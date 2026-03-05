"""Refactored by Temuulen"""

import logging

import numpy as np

from dronewq.utils.data_types import Base_Compute_Method, Image

logger = logging.getLogger(__name__)

MASK_VALUE = np.nan


class ThresholdMasking(Base_Compute_Method):
    """
    Mask contaminated pixels using fixed reflectance thresholds.

    This function identifies and masks pixels contaminated by sun glint, adjacent
    land features, or shadows by applying fixed threshold values to NIR and green
    band reflectances. Pixels with elevated NIR values (typically glint or land)
    or low green values (typically shadows) are masked across all bands. This
    dual-threshold approach helps remove multiple sources of contamination in
    aquatic remote sensing imagery.

    Parameters
    ----------
    nir_threshold : float, optional
        Upper threshold for NIR reflectance (sr^-1). Pixels with Rrs(NIR) exceeding
        this value are masked. These typically represent specular sun glint or
        adjacent land features. Default is 0.01.
    green_threshold : float, optional
        Lower threshold for green reflectance (sr^-1). Pixels with Rrs(green) below
        this value are masked. These typically represent vegetation shadows or
        very dark features. Default is 0.005.
    save_images : bool, optional
        If True, saves the processed images to the specified output directory.
        Default is False.

    Notes
    -----
    The function produces masked Rrs GeoTIFF files with units of sr^-1 in
    settings.masked_rrs_dir where contaminated pixels are set to NaN across
    all bands.

    Masking criteria (applied with logical OR):
    1. Rrs(NIR) > nir_threshold: Masks sun glint and land features
    2. Rrs(green) < green_threshold: Masks shadows and very dark features

    A pixel is masked if it meets EITHER criterion, and the mask is applied
    to all 5 spectral bands.

    Threshold selection guidance:

    NIR threshold:
    - 0.005-0.01: Standard for clear oceanic waters (Case 1)
    - 0.01-0.02: Moderate for slightly turbid waters (Case 2)
    - 0.02-0.05: High for very turbid or coastal waters
    - Values too low may mask valid turbid water pixels
    - Values too high may allow glint contamination

    Green threshold:
    - 0.001-0.005: Conservative, masks strong shadows only
    - 0.005-0.01: Moderate, removes most shadow effects
    - 0.01-0.02: Aggressive, may remove valid dark water pixels
    - Values too low may allow shadow contamination
    - Values too high may mask valid oligotrophic water pixels

    This method is most effective for:
    - Imagery containing sun glint not removed by deglinting algorithms
    - Scenes with adjacent land or vegetation features
    - Data with shadow contamination from nearby structures or terrain
    """

    def __init__(
        self,
        nir_threshold=0.01,
        green_threshold=0.005,
        save_images: bool = False,
    ):
        super().__init__(save_images=save_images)
        self.nir_threshold = nir_threshold
        self.green_threshold = green_threshold

    def __call__(
        self,
        rrs_img: Image,
    ):
        try:
            rrs = rrs_img.data
            # Extract NIR (band 5) and green (band 2)
            # Note: rasterio uses 1-based indexing in read(), 0-based in arrays
            nir = rrs[4, :, :]  # Band 5 -> index 4
            green = rrs[1, :, :]  # Band 2 -> index 1

            # Create boolean masks (True = invalid pixel)
            nir_mask = nir > self.nir_threshold
            green_mask = green < self.green_threshold

            # Combine masks: pixel is invalid if EITHER condition is true
            combined_mask = nir_mask | green_mask

            masked_rrs = rrs.copy()
            # Apply mask to all bands
            masked_rrs[:, combined_mask] = np.nan

            masked_rrs_img = Image.from_image(
                rrs_img, data=masked_rrs, method=self.name
            )
            logger.info(
                "Threshold Masking: Successfully processed: %s",
                rrs_img.file_name,
            )
            return masked_rrs_img
        except Exception as e:
            raise RuntimeError(f"File {rrs_img.file_path!s} failed: {e!s}")
