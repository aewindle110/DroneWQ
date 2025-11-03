import random
import numpy as np
import glob
import rasterio
import os
import concurrent.futures
from functools import partial
from dronewq.utils.settings import settings


def _compute(filepath, mean_min_lt_NIR, lw_dir):
    """Worker function that processes a single file."""

    im_name = os.path.basename(filepath)

    with rasterio.open(filepath, "r") as lt_src:
        profile = lt_src.profile
        lt = lt_src.read()
        lt_reshape = lt.reshape(*lt.shape[:-2], -1)  # flatten last two dims

        lw_all = []
        for j in range(0, 5):
            slopes = np.polyfit(lt_reshape[4, :], lt_reshape[j, :], 1)[0]
            # calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
            lw = lt[j, :, :] - slopes * (lt[4, :, :] - mean_min_lt_NIR)
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all)
        profile["count"] = 5

        output = os.path.join(lw_dir, im_name)

        # write new stacked Lw tif
        with rasterio.open(output, "w", **profile) as dst:
            dst.write(stacked_lw)

    return filepath  # Return filepath for progress tracking


def hedley(random_n=10, num_workers=4):
    """
    This function calculates water leaving radiance (Lw) by modelling a constant 'ambient' NIR brightness level which is removed from all pixels across all bands. An ambient NIR level is calculated by averaging the minimum 10% of Lt(NIR) across a random subset images. This value represents the NIR brightness of a pixel with no sun glint. A linear relationship between Lt(NIR) and the visible bands (Lt) is established, and for each pixel, the slope of this line is multiplied by the difference between the pixel NIR value and the ambient NIR level.

    Parameters:
        num_workers: Number of parallel processes. Depends on hardware.
        random_n: The amount of random images to calculate ambient NIR level. Default is 10.

    Returns:
         New Lw .tifs with units of W/sr/nm
    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    lt_dir = settings.lt_dir
    lw_dir = settings.lw_dir
    filepaths = glob.glob(lt_dir + "/*.tif")

    # Step 1: Calculate mean_min_lt_NIR from random subset
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

    # Step 2: Process all files in parallel using partial to bind mean_min_lt_NIR
    compute_with_args = partial(
        _compute, mean_min_lt_NIR=mean_min_lt_NIR, lw_dir=lw_dir
    )

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Using list() to force execution and catch any errors
        results = list(executor.map(compute_with_args, filepaths))

    return results
