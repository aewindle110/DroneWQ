from micasense import imageset
import numpy as np
import pandas as pd
import glob
import rasterio
import os
import concurrent.futures
from dronewq.utils.settings import settings


def _compute(im, idx, ed_data):
    rrs_dir = settings.rrs_dir
    with rasterio.open(im, "r") as Lw_src:
        profile = Lw_src.profile
        profile["count"] = 5
        rrs_all = []
        # could vectorize this for speed
        for i in range(1, 6):
            lw = Lw_src.read(i)
            rrs = lw / ed_data[idx][i]
            rrs_all.append(rrs)  # append each band
        stacked_rrs = np.stack(rrs_all)  # stack into np.array

        # write new stacked Rrs tifs w/ Rrs units
        im_name = os.path.basename(
            im
        )  # we're grabbing just the .tif file name instead of the whole path
        with rasterio.open(os.path.join(rrs_dir, im_name), "w", **profile) as dst:
            dst.write(stacked_rrs)


def dls_ed(output_csv_path, dls_corr=False, num_workers=4):
    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is derived from the downwelling light sensor (DLS), which is collected at every image capture. This method does not perform well when light is variable such as partly cloudy days. It is recommended to use in overcast, completely cloudy conditions. A DLS correction can be optionally applied to tie together DLS and panel Ed measurements. In this case, a compensation factor derived from the calibration reflectance panel is applied to DLS Ed measurements.The default is False.


    Parameters:
        dls_corr: Option to apply compensation factor from calibration reflectance panel to DLS Ed measurements. Default is False.
        num_workers: Number of parallelizing done on different cores. Depends on hardware.

    Returns:
        New Rrs .tifs with units of sr^-1

        New .csv file with average Ed measurements (mW/m2/nm) calculated from DLS measurements
    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    panel_dir = settings.panel_dir
    lw_dir = settings.lw_dir
    raw_water_dir = settings.raw_water_dir

    ed_data = []
    dls_ed_corr_data = []
    ed_columns = ["image", "ed_475", "ed_560", "ed_668", "ed_717", "ed_842"]

    if dls_corr:
        panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures

        panel_ed_data = []
        dls_ed_data = []

        for i, capture in enumerate(panel_imgset):
            # calculate panel Ed from every panel capture
            panel_ed = (
                capture.panel_irradiance()
            )  # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise raises an error
            panel_ed[3], panel_ed[4] = panel_ed[4], panel_ed[3]  # flip last two bands
            panel_ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(panel_ed[0])]
                + [np.mean(panel_ed[1])]
                + [np.mean(panel_ed[2])]
                + [np.mean(panel_ed[3])]
                + [np.mean(panel_ed[4])]
            )  # multiply by 1000 to scale to mW (but want ed to still be in W to divide by Lw which is in W)
            panel_ed_data.append(panel_ed_row)

            # calculate DLS Ed from every panel capture
            dls_ed = capture.dls_irradiance()
            dls_ed[3], dls_ed[4] = (
                dls_ed[4],
                dls_ed[3],
            )  # flip last two bands (red edge and NIR)
            dls_ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(dls_ed[0] * 1000)]
                + [np.mean(dls_ed[1] * 1000)]
                + [np.mean(dls_ed[2] * 1000)]
                + [np.mean(dls_ed[3] * 1000)]
                + [np.mean(dls_ed[4] * 1000)]
            )  # multiply by 1000 to scale to mW
            dls_ed_data.append(dls_ed_row)

        dls_ed_corr = np.array(panel_ed) / (np.array(dls_ed[0:5]) * 1000)

        # this is the DLS ed corrected by the panel correction factor
        capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
        for i, capture in enumerate(capture_imgset):
            ed = capture.dls_irradiance()
            ed = (ed[0:5] * dls_ed_corr) * 1000
            ed = np.append(ed, [0])  # add zero because other ed ends with a 0
            dls_ed_corr_row = (
                ["capture_" + str(i + 1)]
                + [ed[0]]
                + [ed[1]]
                + [ed[2]]
                + [ed[3]]
                + [ed[4]]
            )
            dls_ed_corr_data.append(dls_ed_corr_row)

        dls_ed_corr_data_df = pd.DataFrame.from_records(
            dls_ed_corr_data, index="image", columns=ed_columns
        )
        dls_ed_corr_data_df.to_csv(os.path.join(output_csv_path, "dls_corr_ed.csv"))

        del dls_ed_corr_data_df

    else:
        capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
        for i, capture in enumerate(capture_imgset):
            ed = capture.dls_irradiance()
            ed[3], ed[4] = ed[4], ed[3]  # flip last two bands (red edge and NIR)
            ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(ed[0] * 1000)]
                + [np.mean(ed[1] * 1000)]
                + [np.mean(ed[2] * 1000)]
                + [np.mean(ed[3] * 1000)]
                + [np.mean(ed[4] * 1000)]
            )  # multiply by 1000 to scale to mW
            ed_data.append(ed_row)

        ed_data_df = pd.DataFrame.from_records(
            ed_data, index="image", columns=ed_columns
        )
        ed_data_df.to_csv(os.path.join(output_csv_path, "dls_ed.csv"))

        del ed_data_df

    # now divide the lw_imagery by ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    filepaths = glob.glob(lw_dir + "/*.tif")
    ed_data = dls_ed_corr_data if dls_corr else ed_data
    args = [(filepath, idx, dls_ed_corr_data) for idx, filepath in enumerate(filepaths)]

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        executor.map(_compute, args)
