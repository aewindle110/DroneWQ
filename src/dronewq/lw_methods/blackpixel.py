import numpy as np
import glob
import rasterio
import os
import concurrent.futures
import logging
from functools import partial
from dronewq.utils.settings import settings
from dronewq.utils.images import load_imgs

logger = logging.getLogger(__name__)


def _compute(filepath, lw_dir, lsky_median):
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
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(lw_dir, im_name), "w", **profile) as dst:
                dst.write(stacked_lw)

            return True
    except Exception as e:
        print(f"Blackpixel Error: File {filepath} has the error {e}")
        raise


def blackpixel(num_workers=4, executor=None):
    """
    This function calculates water leaving radiance (Lw)
    by applying the black pixel assumption which assumes
    Lw in the NIR is negligable due to strong absorption
    of water. Therefore, total radiance (Lt) in the NIR is
    considered to be solely surface reflected light (Lsr),
    which allows rho to be calculated if sky radiance (Lsky)
    is known.
    This method should only be used for waters where
    there is little to none NIR signal (i.e. Case 1 waters).
    The assumption tends to fail in more turbid waters where
    high concentrations of particles enhance backscattering
    and Lw in the NIR (i.e. Case 2 waters).

    Parameters:
        num_workers: Number of parallelizing done on different cores. Depends on hardware.
    Returns:
        New Lw .tifs with units of W/sr/nm

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
        sky_imgs, axis=(0, 2, 3)
    )  # here we want the median of each band
    del sky_imgs

    if executor is not None:
        partial_compute = partial(
            _compute,
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
            max_workers=num_workers
        ) as executor:
            futures = {}
            for filepath in filepaths:
                future = executor.submit(_compute, filepath, lw_dir, lsky_median)
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
    return results
