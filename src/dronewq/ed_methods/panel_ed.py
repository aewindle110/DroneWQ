from micasense import imageset
import numpy as np
import pandas as pd
import glob
import rasterio
import os
from dronewq.utils.settings import settings


def _compute(filepath):
    im = filepath
    rrs_dir = settings.rrs_dir
    with rasterio.open(im, "r") as Lw_src:
        profile = Lw_src.profile
        profile["count"] = 5
        rrs_all = []
        # could vectorize this for speed
        for i in range(1, 6):
            lw = Lw_src.read(i)

            # FIXME: what does this ed point to?
            rrs = lw / ed[i - 1]
            rrs_all.append(rrs)  # append each band
        stacked_rrs = np.stack(rrs_all)  # stack into np.array

        # write new stacked Rrs tifs w/ Rrs units
        im_name = os.path.basename(
            im
        )  # we're grabbing just the .tif file name instead of the whole path
        with rasterio.open(os.path.join(rrs_dir, im_name), "w", **profile) as dst:
            dst.write(stacked_rrs)


def panel_ed(output_csv_path, num_workers=4, executor=None):
    """
    This function calculates remote sensing reflectance (Rrs)
    by dividing downwelling irradiance (Ed) from the water
    leaving radiance (Lw) .tifs. Ed is calculated from the
    calibrated reflectance panel. This method does not perform
    well when light is variable such as partly cloudy days.
    It is recommended to use in the case of a clear, sunny day.

    Parameters:
        lw_dir: A string containing the directory filepath of lw images

        rrs_dir: A string containing the directory filepath of new rrs images

        output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) calculated from the panel

    Returns:
        New Rrs .tifs with units of sr^-1

        New .csv file with average Ed measurements (mW/m2/nm) calculated from image cpatures of the calibrated reflectance panel

    """

    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    panel_dir = settings.panel_dir
    lw_dir = settings.lw_dir

    panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
    panels = np.array(panel_imgset)

    ed_data = []
    ed_columns = ["image", "ed_475", "ed_560", "ed_668", "ed_717", "ed_842"]

    for i in range(len(panels)):
        # calculate panel Ed from every panel capture
        ed = np.array(
            panels[i].panel_irradiance()
        )  # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise raises an error
        ed[3], ed[4] = ed[4], ed[3]  # flip last two bands
        ed_row = (
            ["capture_" + str(i + 1)]
            + [np.mean(ed[0])]
            + [np.mean(ed[1])]
            + [np.mean(ed[2])]
            + [np.mean(ed[3])]
            + [np.mean(ed[4])]
        )
        ed_data.append(ed_row)

    # now divide the lw_imagery by Ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    filepaths = glob.glob(lw_dir + "/*.tif")
    ed_data = pd.DataFrame.from_records(ed_data, index="image", columns=ed_columns)
    ed_data.to_csv(os.path.join(output_csv_path, "panel_ed.csv"))
