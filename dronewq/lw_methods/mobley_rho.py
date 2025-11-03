import glob
import rasterio
import numpy as np
import os
import dronewq
import concurrent.futures
from dronewq.utils.settings import settings

# Global variables for worker processes
_lw_dir = None
_rho = None
_lsky_median = None


def _init_worker(lw_dir, rho, lsky_median):
    """Initialize worker process with shared data."""
    global _lw_dir, _rho, _lsky_median
    _lw_dir = lw_dir
    _rho = rho
    _lsky_median = lsky_median


def _compute(filepath):
    """Worker function that processes a single file."""
    with rasterio.open(filepath, "r") as Lt_src:
        profile = Lt_src.profile
        profile["count"] = 5
        lw_all = []
        for i in range(1, 6):
            lt = Lt_src.read(i)
            lw = lt - (_rho * _lsky_median[i - 1])
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all)

        # Write new stacked lw tifs
        im_name = os.path.basename(filepath)
        output_path = os.path.join(_lw_dir, im_name)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(stacked_lw)

    return filepath


def mobley_rho(rho=0.028, num_workers=4):
    """
    This function calculates water leaving radiance (Lw) by multiplying a single (or small set of) sky radiance (Lsky) images by a single rho value. The default is rho = 0.028, which is based off recommendations described in Mobley, 1999. This approach should only be used if sky conditions are not changing substantially during the flight and winds are less than 5 m/s.

    Parameters:
        rho: The effective sea-surface reflectance of a wave facet. Default is 0.028
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
    sky_imgs, sky_img_metadata = dronewq.retrieve_imgs_and_metadata(
        sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True
    )
    lsky_median = np.median(sky_imgs, axis=(0, 2, 3))
    del sky_imgs  # Free up memory

    # Process each Lt image
    filepaths = glob.glob(lt_dir + "/*.tif")

    # Pass all shared data through initializer
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers,
        initializer=_init_worker,
        initargs=(lw_dir, rho, lsky_median),
    ) as executor:
        results = list(executor.map(_compute, filepaths))

    print(f"Processed {len(results)} files successfully")
    return results
