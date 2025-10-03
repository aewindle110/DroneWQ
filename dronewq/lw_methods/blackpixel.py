import numpy as np
import glob
import rasterio
import os
from dronewq.utils.settings import settings
from dronewq.utils.images import retrieve_imgs_and_metadata


def blackpixel():
    """
    This function calculates water leaving radiance (Lw) by applying the black pixel assumption which assumes Lw in the NIR is negligable due to strong absorption of water. Therefore, total radiance (Lt) in the NIR is considered to be solely surface reflected light (Lsr) , which allows rho to be calculated if sky radiance (Lsky) is known. This method should only be used for waters where there is little to none NIR signal (i.e. Case 1 waters). The assumption tends to fail in more turbid waters where high concentrations of particles enhance backscattering and Lw in the NIR (i.e. Case 2 waters).

    Returns:
        New Lw .tifs with units of W/sr/nm

    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    sky_lt_dir = settings.sky_lt_dir
    lt_dir = settings.lt_dir
    lw_dir = settings.lw_dir

    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(
        sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True
    )
    lsky_median = np.median(
        sky_imgs, axis=(0, 2, 3)
    )  # here we want the median of each band
    del sky_imgs

    for im in glob.glob(lt_dir + "/*.tif"):
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
