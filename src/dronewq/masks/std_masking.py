from dronewq.utils.settings import settings
from dronewq.utils.images import load_imgs
import glob
import os
import numpy as np
import rasterio
import logging
from functools import partial
import concurrent.futures

logger = logging.getLogger(__name__)


def _compute(
    filepath,
    masked_rrs_dir,
    rrs_nir_mean,
    rrs_nir_std,
    mask_std_factor,
):
    im = filepath
    try:
        with rasterio.open(im, "r") as rrs_src:
            profile = rrs_src.profile
            profile["count"] = 5
            rrs_deglint_all = []
            rrs_nir_deglint = rrs_src.read(5)  # nir band
            rrs_nir_deglint[
                rrs_nir_deglint > (rrs_nir_mean + rrs_nir_std * mask_std_factor)
            ] = np.nan
            nan_index = np.isnan(rrs_nir_deglint)
            # filter nan pixel indicies across all bands
            for i in range(1, 6):
                rrs_deglint = rrs_src.read(i)
                rrs_deglint[nan_index] = np.nan
                rrs_deglint_all.append(rrs_deglint)  # append all for each band
            stacked_rrs_deglint = np.stack(rrs_deglint_all)  # stack into np.array
            # write new stacked tifs
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(
                os.path.join(masked_rrs_dir, im_name), "w", **profile
            ) as dst:
                dst.write(stacked_rrs_deglint)
    except Exception as e:
        logger.warn(
            "Threshold Masking error: File %s has failed with error %s",
            filepath,
            str(e),
        )
        raise


def std_masking(num_images=10, mask_std_factor=1, num_workers=4, executor=None):
    """
    This function masks pixels based on a user supplied value in
    an effort to remove instances of specular sun glint. The mean
    and standard deviation of NIR values from the first N images
    is calculated and any pixels containing an
    NIR value > mean + std*mask_std_factor is masked across all bands.
    The lower the mask_std_factor, the more pixels will be masked.

    Parameters:
        num_images: Number of images in the dataset to calculate
            the mean and std of NIR. Default is 10.

        mask_std_factor: A factor to multiply to the standard deviation
            of NIR values. Default is 1.

        num_workers: Number of parallelizing done on different cores.
            Depends on hardware.

    Returns:
        New masked .tifs

    """

    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    rrs_dir = settings.rrs_dir
    masked_rrs_dir = settings.masked_rrs_dir

    # grab the first num_images images, finds the mean and std of NIR, then anything times the glint factor is classified as glint
    rrs_imgs_gen = load_imgs(
        rrs_dir,
        count=num_images,
        start=0,
        altitude_cutoff=0,
        random=True,
    )
    rrs_imgs = np.array(list(rrs_imgs_gen))
    rrs_nir_mean = np.nanmean(rrs_imgs, axis=(0, 2, 3))[4]  # mean of NIR band
    rrs_nir_std = np.nanstd(rrs_imgs, axis=(0, 2, 3))[4]  # std of NIR band
    logger.info(
        "The mean and std of Rrs from first N images is: %d, %d",
        rrs_nir_mean,
        rrs_nir_std,
    )
    logger.info(
        "Pixels will be masked where Rrs(NIR) > %d",
        rrs_nir_mean + rrs_nir_std * mask_std_factor,
    )
    del rrs_imgs  # free up the memory

    # go through each Rrs image in the dir and mask any pixels > mean+std*glint factor
    filepaths = glob.glob(rrs_dir + "/*.tif")

    partial_compute = partial(
        _compute,
        masked_rrs_dir=masked_rrs_dir,
        rrs_nir_mean=rrs_nir_mean,
        rrs_nir_std=rrs_nir_std,
        mask_std_factor=mask_std_factor,
    )

    if executor is not None:
        results = list(executor.map(partial_compute, filepaths))
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers
        ) as executor:
            results = list(executor.map(partial_compute, filepaths))

    logger.info(
        "Masking Stage (std): Successfully processed: %d captures",
        len(results),
    )
    return results
