from dronewq.utils.settings import settings
from functools import partial
import concurrent.futures
import numpy as np
import rasterio
import logging
import glob
import os

logger = logging.getLogger(__name__)


def _compute(filename, wq_alg, wq_dir):
    algorithms = {
        "chl_hu": chl_hu,
        "chl_ocx": chl_ocx,
        "chl_hu_ocx": chl_hu_ocx,
        "chl_gitelson": chl_gitelson,
        "tsm_nechad": tsm_nechad,
    }
    try:
        with rasterio.open(filename, "r") as src:
            # Copy geotransform if it exists
            profile = src.profile
            rrs = np.squeeze(src.read())
            profile.update(dtype=rasterio.float32, count=1, nodata=np.nan)

            wq = algorithms[wq_alg](rrs)

            with rasterio.open(
                os.path.join(wq_dir, os.path.basename(filename)),
                "w",
                **profile,
            ) as dst:
                dst.write(wq, 1)
        return True
    except Exception as e:
        logger.error(
            "File %s: %s using algorithm %s",
            filename,
            str(e),
            wq_alg,
        )
        return False


def save_wq_imgs(
    rrs_dir,
    wq_alg="chl_gitelson",
    start=0,
    count=10000,
    num_workers=4,
    executor=None,
):
    """
    This function saves new .tifs with units of chl (ug/L) or TSM (mg/m3).

    Parameters:
        rrs_dir: A string containing directory of Rrs images

        wq_alg: what wq algorithm to apply

        start: The image to start loading from. Default is 0.

        count: The amount of images to load. Default is 10000

    Returns:
        New georeferenced .tifs with same units of images in img_dir
    """

    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    main_dir = settings.main_dir
    wq_dir_name = "masked_" + wq_alg + "_imgs"
    dir_path = os.path.join(main_dir, wq_dir_name)
    attribute_name = wq_alg + "_dir"

    setattr(settings, attribute_name, dir_path)

    def _capture_path_to_int(path: str) -> int:
        return int(os.path.basename(path).split("_")[-1].split(".")[0])

    filenames = sorted(
        glob.glob(os.path.join(rrs_dir, "*")),
        key=_capture_path_to_int,
    )[start:count]

    # make wq_dir directory
    if not os.path.exists(os.path.join(main_dir, wq_dir_name)):
        os.makedirs(os.path.join(main_dir, wq_dir_name))

    partial_compute = partial(
        _compute,
        wq_alg=wq_alg,
        wq_dir=dir_path,
    )

    if executor is not None:
        results = list(executor.map(partial_compute, filenames))
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            results = list(executor.map(partial_compute, filenames))
    logger.info(
        "WQ Stage (%s): Successfully processed: %d/%d captures",
        wq_alg,
        sum(results),
        len(results),
    )


def chl_hu(Rrs):
    """
    This is the Ocean Color Index (CI) three-band reflectance difference algorithm (Hu et al. 2012). This should only be used for chlorophyll retrievals below 0.15 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. doi: 10.1029/2011jc007395

    Parameters:
        Rrs: Takes in a numpy array of shape (bands, width, height).

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).

    """
    Rrsblue = Rrs[0, :, :]
    Rrsgreen = Rrs[1, :, :]
    Rrsred = Rrs[2, :, :]

    ci1 = -0.4909
    ci2 = 191.6590

    CI = Rrsgreen - (Rrsblue + (560 - 475) / (668 - 475) * (Rrsred - Rrsblue))
    ChlCI = 10 ** (ci1 + ci2 * CI)
    return ChlCI


def chl_ocx(Rrs):
    """
    This is the OCx algorithm which uses a fourth-order polynomial relationship (O'Reilly et al. 1998). This should be used for chlorophyll retrievals above 0.2 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. The coefficients for OC2 (OLI/Landsat 8) are used as default. doi: 10.1029/98JC02160.

    Parameters:
        Rrs: Takes in a numpy array of shape (bands, width, height).

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).

    """
    Rrsblue = Rrs[0, :, :]
    Rrsgreen = Rrs[1, :, :]

    # L8 OC2 coefficients
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    temp = np.log10(Rrsblue / Rrsgreen)

    log10chl = a0 + a1 * (temp) + a2 * (temp) ** 2 + a3 * (temp) ** 3 + a4 * (temp) ** 4

    ocx = np.power(10, log10chl)
    return ocx


def chl_hu_ocx(Rrs):
    """
    This is the blended NASA chlorophyll algorithm which combines Hu color index (CI) algorithm (chl_hu) and the O'Reilly band ratio OCx algortihm (chl_ocx). This specific code is grabbed from https://github.com/nasa/HyperInSPACE. Documentation can be found here https://www.earthdata.nasa.gov/apt/documents/chlor-a/v1.0#introduction.

    Parameters:
        Rrs: Takes in a numpy array of shape (bands, width, height).

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """
    thresh = [0.15, 0.20]

    # Compute both algorithms
    ChlCI = chl_hu(Rrs)
    ocx = chl_ocx(Rrs)

    if ChlCI.any() <= thresh[0]:
        chlor_a = ChlCI
    elif ChlCI.any() > thresh[1]:
        chlor_a = ocx
    else:
        chlor_a = ocx * (ChlCI - thresh[0]) / (thresh[1] - thresh[0]) + ChlCI * (
            thresh[1] - ChlCI
        ) / (thresh[1] - thresh[0])

    return chlor_a


def chl_gitelson(Rrs):
    """
    This algorithm estimates chlorophyll a concentrations using a 2-band algorithm with coefficients from Gitelson et al. 2007. This algorithm is recommended for coastal (Case 2) waters. doi:10.1016/j.rse.2007.01.016

    Parameters:
        Rrs: Takes in a numpy array of shape (bands, width, height).

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """
    Rrsred = Rrs[2, :, :]
    Rrsrededge = Rrs[3, :, :]

    chl = 59.826 * (Rrsrededge / Rrsred) - 17.546
    return chl


######## TSM retrieval algs ######


def tsm_nechad(Rrs):
    """
    This algorithm estimates total suspended matter (TSM) concentrations using the Nechad et al. (2010) algorithm. doi:10.1016/j.rse.2009.11.022

    Parameters:
        Rrs: Takes in a numpy array of shape (bands, width, height).

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """
    Rrsred = Rrs[2, :, :]
    A = 374.11
    B = 1.61
    C = 17.38

    tsm = (A * Rrsred / (1 - (Rrsred / C))) + B
    return tsm
