import glob
import rasterio
import numpy as np
import os
import dronewq
import logging
import concurrent.futures
from functools import partial
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def _compute(filepath, rho, lsky_median, lw_dir):
    """Worker function that processes a single file."""
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
        logger.warn(
            "File %s failed: %s",
            filepath,
            str(e),
        )
        raise

    return filepath


def mobley_rho(rho=0.028, executor=None, num_workers=4):
    """
    This function calculates water leaving radiance (Lw)
    by multiplying a single (or small set of) sky radiance (Lsky)
    images by a single rho value. The default is rho = 0.028,
    which is based off recommendations described in Mobley, 1999.
    This approach should only be used if sky conditions are not
    changing substantially during the flight and winds are less than 5 m/s.

    Parameters:
        rho: The effective sea-surface reflectance of a wave facet. Default is 0.028
        executor: Worker pool executor
        num_workers: Number of parallel processes. Depends on hardware.

    Returns:
        New Lw .tifs with units of W/sr/nm
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
        sky=True,
    )

    sky_imgs = np.array(list(sky_imgs_gen))

    lsky_median = np.median(sky_imgs, axis=(0, 2, 3))
    del sky_imgs  # Free up memory

    # Process each Lt image
    filepaths = glob.glob(lt_dir + "/*.tif")

    if executor is not None:
        partial_compute = partial(
            _compute,
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
                    _compute,
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
                    logger.warn(
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
    return results
