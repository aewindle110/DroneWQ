"""Refactored by: Temuulen"""

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


def __compute(filepath, lw_dir, lsky_median):
    """
    Process a single Lt file to compute water-leaving radiance using black pixel assumption.

    Worker function that reads a total radiance (Lt) raster file, applies the black
    pixel assumption to remove surface-reflected light, and writes the resulting
    water-leaving radiance (Lw) to a new file. The black pixel assumption uses the
    NIR band to estimate the surface reflectance factor (rho), assuming negligible
    water-leaving radiance in the NIR due to strong water absorption.

    Parameters
    ----------
    filepath : str
        Path to the input Lt raster file.
    lw_dir : str
        Directory path where the output Lw file will be saved.
    lsky_median : array-like
        Median sky radiance values for 5 bands, indexed from 0-4.

    Returns
    -------
    bool
        True if processing succeeded.

    Raises
    ------
    Exception
        If file processing fails for any reason (printed and re-raised).

    Notes
    -----
    The function computes Lw = Lt - (rho * Lsky) for each band, where:
    - rho is calculated from the NIR band (band 4): rho = Lt_NIR / Lsky_NIR
    - This rho is then applied to all bands to remove surface-reflected light

    Output files maintain the same basename as input files.
    """
    im = filepath
    try:
        with rasterio.open(im, "r") as Lt_src:
            profile = Lt_src.profile
            profile["count"] = 5

            Lt = Lt_src.read(4)
            rho = Lt / lsky_median[4 - 1]
            lw_all = []
            for i in range(1, 6):
                # TODO: this is probably faster if we read them all and divide by the vector
                lt = Lt_src.read(i)
                lw = lt - (rho * lsky_median[i - 1])
                lw_all.append(lw)  # append each band
            stacked_lw = np.stack(lw_all)  # stack into np.array

            # write new stacked lw tifs
            im_name = os.path.basename(
                im,
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(lw_dir, im_name), "w", **profile) as dst:
                dst.write(stacked_lw)

            return True
    except Exception as e:
        print(f"Blackpixel Error: File {filepath} has the error {e}")
        raise


def blackpixel(num_workers=4, executor=None):
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
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    sky_lt_dir = settings.sky_lt_dir
    lt_dir = settings.lt_dir
    lw_dir = settings.lw_dir

    filepaths = glob.glob(lt_dir + "/*.tif")

    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs_gen = load_imgs(
        sky_lt_dir,
        count=10,
        start=0,
        altitude_cutoff=0,
    )
    sky_imgs = np.array(list(sky_imgs_gen))
    lsky_median = np.median(
        sky_imgs,
        axis=(0, 2, 3),
    )  # here we want the median of each band
    del sky_imgs

    if executor is not None:
        partial_compute = partial(
            __compute,
            lw_dir=lw_dir,
            lsky_median=lsky_median,
        )
        results = list(executor.map(partial_compute, filepaths))
        logger.info(
            "Lw Stage (blackpixel): Successfully processed: %d captures",
            len(results),
        )
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            futures = {}
            for filepath in filepaths:
                future = executor.submit(__compute, filepath, lw_dir, lsky_median)
                futures[future] = filepath
            # Wait for all tasks to complete and collect results
            results = []
            completed = 0

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = (
                        future.result()
                    )  # Blocks until this specific future completes
                    results.append(result)
                    completed += 1
                except Exception as e:
                    filepath = futures[future]
                    print(f"File {filepath} failed: {e}")
                    results.append(False)

        logger.info(
            "Lw Stage (blackpixel): Successfully processed: %d/%d captures",
            sum(results),
            len(results),
        )
