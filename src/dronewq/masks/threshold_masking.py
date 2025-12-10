"""Refactored by Temuulen"""

import concurrent.futures
import glob
import logging
import os
from functools import partial

import numpy as np
import rasterio

from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def __compute(
    filepath,
    nir_threshold,
    green_threshold,
    masked_rrs_dir,
):
    """
    Process a single Rrs file to mask pixels based on NIR and green thresholds.

    Worker function that reads a remote sensing reflectance (Rrs) raster file,
    identifies pixels contaminated by sun glint, land features, or shadows using
    NIR and green band thresholds, masks these pixels across all bands by setting
    them to NaN, and writes the masked result to a new file.

    Parameters
    ----------
    filepath : str
        Path to the input Rrs raster file.
    nir_threshold : float
        Upper threshold for NIR reflectance. Pixels with Rrs(NIR) > nir_threshold
        are masked. These typically represent sun glint or land features.
    green_threshold : float
        Lower threshold for green reflectance. Pixels with Rrs(green) < green_threshold
        are masked. These typically represent vegetation shadows or dark features.
    masked_rrs_dir : str
        Directory path where the masked output file will be saved.

    Returns
    -------
    bool
        True if processing succeeded.

    Raises
    ------
    Exception
        If file processing fails for any reason (logged as warning and re-raised).

    Notes
    -----
    The function applies two masking criteria:
    1. Pixels where Rrs(NIR) > nir_threshold are masked (band 5)
    2. Pixels where Rrs(green) < green_threshold are masked (band 2)

    Pixels meeting EITHER criterion are masked across all 5 bands by setting
    values to NaN. The combined boolean mask uses logical OR operation.

    Output files maintain the same basename as input files.
    """
    try:
        with rasterio.open(filepath, "r") as rrs_src:
            profile = rrs_src.profile
            profile["count"] = 5

            # Read all bands once
            rrs = rrs_src.read()  # Shape: (5, H, W)

            # Extract NIR (band 5) and green (band 2)
            # Note: rasterio uses 1-based indexing in read(), 0-based in arrays
            nir = rrs[4, :, :]  # Band 5 -> index 4
            green = rrs[1, :, :]  # Band 2 -> index 1

            # Create boolean masks (True = invalid pixel)
            nir_mask = nir > nir_threshold
            green_mask = green < green_threshold

            # Combine masks: pixel is invalid if EITHER condition is true
            combined_mask = nir_mask | green_mask

            # Apply mask to all bands
            rrs[:, combined_mask] = np.nan

            # Write masked output
            im_name = os.path.basename(filepath)
            output_path = os.path.join(masked_rrs_dir, im_name)

            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(rrs)

        return True

    except Exception as e:
        logger.warning(
            "Threshold Masking error: File %s has failed with error %s",
            filepath,
            str(e),
        )
        raise


def threshold_masking(
    nir_threshold=0.01,
    green_threshold=0.005,
    num_workers=4,
    executor=None,
):
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
    num_workers : int, optional
        Number of parallel worker processes for file processing. Should be
        tuned based on available CPU cores. Default is 4.
    executor : concurrent.futures.Executor, optional
        Pre-configured executor for parallel processing. If None, a new
        ProcessPoolExecutor will be created. Default is None.

    Returns
    -------
    None

    Raises
    ------
    LookupError
        If main_dir is not set in settings.

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
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    rrs_dir = settings.rrs_dir
    masked_rrs_dir = settings.masked_rrs_dir
    filepaths = glob.glob(rrs_dir + "/*.tif")

    partial_compute = partial(
        __compute,
        nir_threshold=nir_threshold,
        green_threshold=green_threshold,
        masked_rrs_dir=masked_rrs_dir,
    )

    if executor is not None:
        results = list(executor.map(partial_compute, filepaths))
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            results = list(executor.map(partial_compute, filepaths))

    logger.info(
        "Masking Stage (threshold_masking): Successfully processed: %d captures",
        len(results),
    )
