import random
import numpy as np
import glob
import rasterio
import os
from dronewq.utils.settings import settings


def hedley(random_n=10):
    """
    This function calculates water leaving radiance (Lw) by modelling a constant 'ambient' NIR brightness level which is removed from all pixels across all bands. An ambient NIR level is calculated by averaging the minimum 10% of Lt(NIR) across a random subset images. This value represents the NIR brightness of a pixel with no sun glint. A linear relationship between Lt(NIR) amd the visible bands (Lt) is established, and for each pixel, the slope of this line is multiplied by the difference between the pixel NIR value and the ambient NIR level.

    Parameters:
        random_n: The amount of random images to calculate ambient NIR level. Default is 10.

    Returns:
         New Lw .tifs with units of W/sr/nm

    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    lt_dir = settings.lt_dir
    lw_dir = settings.lw_dir

    lt_all = []

    rand = random.sample(
        glob.glob(lt_dir + "/*.tif"), random_n
    )  # open random n files. n is selected by user in process_raw_to_rrs
    for im in rand:
        with rasterio.open(im, "r") as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_all.append(lt)

    stacked_lt = np.stack(lt_all)
    stacked_lt_reshape = stacked_lt.reshape(
        *stacked_lt.shape[:-2], -1
    )  # flatten last two dims

    # apply linear regression between NIR and visible bands
    min_lt_NIR = []
    for i in range(len(rand)):
        min_lt_NIR.append(
            np.percentile(stacked_lt_reshape[i, 4, :], 0.1)
        )  # calculate minimum 10% of Lt(NIR)
    mean_min_lt_NIR = np.mean(min_lt_NIR)  # take mean of minimum 10% of random Lt(NIR)

    all_slopes = []
    for i in range(len(glob.glob(lt_dir + "/*.tif"))):
        im = glob.glob(lt_dir + "/*.tif")[i]
        im_name = os.path.basename(
            im
        )  # we're grabbing just the .tif file name instead of the whole path
        with rasterio.open(im, "r") as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_reshape = lt.reshape(*lt.shape[:-2], -1)  # flatten last two dims

        lw_all = []
        for j in range(0, 5):
            slopes = np.polyfit(lt_reshape[4, :], lt_reshape[j, :], 1)[
                0
            ]  # calculate slope between NIR and all bands of random files
            all_slopes.append(slopes)

            # calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
            lw = lt[j, :, :] - all_slopes[j] * (lt[4, :, :] - mean_min_lt_NIR)
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all)  # stack into np.array
        profile["count"] = 5

        # write new stacked Rrs tif w/ reflectance units
        with rasterio.open(os.path.join(lw_dir, im_name), "w", **profile) as dst:
            dst.write(stacked_lw)
    return True
