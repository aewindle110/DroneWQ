from dronewq.utils.settings import settings
from micasense import imageset
from pathlib import Path
import concurrent.futures
import logging
import dronewq
import shutil
import os

logger = logging.getLogger(__name__)


def process_raw_to_rrs(
    output_csv_path: str,
    lw_method="mobley_rho_method",
    random_n=10,
    pixel_masking_method=None,
    mask_std_factor=1,
    nir_threshold=0.01,
    green_threshold=0.005,
    ed_method="dls_ed",
    overwrite_lt_lw=False,
    clean_intermediates=True,
    num_workers=4,
):
    """
    This functions is the main processing script that processs raw
    imagery to units of remote sensing reflectance (Rrs). Users can
    select which processing parameters to use to calculate Rrs.

    Parameters:
        output_csv_path: A string containing the filepath to write
            the metadata.csv

        lw_method: Method used to calculate water leaving radiance.
            Default is mobley_rho_method().

        random_n: The amount of random images to calculate ambient
            NIR level. Default is 10. Only need if lw_method = 'hedley_method'

        pixel_masking_method: Method to mask pixels. Options are
            'value_threshold', 'std_threshold', or None. Default is None.

        mask_std_factor: A factor to multiply to the standard
            deviation of NIR values. Default is 1.
            Only need if pixel_masking_method = 'std_threshold'

        nir_threshold: An Rrs(NIR) value where pixels above this
            will be masked. These are usually pixels of specular
            sun glint or land features.
            Only need if pixel_masking_method = 'value_threshold'.
            Default is 0.01.

        green_threshold: A Rrs(green) value where pixels below this
            will be masked. Default is 0.005. These are usually pixels
            of vegetation shadowing.
            Only need if pixel_masking_method = 'value_threshold'.

        ed_method: Method used to calculate downwelling irradiance (Ed).
            Default is dls_ed().

        overwrite_lt_lw: Option to overwrite lt and lw files that have
            been written previously.
            Default is False but this is only applied to the Lt images.

        clean_intermediates: Option to erase intermediates of
            processing (Lt, Lw, unmasked Rrs)

        num_workers: Number of parallelizing done on different cores.
            Depends on hardware.

    Returns:
        New Rrs tifs (masked or unmasked) with units of sr^-1.
    """
    ############################
    #### setup the workspace ###
    ############################

    if settings.main_dir is None:
        msg = "Please set the main_dir path."
        raise LookupError(msg)

    raw_water_img_dir = settings.raw_water_dir

    lt_dir = settings.lt_dir
    sky_lt_dir = settings.sky_lt_dir
    lw_dir = settings.lw_dir
    rrs_dir = settings.rrs_dir
    masked_rrs_dir = settings.masked_rrs_dir
    warp_img_dir = settings.warp_img_dir

    # make all these directories if they don't already exist
    all_dirs = [lt_dir, lw_dir, rrs_dir]
    for directory in all_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)

    if pixel_masking_method:
        Path(masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    files = os.listdir(raw_water_img_dir)  # your directory path
    num_bands = imageset.ImageSet.from_directory(warp_img_dir).captures[0].num_bands

    logger.info(
        "Processing a total of %d images or %d captures.",
        len(files),
        round(len(files) / num_bands),
    )

    # convert raw imagery to radiance (Lt)
    logger.info("Converting raw images to radiance (raw -> Lt).")
    dronewq.process_micasense_images(
        warp_img_dir=warp_img_dir,
        overwrite_lt_lw=overwrite_lt_lw,
        sky=False,
    )

    # deciding if we need to process raw sky images to radiance
    if lw_method in ["mobley_rho", "blackpixel"]:
        logger.info("Converting raw sky images to radiance (raw sky -> Lsky).")
        # we're also making an assumption that we don't need to align/warp
        # these images properly because they'll be medianed
        dronewq.process_micasense_images(
            warp_img_dir=None,
            overwrite_lt_lw=overwrite_lt_lw,
            sky=True,
        )

    ##################################
    ### correct for surface reflected light ###
    ##################################

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers,
    ) as Executor:
        if lw_method == "mobley_rho":
            logger.info("Applying the mobley_rho_method (Lt -> Lw).")
            dronewq.mobley_rho(num_workers=num_workers, executor=Executor)

        elif lw_method == "blackpixel":
            logger.info("Applying the blackpixel_method (Lt -> Lw)")
            dronewq.blackpixel(num_workers=num_workers, executor=Executor)

        elif lw_method == "hedley":
            logger.info("Applying the Hochberg/Hedley (Lt -> Lw)")
            dronewq.hedley(
                random_n,
                num_workers=num_workers,
                executor=Executor,
            )
        # just change this pointer if we didn't do anything
        # the lt over to the lw dir
        else:
            logger.info("Not doing any Lw calculation.")
            lw_dir = lt_dir

        #####################################
        ### normalize Lw by Ed to get Rrs ###
        #####################################

        if ed_method == "panel_ed":
            logger.info("Normalizing by panel irradiance (Lw/Ed -> Rrs).")
            dronewq.panel_ed(output_csv_path, num_workers=num_workers)

        elif ed_method == "dls_ed":
            logger.info("Normalizing by DLS irradiance (Lw/Ed -> Rrs).")
            dronewq.dls_ed(
                output_csv_path,
                num_workers=num_workers,
                executor=Executor,
            )

        elif ed_method == "dls_and_panel_ed":
            logger.info(
                "Normalizing by DLS corrected by panel irradiance (Lw/Ed -> Rrs)."
            )
            dronewq.dls_ed(
                output_csv_path,
                dls_corr=True,
                num_workers=num_workers,
                executor=Executor,
            )

        else:
            logger.info(
                "No other irradiance normalization methods implemented yet, panel_ed is recommended."
            )
            return False

        logger.info(
            "All data has been saved as Rrs using the %s to\
            calculate Lw and normalized by %s irradiance.",
            str(lw_method),
            str(ed_method),
        )

        ########################################
        ### mask pixels in the imagery (from glint, vegetation, shadows) ###
        ########################################
        if pixel_masking_method == "value_threshold":
            logger.info("Masking pixels using NIR and green Rrs thresholds")
            dronewq.threshold_masking(
                nir_threshold=nir_threshold,
                green_threshold=green_threshold,
                num_workers=num_workers,
                executor=Executor,
            )
        elif pixel_masking_method == "std_threshold":
            logger.info("Masking pixels using std Rrs(NIR)")
            dronewq.std_masking(
                mask_std_factor=mask_std_factor,
                num_workers=num_workers,
                executor=Executor,
            )

        else:  # if we don't do the glint correction then just change the pointer to the lt_dir
            logger.info("Not masking pixels.")

    ################################################
    ### finalize and add point output ###
    ################################################

    if clean_intermediates:
        dirs_to_delete = [lt_dir, sky_lt_dir, lw_dir]
        for d in dirs_to_delete:
            shutil.rmtree(d, ignore_errors=True)
        logger.info("Deleted intermediate results.")
