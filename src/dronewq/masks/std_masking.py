"""Refactored by Temuulen"""

import concurrent.futures
import glob
import logging
import os
from functools import partial

import numpy as np
import rasterio

from dronewq.utils.images import load_imgs
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def __compute(
    filepath,
    masked_rrs_dir,
    rrs_nir_mean,
    rrs_nir_std,
    mask_std_factor,
):
    """
    Process a single Rrs file to mask sun glint pixels based on NIR threshold.

    Worker function that reads a remote sensing reflectance (Rrs) raster file,
    identifies pixels likely contaminated by sun glint using NIR values exceeding
    a statistical threshold, masks these pixels across all bands by setting them
    to NaN, and writes the masked result to a new file.

    Parameters
    ----------
    filepath : str
        Path to the input Rrs raster file.
    masked_rrs_dir : str
        Directory path where the masked output file will be saved.
    rrs_nir_mean : float
        Mean NIR reflectance value calculated from a subset of images,
        representing typical glint-free conditions.
    rrs_nir_std : float
        Standard deviation of NIR reflectance values from a subset of images.
    mask_std_factor : float
        Multiplier for standard deviation to determine the masking threshold.
        Lower values result in more aggressive masking.

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
    im = filepath
    try:
        with rasterio.open(im, "r") as rrs_src:
            profile = rrs_src.profile
            profile["count"] = 5
            rrs_deglint_all = []
            rrs_nir_deglint = rrs_src.read(5)  # nir band
            rrs_nir_deglint[
                rrs_nir_deglint > (rrs_nir_mean + rrs_nir_std * mask_std_factor)
            ] = np.nan
            nan_index = np.isnan(rrs_nir_deglint)
            # filter nan pixel indicies across all bands
            for i in range(1, 6):
                rrs_deglint = rrs_src.read(i)
                rrs_deglint[nan_index] = np.nan
                rrs_deglint_all.append(rrs_deglint)  # append all for each band
            stacked_rrs_deglint = np.stack(rrs_deglint_all)  # stack into np.array
            # write new stacked tifs
            im_name = os.path.basename(
                im,
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(
                os.path.join(masked_rrs_dir, im_name),
                "w",
                **profile,
            ) as dst:
                dst.write(stacked_rrs_deglint)
    except Exception as e:
        logger.warning(
            "Threshold Masking error: File %s has failed with error %s",
            filepath,
            str(e),
        )
        raise


def std_masking(
    num_images=10,
    mask_std_factor=1,
    num_workers=4,
    executor=None,
):
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
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    rrs_dir = settings.rrs_dir
    masked_rrs_dir = settings.masked_rrs_dir

    # grab the first num_images images, finds the mean and std of NIR, then anything times the glint factor is classified as glint
    rrs_imgs_gen = load_imgs(
        rrs_dir,
        count=num_images,
        start=0,
        altitude_cutoff=0,
        random=True,
    )
    rrs_imgs = np.array(list(rrs_imgs_gen))
    rrs_nir_mean = np.nanmean(rrs_imgs, axis=(0, 2, 3))[4]  # mean of NIR band
    rrs_nir_std = np.nanstd(rrs_imgs, axis=(0, 2, 3))[4]  # std of NIR band
    logger.info(
        "The mean and std of Rrs from first N images is: %d, %d",
        rrs_nir_mean,
        rrs_nir_std,
    )
    logger.info(
        "Pixels will be masked where Rrs(NIR) > %d",
        rrs_nir_mean + rrs_nir_std * mask_std_factor,
    )
    del rrs_imgs  # free up the memory

    # go through each Rrs image in the dir and mask any pixels > mean+std*glint factor
    filepaths = glob.glob(rrs_dir + "/*.tif")

    partial_compute = partial(
        __compute,
        masked_rrs_dir=masked_rrs_dir,
        rrs_nir_mean=rrs_nir_mean,
        rrs_nir_std=rrs_nir_std,
        mask_std_factor=mask_std_factor,
    )

    if executor is not None:
        results = list(executor.map(partial_compute, filepaths))
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            results = list(executor.map(partial_compute, filepaths))

    logger.info(
        "Masking Stage (std): Successfully processed: %d captures",
        len(results),
    )
