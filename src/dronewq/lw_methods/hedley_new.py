"""Refactored by: Temuulen"""

import logging
import os
import random

import numpy as np
import rasterio
from numpy.polynomial import Polynomial

from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def __compute(filepath, mean_min_lt_NIR, lw_dir):
    """
    Process a single Lt file to compute water-leaving radiance using Hedley deglinting.

    Worker function that reads a total radiance (Lt) raster file, applies the Hedley
    et al. deglinting method to remove sun glint effects, and writes the resulting
    water-leaving radiance (Lw) to a new file. The method establishes a linear
    relationship between NIR and visible bands, then uses this to remove glint
    contribution based on deviation from ambient NIR levels.

    Parameters
    ----------
    filepath : str
        Path to the input Lt raster file.
    mean_min_lt_NIR : float
        Ambient NIR brightness level calculated from the minimum 10th percentile
        of Lt(NIR) across a random subset of images. Represents NIR brightness
        of pixels without sun glint.
    lw_dir : str
        Directory path where the output Lw file will be saved.

    Returns
    -------
    str
        The input filepath, returned for progress tracking.

    Notes
    -----
    The function performs the following steps for each visible band (bands 0-3):
    1. Fits a linear polynomial between NIR (band 4) and the visible band
    2. Extracts the slope coefficient from the fitted relationship
    3. Computes Lw = Lt - slope * (Lt_NIR - ambient_NIR)

    The NIR band (band 4) is kept unchanged in the output.
    Output files maintain the same basename as input files.
    """
    im_name = os.path.basename(filepath)

    with rasterio.open(filepath, "r") as lt_src:
        profile = lt_src.profile
        lt = lt_src.read()
        lt_reshape = lt.reshape(*lt.shape[:-2], -1)  # flatten last two dims

        lw_all = []
        for j in range(4):
            # Fit polynomial using new API
            p = Polynomial.fit(lt_reshape[4, :], lt_reshape[j, :], 1)
            # Extract slope coefficient (coefficient of x^1 term)
            slopes = p.convert().coef[1]
            # calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
            lw = lt[j, :, :] - slopes * (lt[4, :, :] - mean_min_lt_NIR)
            lw_all.append(lw)

        # Keep the original NIR band
        lw_all.append(lt[4, :, :])

        stacked_lw = np.stack(lw_all)
        profile["count"] = 5

        output = os.path.join(lw_dir, im_name)

        # write new stacked Lw tif
        with rasterio.open(output, "w", **profile) as dst:
            dst.write(stacked_lw)

    return filepath  # Return filepath for progress tracking


def hedley(random_n=10, num_workers=4, executor=None):
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
    random_n : int, optional
        Number of random images to sample for calculating the ambient NIR level.
        More images provide a more robust estimate but increase computation time.
        Default is 10.
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
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    lt_dir = settings.lt_dir
    lw_dir = settings.lw_dir
    filepaths = glob.glob(lt_dir + "/*.tif")

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

    if executor is not None:
        partial_compute = partial(
            __compute,
            mean_min_lt_NIR=mean_min_lt_NIR,
            lw_dir=lw_dir,
        )
        results = list(executor.map(partial_compute, filepaths))
        logger.info(
            "Lw Stage (Hedley): Successfully processed: %d captures",
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
                    mean_min_lt_NIR,
                    lw_dir,
                )
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
            "Lw Stage (Hedley): Successfully processed: %d/%d captures",
            sum(results),
            len(results),
        )
