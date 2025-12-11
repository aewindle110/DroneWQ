"""
Refactored by: Temuulen and Kurtis
"""

import concurrent.futures
import glob
import logging
import os
from functools import partial

import numpy as np
import rasterio

from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def __compute(filename, wq_algs, main_dir):
    """
    Apply one or more water-quality algorithms to a single Rrs raster.

    This is an internal helper function used by ``save_wq_imgs``. It loads a
    raster, runs the specified algorithms, and writes output rasters into the
    corresponding algorithm-specific directories under ``main_dir``.

    Parameters
    ----------
    filename : str
        Path to the Rrs raster file.

    wq_algs : `list[str]`
        Algorithm names to apply to this file.

    main_dir : str
        Base directory where algorithm-specific output folders are located.

    Returns
    -------
    bool
        ``True`` if processing succeeds; ``False`` if an exception occurs.

    Notes
    -----
    Output rasters:
    - Use the same geotransform, CRS, and spatial dimensions as the input.
    - Have ``float32`` dtype and ``nodata=np.nan``.
    """

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

            for wq_alg in wq_algs:
                wq_dir_name = "masked_" + wq_alg + "_imgs"
                wq_dir = os.path.join(main_dir, wq_dir_name)
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
    rrs_dir: str,
    wq_algs: list[str] = ["chl_gitelson"],
    start: int = 0,
    count: int = 10000,
    num_workers: int = 4,
    executor=None,
):
    """
    Generate and save water-quality (WQ) products from Rrs rasters.

    This function loads Rrs raster files from `rrs_dir`, applies the specified
    water-quality algorithms (e.g., chlorophyll or TSM retrieval algorithms),
    and writes the results as new GeoTIFF files in dedicated subdirectories
    under `settings.main_dir`.

    Processing is parallelized using either a provided executor or a
    ProcessPoolExecutor.

    Parameters
    ----------
    rrs_dir : str
        Directory containing input Rrs raster files.

    wq_algs : `list[str]`, optional
        List of algorithm names to apply.
        Supported values: ``"chl_hu"``, ``"chl_ocx"``, ``"chl_hu_ocx"``,
        ``"chl_gitelson"``, ``"tsm_nechad"``.
        Default is ``["chl_gitelson"]``.

    start : int, optional
        Starting index when selecting which Rrs files to process. Default is 0.

    count : int, optional
        Maximum number of images to process. Default is 10000.

    num_workers : int, optional
        Number of worker processes to use if no executor is provided.

    executor : Executor or None, optional
        External concurrent executor.
        If provided, it is used instead of creating a new ProcessPoolExecutor.

    Returns
    -------
    None
        The function writes output GeoTIFFs for each algorithm into:
        ``<main_dir>/masked_<algorithm>_imgs/``.

    Notes
    -----
    - Output filenames match the input filenames.
    - Directories are automatically created for each WQ algorithm.
    - `settings.main_dir` must be configured prior to calling this function.
    """

    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    main_dir = settings.main_dir

    for wq_alg in wq_algs:
        attribute_name = wq_alg + "_dir"
        wq_dir_name = "masked_" + wq_alg + "_imgs"
        dir_path = os.path.join(main_dir, wq_dir_name)
        setattr(settings, attribute_name, dir_path)
        # make wq_dir directory
        os.makedirs(os.path.join(main_dir, wq_dir_name), exist_ok=True)

    def _capture_path_to_int(path: str) -> int:
        return int(os.path.basename(path).split("_")[-1].split(".")[0])

    filenames = sorted(
        glob.glob(os.path.join(rrs_dir, "*")),
        key=_capture_path_to_int,
    )[start:count]

    partial_compute = partial(
        __compute,
        wq_algs=wq_algs,
        main_dir=main_dir,
    )

    if executor is not None:
        results = list(executor.map(partial_compute, filenames))
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=num_workers,
        ) as executor:
            results = list(executor.map(partial_compute, filenames))
    logger.info(
        "WQ Stage: Successfully processed: %d/%d captures",
        sum(results),
        len(results),
    )


def chl_hu(Rrs):
    """
    Compute chlorophyll-a using the Hu et al. (2012) Color Index (CI) algorithm.

    This three-band reflectance difference algorithm is recommended for very low
    chlorophyll concentrations (< 0.15 mg m⁻³). See:
    https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/

    Parameters
    ----------
    Rrs : numpy.ndarray
        Array of remote-sensing reflectances with shape ``(bands, height, width)``.
        Expected bands: blue, green, red.

    Returns
    -------
    numpy.ndarray
        Chlorophyll-a estimate (mg m⁻³).
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
    Compute chlorophyll-a using the O'Reilly OCx band-ratio algorithm.

    Implements a fourth-order polynomial relationship using the OC2 coefficients
    for Landsat-8 (O'Reilly et al., 1998). Best suited for chlorophyll levels
    above ~0.2 mg m⁻³.

    Documentation:
    https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/

    Parameters
    ----------
    Rrs : numpy.ndarray
        Array of reflectances with shape ``(bands, height, width)``.
        Expected bands: blue, green.

    Returns
    -------
    numpy.ndarray
        Chlorophyll-a estimate (mg m⁻³).
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
    Compute chlorophyll-a using the blended NASA CI/OCx algorithm.

    This algorithm blends the Hu Color Index (chl_hu) and OCx (chl_ocx)
    algorithms using a threshold-based transition region:
    - CI dominates below 0.15 mg m⁻³
    - OCx dominates above 0.20 mg m⁻³
    - Linear blend in the transition region

    Implementation follows the NASA HyperInSPACE reference:
    https://www.earthdata.nasa.gov/apt/documents/chlor-a/v1.0

    Parameters
    ----------
    Rrs : numpy.ndarray
        Reflectance array of shape ``(bands, height, width)``.

    Returns
    -------
    numpy.ndarray
        Chlorophyll-a estimate (mg m⁻³).
    """

    # Thresholds from NASA specs (mg m^-3)
    lo, hi = 0.15, 0.20

    # Compute both algorithms
    ChlCI = chl_hu(Rrs)
    OCX = chl_ocx(Rrs)

    # Allocate output
    chlor_a = np.zeros_like(ChlCI, dtype=np.float32)

    # Masks
    mask_low = ChlCI < lo
    mask_high = ChlCI > hi
    mask_mid = (~mask_low) & (~mask_high)

    # Apply logic
    chlor_a[mask_low] = ChlCI[mask_low]
    chlor_a[mask_high] = OCX[mask_high]

    # Linear blend in transition zone
    if np.any(mask_mid):
        w = (ChlCI[mask_mid] - lo) / (hi - lo)
        chlor_a[mask_mid] = OCX[mask_mid] * w + ChlCI[mask_mid] * (1 - w)

    return chlor_a


def chl_gitelson(Rrs):
    """
    Compute chlorophyll-a using the Gitelson et al. (2007) two-band algorithm.

    Designed primarily for optically complex (Case-2) waters and uses the red
    and red-edge bands.

    Reference:
    Gitelson et al., 2007. doi:10.1016/j.rse.2007.01.016

    Parameters
    ----------
    Rrs : numpy.ndarray
        Reflectance array of shape ``(bands, height, width)``.
        Expected bands: red, red-edge.

    Returns
    -------
    numpy.ndarray
        Chlorophyll-a concentration (mg m⁻³).
    """

    Rrsred = Rrs[2, :, :]
    Rrsrededge = Rrs[3, :, :]

    chl = 59.826 * (Rrsrededge / Rrsred) - 17.546
    return chl


######## TSM retrieval algs ######


def tsm_nechad(Rrs):
    """
    Estimate Total Suspended Matter (TSM) using the Nechad et al. (2010) algorithm.

    Uses a semi-empirical relationship based on red-band reflectance.

    Reference:
    Nechad et al., 2010. doi:10.1016/j.rse.2009.11.022

    Parameters
    ----------
    Rrs : numpy.ndarray
        Reflectance array of shape ``(bands, height, width)``.
        Expected band: red.

    Returns
    -------
    numpy.ndarray
        TSM concentration (mg m⁻³).
    """

    Rrsred = Rrs[2, :, :]
    A = 374.11
    B = 1.61
    C = 17.38

    tsm = (A * Rrsred / (1 - (Rrsred / C))) + B
    return tsm
