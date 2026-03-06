"""
Refactored by: Temuulen and Kurtis
"""

import concurrent.futures
import logging
from functools import partial
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
from tqdm import tqdm

from dronewq.utils.images import get_sorted_filepaths
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def save_wq(arr: np.ndarray, output_path: Path, profile: dict):
    """Saves a 2D numpy array to band 1 of a raster file using windowed writing."""
    profile = profile.copy()
    profile["count"] = 1

    height, width = arr.shape
    chunk_size = 256

    with rasterio.open(output_path, "w", **profile) as dst:
        for row in range(0, height, chunk_size):
            for col in range(0, width, chunk_size):
                row_end = min(row + chunk_size, height)
                col_end = min(col + chunk_size, width)

                window = Window(col, row, col_end - col, row_end - row)
                window_data = arr[row:row_end, col:col_end]

                dst.write(window_data, 1, window=window)


def __compute(filename, wq_algs, main_dir):
    """Apply one or more water-quality algorithms to a single Rrs raster."""
    algorithms = {
        "chl_hu": chl_hu,
        "chl_ocx": chl_ocx,
        "chl_hu_ocx": chl_hu_ocx,
        "chl_gitelson": chl_gitelson,
        "tsm_nechad": tsm_nechad,
    }
    with rasterio.open(filename, "r") as src:
        # Copy geotransform if it exists
        profile = src.profile
        rrs = np.squeeze(src.read())
        profile.update(dtype=rasterio.float32, count=1, nodata=np.nan)

        for wq_alg in wq_algs:
            try:
                wq_dir_name = "masked_" + wq_alg + "_imgs"
                wq_dir = main_dir / wq_dir_name
                wq = algorithms[wq_alg](rrs)

                save_wq(wq, wq_dir / filename.name, profile)
            except Exception as e:
                logger.error(
                    "File %s: %s using algorithm %s",
                    filename,
                    str(e),
                    wq_alg,
                )
                return False
        return True


def save_wq_imgs(
    rrs_dir: Path | str,
    output_dir: Path | str = "",
    wq_algs: list[str] = ["chl_gitelson"],
    start: int = 0,
    count: int = 10000,
    num_workers: int = 4,
):
    """
    Generate and save water-quality (WQ) products from Rrs rasters.

    This function loads Rrs raster files from `rrs_dir`, applies the specified
    water-quality algorithms (e.g., chlorophyll or TSM retrieval algorithms),
    and writes the results as new GeoTIFF files in dedicated subdirectories
    under `settings.main_dir`.

    Parameters
    ----------
    rrs_dir : str | Path
        Directory containing input Rrs raster files.

    output_dir : str | Path, optional
        Directory to save output files. If not provided, defaults to
        `rrs_dir.parent`.

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
    """
    rrs_dir = Path(rrs_dir)

    if not rrs_dir.exists():
        raise FileNotFoundError(f"Rrs directory {rrs_dir} does not exist.")

    if not rrs_dir.is_dir():
        raise NotADirectoryError(f"Rrs directory {rrs_dir} is not a directory.")

    main_dir = rrs_dir.parent

    if output_dir:
        main_dir = Path(output_dir)
        main_dir.mkdir(parents=True, exist_ok=True)

    for wq_alg in wq_algs:
        attribute_name = wq_alg + "_dir"
        wq_dir_name = "masked_" + wq_alg + "_imgs"
        dir = main_dir / wq_dir_name
        setattr(settings, attribute_name, dir)
        # make wq_dir directory
        dir.mkdir(parents=True, exist_ok=True)

    partial_compute = partial(
        __compute,
        wq_algs=wq_algs,
        main_dir=main_dir,
    )

    filenames = get_sorted_filepaths(rrs_dir, start, count)

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers,
    ) as executor:
        results = executor.map(partial_compute, filenames)

        for _ in tqdm(results, total=len(filenames), desc="Processing images"):
            pass

    logger.info(
        "WQ Stage: Successfully processed: %d/%d captures",
        sum(results),
        len(filenames),
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

    # Compute ratio, handling cases where values cannot be log10'd
    ratio = Rrsblue / Rrsgreen
    
    # Create mask for valid values (positive, non-NaN ratios)
    valid_mask = (ratio > 0) & (~np.isnan(ratio))
    
    # Initialize output array with NaN
    temp = np.full_like(ratio, np.nan, dtype=np.float32)
    
    # Only compute log10 for valid values
    temp[valid_mask] = np.log10(ratio[valid_mask])

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
