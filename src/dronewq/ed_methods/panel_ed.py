"""Refactored by: Temuulen"""

import concurrent.futures
import glob
import logging
import os
from functools import partial

import numpy as np
import pandas as pd
import rasterio

from dronewq.utils.settings import settings

from ..micasense import imageset

logger = logging.getLogger(__name__)


def __compute(filepath, ed):
    """
    Process a single Lw file to compute remote sensing reflectance using panel Ed.

    Worker function that reads a water-leaving radiance (Lw) raster file,
    divides each band by the corresponding panel-derived downwelling irradiance
    (Ed) value, and writes the resulting remote sensing reflectance (Rrs) to a
    new file.

    Parameters
    ----------
    filepath : str
        Path to the input Lw raster file.
    ed : array-like
        Panel-derived downwelling irradiance values for 5 bands, indexed from 0-4.

    Notes
    -----
    The function processes 5 bands, computing Rrs = Lw / Ed for each band.
    Output files are saved to settings.rrs_dir with the same basename as input files.
    """
    im = filepath
    rrs_dir = settings.rrs_dir
    with rasterio.open(im, "r") as Lw_src:
        profile = Lw_src.profile
        profile["count"] = 5
        rrs_all = []
        # could vectorize this for speed
        for i in range(1, 6):
            lw = Lw_src.read(i)

            # NOTE: ed points to the last panel ed
            rrs = lw / ed[i - 1]
            rrs_all.append(rrs)  # append each band
        stacked_rrs = np.stack(rrs_all)  # stack into np.array

        # write new stacked Rrs tifs w/ Rrs units
        im_name = os.path.basename(
            im,
        )  # we're grabbing just the .tif file name instead of the whole path
        with rasterio.open(
            os.path.join(rrs_dir, im_name),
            "w",
            **profile,
        ) as dst:
            dst.write(stacked_rrs)


def panel_ed(output_csv_path, num_workers=4, executor=None):
    """
    Calculate remote sensing reflectance using calibrated reflectance panel.

    This function computes remote sensing reflectance (Rrs) by dividing
    water-leaving radiance (Lw) by downwelling irradiance (Ed) calculated
    from a calibrated reflectance panel. The panel is imaged during data
    collection to provide a reference for Ed measurements. This method
    performs best under clear, sunny conditions with stable lighting.

    Parameters
    ----------
    output_csv_path : str
        Directory path where the panel Ed CSV file will be saved.
    num_workers : int, optional
        Number of parallel worker processes for file processing. Should be
        tuned based on available CPU cores. Default is 4.
    executor : concurrent.futures.Executor, optional
        Pre-configured executor for parallel processing. If None, a new
        ProcessPoolExecutor will be created. Default is None.

    Returns
    -------
    None

    Raises
    ------
    LookupError
        If main_dir is not set in settings.

    Notes
    -----
    This method does not perform well under variable lighting conditions such
    as partly cloudy days. It is recommended for use on clear, sunny days with
    stable illumination.

    The function produces two types of outputs:
    - Rrs GeoTIFF files with units of sr^-1 in settings.rrs_dir
    - CSV file 'panel_ed.csv' containing average Ed measurements in mW/m^2/nm
      calculated from calibrated reflectance panel captures

    The function processes 5 spectral bands centered at approximately:
    475nm, 560nm, 668nm, 717nm, and 842nm. Note that bands 4 and 5 (717nm and
    842nm) are swapped during processing to correct band ordering.

    The panel_irradiance() method automatically finds the panel albedo and
    uses it to calculate Ed, otherwise raises an error if the panel cannot
    be detected.
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
            panels[i].panel_irradiance(),
        )
        # this function automatically finds the panel albedo
        # and uses that to calcuate Ed, otherwise raises an error
        # flip last two bands
        ed[3], ed[4] = ed[4], ed[3]
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
    ed_data = pd.DataFrame.from_records(
        ed_data,
        index="image",
        columns=ed_columns,
    )
    ed_data.to_csv(os.path.join(output_csv_path, "panel_ed.csv"))

    partial_compute = partial(__compute, ed=ed)

    if executor is not None:
        results = list(executor.map(partial_compute, filepaths))
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            results = list(executor.map(partial_compute, filepaths))

    logger.info(
        "Lw Stage (Hedley): Successfully processed: %d captures",
        len(results),
    )
