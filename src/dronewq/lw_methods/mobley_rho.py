"""Refactored by: Temuulen"""

import concurrent.futures
import glob
import logging
import os
from functools import partial

import numpy as np
import rasterio

import dronewq
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def __compute(filepath, rho, lsky_median, lw_dir):
    """
    Process a single Lt file to compute water-leaving radiance using Mobley rho method.

    Worker function that reads a total radiance (Lt) raster file, removes surface-
    reflected sky radiance using a constant rho value, and writes the resulting
    water-leaving radiance (Lw) to a new file. The method applies the equation
    Lw = Lt - rho * Lsky for each band.

    Parameters
    ----------
    filepath : str
        Path to the input Lt raster file.
    rho : float
        Effective sea-surface reflectance of a wave facet. Typically 0.028 based
        on Mobley (1999) recommendations for wind speeds < 5 m/s.
    lsky_median : array-like
        Median sky radiance values for 5 bands, indexed from 0-4.
    lw_dir : str
        Directory path where the output Lw file will be saved.

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
    The function processes 5 bands, computing Lw = Lt - rho * Lsky for each band.
    Output files maintain the same basename as input files.
    """
    try:
        with rasterio.open(filepath, "r") as Lt_src:
            profile = Lt_src.profile
            profile["count"] = 5
            lw_all = []
            for i in range(1, 6):
                lt = Lt_src.read(i)
                lw = lt - (rho * lsky_median[i - 1])
                lw_all.append(lw)

            stacked_lw = np.stack(lw_all)

            # Write new stacked lw tifs
            im_name = os.path.basename(filepath)
            output_path = os.path.join(lw_dir, im_name)
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(stacked_lw)
        return True
    except Exception as e:
        logger.warning(
            "File %s failed: %s",
            filepath,
            str(e),
        )
        raise

    return filepath


def mobley_rho(rho=0.028, executor=None, num_workers=4):
    """
    Calculate water-leaving radiance using Mobley's constant rho method.

    This function computes water-leaving radiance (Lw) by removing surface-reflected
    sky radiance from total radiance measurements using a constant effective surface
    reflectance factor (rho). Sky radiance (Lsky) is calculated from a median of sky
    images and multiplied by rho to estimate the surface-reflected component, which
    is then subtracted from total radiance: Lw = Lt - rho * Lsky.

    Parameters
    ----------
    rho : float, optional
        Effective sea-surface reflectance of a wave facet. The default value of
        0.028 is based on Mobley (1999) recommendations for typical conditions.
        Default is 0.028.
    executor : concurrent.futures.Executor, optional
        Pre-configured executor for parallel processing. If None, a new
        ProcessPoolExecutor will be created. Default is None.
    num_workers : int, optional
        Number of parallel worker processes for file processing. Should be
        tuned based on available CPU cores. Default is 4.

    Returns
    -------
    None

    Raises
    ------
    LookupError
        If main_dir or lw_dir are not set in settings.

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
    The function produces Lw GeoTIFF files with units of W/sr/nm in settings.lw_dir.

    Sky radiance is computed from the first 10 sky images in settings.sky_lt_dir,
    taking the median across all images for each band. This median Lsky assumes
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
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    sky_lt_dir = settings.sky_lt_dir
    lt_dir = settings.lt_dir
    lw_dir = settings.lw_dir

    # Validate lw_dir
    if lw_dir is None:
        raise LookupError("Please set the lw_dir path in settings.")

    # Grab the first ten sky images, average them, then delete from memory
    sky_imgs_gen = dronewq.load_imgs(
        sky_lt_dir,
        count=10,
        start=0,
        altitude_cutoff=0,
    )

    sky_imgs = np.array(list(sky_imgs_gen))

    lsky_median = np.median(sky_imgs, axis=(0, 2, 3))
    del sky_imgs  # Free up memory

    # Process each Lt image
    filepaths = glob.glob(lt_dir + "/*.tif")

    if executor is not None:
        partial_compute = partial(
            __compute,
            rho=rho,
            lsky_median=lsky_median,
            lw_dir=lw_dir,
        )
        results = list(executor.map(partial_compute, filepaths, chunksize=5))
        logger.info(
            "Lw Stage (Mobley_rho): Successfully processed: %d captures",
            len(results),
        )

    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            futures = {}
            for filepath in filepaths:
                future = executor.submit(
                    __compute,
                    filepath,
                    rho,
                    lsky_median,
                    lw_dir,
                )
                futures[future] = filepath
            # Wait for all tasks to complete and collect results
            results = []
            completed = 0

            for future in concurrent.futures.as_completed(futures):
                try:
                    # Blocks until this specific future completes
                    result = future.result()
                    results.append(result)
                    completed += 1
                except Exception as e:
                    filepath = futures[future]
                    logger.warning(
                        "File %s failed: %s",
                        filepath,
                        str(e),
                    )
                    results.append(False)

        logger.info(
            "Lw Stage (Mobley_rho): Successfully processed: %d/%d captures",
            sum(results),
            len(results),
        )
