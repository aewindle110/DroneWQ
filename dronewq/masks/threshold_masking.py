import glob
import os
import numpy as np
import rasterio
from dronewq.utils.settings import settings


def threshold_masking(nir_threshold=0.01, green_threshold=0.005):
    """
    This function masks pixels based on user supplied Rrs thresholds in an effort to remove instances of specular sun glint, shadowing, or adjacent land when present in the images.

    Parameters:
        nir_threshold: An Rrs(NIR) value where pixels above this will be masked. Default is 0.01. These are usually pixels of specular sun glint or land features.

        green_threshold: A Rrs(green) value where pixels below this will be masked. Default is 0.005. These are usually pixels of vegetation shadowing.

    Returns:
        New masked Rrs.tifs with units of sr^-1

    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    rrs_dir = settings.rrs_dir
    masked_rrs_dir = settings.masked_rrs_dir

    # go through each rrs image in the dir and mask pixels > nir_threshold and < green_threshold
    for im in glob.glob(rrs_dir + "/*.tif"):
        with rasterio.open(im, "r") as rrs_src:
            profile = rrs_src.profile
            profile["count"] = 5
            rrs_mask_all = []
            nir = rrs_src.read(5)
            green = rrs_src.read(2)
            nir[nir > nir_threshold] = np.nan
            green[green < green_threshold] = np.nan

            nir_nan_index = np.isnan(nir)
            green_nan_index = np.isnan(green)

            # filter nan pixel indicies across all bands
            for i in range(1, 6):

                rrs_mask = rrs_src.read(i)
                rrs_mask[nir_nan_index] = np.nan
                rrs_mask[green_nan_index] = np.nan

                rrs_mask_all.append(rrs_mask)

            stacked_rrs_mask = np.stack(rrs_mask_all)  # stack into np.array

            # write new stacked rrs tifs
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(
                os.path.join(masked_rrs_dir, im_name), "w", **profile
            ) as dst:
                dst.write(stacked_rrs_mask)

    return True

