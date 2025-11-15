import random
import numpy as np
import glob
import rasterio
import os
import concurrent.futures
import logging
from functools import partial
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def _compute(filepath, mean_min_lt_NIR, lw_dir):
    """Worker function that processes a single file."""

    im_name = os.path.basename(filepath)

    try:
        with rasterio.open(filepath, "r") as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_reshape = lt.reshape(*lt.shape[:-2], -1)  # flatten last two dims

            lw_all = []
            # NOTE: Is this supposed to also compute the NIR?
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
        return True  # Return filepath for progress tracking
    except Exception as e:
        logger.warn(
            "Hedley error: File %s has failed with error %s",
            filepath,
            str(e),
        )
        raise


def hedley(random_n=10, num_workers=4, executor=None):
    """
    This function calculates water leaving radiance (Lw) by modelling
    a constant 'ambient' NIR brightness level which is removed from all
    pixels across all bands. An ambient NIR level is calculated by
    averaging the minimum 10% of Lt(NIR) across a random subset images.

    This value represents the NIR brightness of a pixel with no sun glint.
    A linear relationship between Lt(NIR) and the visible bands (Lt) is
    established, and for each pixel, the slope of this line is multiplied
    by the difference between the pixel NIR value and the ambient NIR level.

    Parameters:
        random_n: The amount of random images to calculate ambient NIR level. Default is 10.
        num_workers: Number of parallel processes. Depends on hardware.

    Returns:
         New Lw .tifs with units of W/sr/nm
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
            _compute, mean_min_lt_NIR=mean_min_lt_NIR, lw_dir=lw_dir
        )
        results = list(executor.map(partial_compute, filepaths))
        logger.info(
            "Lw Stage (Hedley): Successfully processed: %d captures",
            len(results),
        )

    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers
        ) as executor:
            futures = {}
            for filepath in filepaths:
                future = executor.submit(
                    _compute,
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
    return results
