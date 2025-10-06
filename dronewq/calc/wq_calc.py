from tqdm import tqdm
from dronewq.utils.images import load_images
from dronewq.utils.settings import settings
import numpy as np
import rasterio
import glob
import os


def save_wq_imgs(wq_alg="chl_gitelson", start=0, count=10000):
    """
    This function saves new .tifs with units of chl (ug/L) or TSM (mg/m3).

    Parameters:
        main_dir: A string containing main directory

        rrs_img_dir: A string containing directory of Rrs images

        wq_dir_name: A string containing the directory that the wq images will be saved

        wq_alg: what wq algorithm to apply

        start: The image to start loading from. Default is 0.

        count: The amount of images to load. Default is 10000

    Returns:
        New georeferenced .tifs with same units of images in img_dir
    """

    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    main_dir = settings.main_dir
    rrs_img_dir = settings.rrs_dir
    wq_dir_name = wq_alg + "_img"

    def _capture_path_to_int(path: str) -> int:
        return int(os.path.basename(path).split("_")[-1].split(".")[0])

    filenames = sorted(
        glob.glob(os.path.join(main_dir, rrs_img_dir, "*")), key=_capture_path_to_int
    )[start:count]

    # make wq_dir directory
    if not os.path.exists(os.path.join(main_dir, wq_dir_name)):
        os.makedirs(os.path.join(main_dir, wq_dir_name))

    BLUE, GREEN, RED, RED_EDGE = 0, 1, 2, 3

    for filename in tqdm(filenames, total=len(filenames)):
        rrs = np.squeeze(load_images([filename]))

        if wq_alg == "chl_hu":
            wq = chl_hu(rrs[BLUE, :, :], rrs[GREEN, :, :], rrs[RED, :, :])
        elif wq_alg == "chl_ocx":
            wq = chl_ocx(rrs[BLUE, :, :], rrs[GREEN, :, :])
        elif wq_alg == "chl_hu_ocx":
            wq = chl_hu_ocx(rrs[BLUE, :, :], rrs[GREEN, :, :], rrs[RED, :, :])
        elif wq_alg == "chl_gitelson":
            wq = chl_gitelson(rrs[RED, :, :], rrs[RED_EDGE, :, :])
        elif wq_alg == "nechad_tsm":
            wq = tsm_nechad(rrs[RED, :, :])

        with rasterio.open(filename, "r") as src:
            profile = src.profile
            profile.update(dtype=rasterio.float32, count=1, nodata=np.nan)

        with rasterio.open(
            os.path.join(main_dir, wq_dir_name, os.path.basename(filename)),
            "w",
            **profile,
        ) as dst:
            dst.write(wq, 1)


def chl_hu(Rrsblue, Rrsgreen, Rrsred):
    """
    This is the Ocean Color Index (CI) three-band reflectance difference algorithm (Hu et al. 2012). This should only be used for chlorophyll retrievals below 0.15 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. doi: 10.1029/2011jc007395

    Parameters:
        Rrsblue: numpy array of Rrs in the blue band.

        Rrsgreen: numpy array of Rrs in the green band.

        Rrsred: numpy array of Rrs in the red band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).

    """

    ci1 = -0.4909
    ci2 = 191.6590

    CI = Rrsgreen - (Rrsblue + (560 - 475) / (668 - 475) * (Rrsred - Rrsblue))
    ChlCI = 10 ** (ci1 + ci2 * CI)
    return ChlCI


def chl_ocx(Rrsblue, Rrsgreen):
    """
    This is the OCx algorithm which uses a fourth-order polynomial relationship (O'Reilly et al. 1998). This should be used for chlorophyll retrievals above 0.2 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. The coefficients for OC2 (OLI/Landsat 8) are used as default. doi: 10.1029/98JC02160.

    Parameters:
        Rrsblue: numpy array of Rrs in the blue band.

        Rrsgreen: numpy array of Rrs in the green band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).

    """

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


def chl_hu_ocx(Rrsblue, Rrsgreen, Rrsred):
    """
    This is the blended NASA chlorophyll algorithm which combines Hu color index (CI) algorithm (chl_hu) and the O'Reilly band ratio OCx algortihm (chl_ocx). This specific code is grabbed from https://github.com/nasa/HyperInSPACE. Documentation can be found here https://www.earthdata.nasa.gov/apt/documents/chlor-a/v1.0#introduction.

    Parameters:
        Rrsblue: numpy array of Rrs in the blue band.

        Rrsgreen: numpy array of Rrs in the green band.

        Rrsred: numpy array of Rrs in the red band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """

    thresh = [0.15, 0.20]
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    ci1 = -0.4909
    ci2 = 191.6590

    temp = np.log10(Rrsblue / Rrsgreen)

    log10chl = a0 + a1 * (temp) + a2 * (temp) ** 2 + a3 * (temp) ** 3 + a4 * (temp) ** 4

    ocx = np.power(10, log10chl)

    CI = Rrsgreen - (Rrsblue + (560 - 475) / (668 - 475) * (Rrsred - Rrsblue))

    ChlCI = 10 ** (ci1 + ci2 * CI)

    if ChlCI.any() <= thresh[0]:
        chlor_a = ChlCI
    elif ChlCI.any() > thresh[1]:
        chlor_a = ocx
    else:
        chlor_a = ocx * (ChlCI - thresh[0]) / (thresh[1] - thresh[0]) + ChlCI * (
            thresh[1] - ChlCI
        ) / (thresh[1] - thresh[0])

    return chlor_a


def chl_gitelson(Rrsred, Rrsrededge):
    """
    This algorithm estimates chlorophyll a concentrations using a 2-band algorithm with coefficients from Gitelson et al. 2007. This algorithm is recommended for coastal (Case 2) waters. doi:10.1016/j.rse.2007.01.016

    Parameters:
        Rrsred: numpy array of Rrs in the red band.

        Rrsrededge: numpy array of Rrs in the red edge band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """

    chl = 59.826 * (Rrsrededge / Rrsred) - 17.546
    return chl


######## TSM retrieval algs ######


def tsm_nechad(Rrsred):
    """
    This algorithm estimates total suspended matter (TSM) concentrations using the Nechad et al. (2010) algorithm. doi:10.1016/j.rse.2009.11.022

    Parameters:
        Rrsred: numpy array of Rrs in the red band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """
    A = 374.11
    B = 1.61
    C = 17.38

    tsm = (A * Rrsred / (1 - (Rrsred / C))) + B
    return tsm
