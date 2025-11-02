import glob
import rasterio
import numpy as np
import os
import dronewq
import concurrent.futures
from dronewq.utils.settings import settings


def _compute(filepath, rho, lsky_median):
    lw_dir = settings.lw_dir
    im = filepath
    with rasterio.open(im, "r") as Lt_src:
        profile = Lt_src.profile
        profile["count"] = 5
        lw_all = []
        for i in range(1, 6):
            # todo this is probably faster if we read them all and divide by the vector
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


def mobley_rho(rho=0.028, num_workers=4):
    """
    This function calculates water leaving radiance (Lw) by multiplying a single (or small set of) sky radiance (Lsky) images by a single rho value. The default is rho = 0.028, which is based off recommendations described in Mobley, 1999. This approach should only be used if sky conditions are not changing substantially during the flight and winds are less than 5 m/s.

    Parameters:
        rho = The effective sea-surface reflectance of a wave facet. The default 0.028

        num_workers: Number of parallelizing done on different cores. Depends on hardware.

    Returns:
        New Lw .tifs with units of W/sr/nm
    """

    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    sky_lt_dir = settings.sky_lt_dir
    lt_dir = settings.lt_dir

    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = dronewq.retrieve_imgs_and_metadata(
        sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True
    )
    lsky_median = np.median(
        sky_imgs, axis=(0, 2, 3)
    )  # here we want the median of each band
    del sky_imgs  # free up the memory

    # go through each Lt image in the dir and subtract out rho*lsky to account for sky reflection
    filepaths = glob.glob(lt_dir + "/*.tif")
    args = [(filepath, rho, lsky_median) for filepath in filepaths]

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        executor.map(_compute, args)
