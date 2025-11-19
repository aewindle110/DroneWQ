import concurrent.futures
import glob
import logging
import os
from functools import partial

import numpy as np
import rasterio

from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def _compute(
    filepath,
    nir_threshold,
    green_threshold,
    masked_rrs_dir,
):
    """Worker function that masks a single file based on NIR and green thresholds."""
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
    This function masks pixels based on user supplied Rrs thresholds
    in an effort to remove instances of specular sun glint, shadowing,
    or adjacent land when present in the images.

    Parameters
        nir_threshold: An Rrs(NIR) value where pixels above this
            will be masked. Default is 0.01.
            These are usually pixels of specular sun glint or land features.

        green_threshold: A Rrs(green) value where pixels below
            this will be masked. Default is 0.005.
            These are usually pixels of vegetation shadowing.

        num_workers: Number of parallelizing done on different cores.
            Depends on hardware.

    Returns
        New masked Rrs.tifs with units of sr^-1

    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    rrs_dir = settings.rrs_dir
    masked_rrs_dir = settings.masked_rrs_dir
    filepaths = glob.glob(rrs_dir + "/*.tif")

    partial_compute = partial(
        _compute,
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
    return results
