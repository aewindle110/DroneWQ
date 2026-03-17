import datetime
import logging
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

import dronewq
from dronewq.micasense import imageset, imageutils
from dronewq.utils.data_types import Image
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def load_imgs(
    img_dir: str | Path,
    count=10000,
    start=0,
    altitude_cutoff=0,
    random=False,
):
    """
    Load images from a directory as numpy arrays with metadata filtering.

    This function reads raster images from a specified directory and returns them
    as an iterator of numpy arrays. Images can be filtered and selected based on
    metadata criteria including count, starting position, altitude threshold, and
    random sampling. The function leverages metadata stored in a CSV file to
    efficiently select and load images.

    Parameters
    ----------
    img_dir : str | Path
        Directory path containing the images to be loaded. The directory or its
        parent must contain a 'metadata.csv' file with image information.
    count : int, optional
        Maximum number of images to load. If count exceeds the number of available
        images after filtering, all available images are loaded. Default is 10000.
    start : int, optional
        Index of the first image to load when loading sequentially (random=False).
        Zero-based indexing. Default is 0.
    altitude_cutoff : float, optional
        Minimum altitude threshold in meters. Images captured below this altitude
        are excluded. Default is 0 (no altitude filtering).
    random : bool, optional
        If True, randomly samples 'count' images from the available set. If False,
        loads images sequentially starting from 'start' index. Default is False.

    Yields
    ------
    numpy.ndarray
        3D numpy array for each image with shape (bands, height, width), where
        bands is the number of spectral bands in the raster image.

    Notes
    -----
    The function expects a 'metadata.csv' file containing at least the following columns:
    - 'filename': Name of the image file (used as index)
    - 'Altitude': Altitude at which the image was captured

    Images are loaded using rasterio, which supports various raster formats including
    GeoTIFF. The function uses lazy loading via a generator pattern to minimize
    memory usage when processing large datasets.

    The metadata CSV location is determined by:
    - If 'sky' is in img_dir: looks for metadata.csv in img_dir
    - Otherwise: looks for metadata.csv in the parent directory of img_dir

    Examples
    --------
    >>> # Load first 10 images from directory
    >>> imgs = load_imgs('/path/to/images', count=10)
    >>> for img in imgs:
    ...     print(img.shape)

    >>> # Load first 10 images without iterating
    >>> imgs = load_imgs('/path/to/images', count=10)
    >>> imgs = list(imgs)
    """
    img_dir = Path(img_dir)
    if not img_dir.exists():
        raise FileNotFoundError(f"Directory {img_dir} does not exist.")
    if not img_dir.is_dir():
        raise NotADirectoryError(f"{img_dir} is not a directory.")

    df = load_metadata(
        img_dir,
        count,
        start,
        altitude_cutoff,
        random,
    )

    img_list = [img_dir / fn for fn in df.index.values]

    for im in img_list:
        with rasterio.open(im, "r") as src:
            yield np.array(src.read())


def load_metadata(
    img_dir: str | Path,
    count=10000,
    start=0,
    altitude_cutoff=0,
    random=False,
):
    """
    Load and filter image metadata from a CSV file.

    This function reads image metadata from a CSV file and returns a filtered
    pandas DataFrame based on specified criteria including image count, starting
    position, altitude threshold, and random sampling. The metadata is used to
    efficiently select images for loading without reading the actual image files.

    Parameters
    ----------
    img_dir : str | Path
        Directory path containing the images. The directory or its parent must
        contain a 'metadata.csv' file with image information.
    count : int, optional
        Maximum number of images to include in the returned DataFrame. If count
        exceeds the number of available images, all available images are included.
        Default is 10000.
    start : int, optional
        Index of the first image to include when selecting sequentially (random=False).
        Zero-based indexing. Default is 0.
    altitude_cutoff : float, optional
        Minimum altitude threshold in meters. Images captured below this altitude
        are excluded from the DataFrame. Applied after count/start filtering.
        Default is 0 (no altitude filtering).
    random : bool, optional
        If True, randomly samples 'count' images from the available metadata.
        If False, selects images sequentially starting from 'start' index.
        Default is False.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing metadata for selected images, with 'filename' as
        the index. Only includes images meeting the altitude_cutoff criterion.

    Notes
    -----
    The function expects a 'metadata.csv' file with at least the following columns:
    - 'filename': Name of the image file (becomes DataFrame index)
    - 'Altitude': Altitude at which the image was captured (in meters)

    Additional columns may include:
    - 'UTC-Time': Timestamp of image capture
    - 'Latitude', 'Longitude': Geographic coordinates
    - Other sensor-specific metadata

    The metadata CSV location is determined by:
    - If 'sky' appears in img_dir path: looks for metadata.csv in img_dir
    - Otherwise: looks for metadata.csv in the parent directory of img_dir

    This logic accommodates directory structures where sky images may have
    separate metadata from water/ground images.

    The filtering order is:
    1. Load full metadata CSV
    2. Set filename as index
    3. Apply count and start (or random sampling)
    4. Apply altitude_cutoff filter

    Examples
    --------
    >>> # Load metadata for first 50 images
    >>> df = load_metadata('/path/to/images', count=50)
    >>> print(df.columns)

    >>> # Load metadata for random sample with altitude filter
    >>> df = load_metadata('/path/to/images', count=100, altitude_cutoff=15, random=True)
    >>> print(f"Selected {len(df)} images above 15m altitude")

    >>> # Load metadata starting from image 20
    >>> df = load_metadata('/path/to/images', count=30, start=20)
    >>> filenames = df.index.tolist()

    >>> # Get all available metadata with altitude filter
    >>> df = load_metadata('/path/to/images', altitude_cutoff=10)
    >>> print(f"Mean altitude: {df['Altitude'].mean():.2f}m")
    """
    img_dir = Path(img_dir)

    if "sky" in str(img_dir):
        base = img_dir
    else:
        base = img_dir.parent

    csv_path = base / "metadata.csv"

    df = pd.read_csv(csv_path)
    df = df.set_index("filename")
    count = min(count, len(df))
    # df['UTC-Time'] = pd.to_datetime(df['UTC-Time'])
    # cut off if necessary
    df = (
        df.iloc[start : start + count]
        if not random
        else df.loc[np.random.choice(df.index, count)]
    )

    # apply altitiude threshold and set IDs as the indez
    df = df[df["Altitude"] > altitude_cutoff]

    return df


def get_warp_matrix(
    img_capture,
    match_index=0,
    warp_mode=cv2.MOTION_HOMOGRAPHY,
    pyramid_levels=1,
    max_alignment_iterations=50,
):
    """
    This function uses the MicaSense imageutils.align_capture()
    function to determine an alignment (warp) matrix of a single
    capture that can be applied to all images.

    From MicaSense: "For best alignment results it's recommended
    to select a capture which has features which visible in all bands.
    Man-made objects such as cars, roads, and buildings tend to work
    very well, while captures of only repeating crop rows tend to
    work poorly. Remember, once a good transformation has been found
    for flight, it can be generally be applied across all of the images."


    Parameters
    ----------
    img_capture:
        A capture is a set of images taken by one MicaSense camera
        which share the same unique capture identifier (capture_id).
        These images share the same filename prefix, such as
        IMG_0000_*.tif. It is defined by running
        ImageSet.from_directory().captures.

    match_index: Index of the band. Default is 0.

    warp_mode: MOTION_HOMOGRAPHY or MOTION_AFFINE.
        For Altum images only use MOTION_HOMOGRAPHY

    pyramid_levels:
        Default is 1. For images with RigRelatives,
        setting this to 0 or 1 may improve alignment

    max_alignment_iterations:
        The maximum number of solver iterations.

    Returns
    -------
        A numpy.ndarray of the warp matrix from a single image capture.

    Reference
    ---------
    https://github.com/micasense/imageprocessing/blob/master/Alignment.ipynb
    """
    logger.info(
        "Aligning images. Depending on settings this can take from a few seconds to many minutes",
    )
    # Can potentially increase max_iterations for better results, but longer runtimes
    warp_matrices, alignment_pairs = imageutils.align_capture(
        img_capture,
        ref_index=match_index,
        max_iterations=max_alignment_iterations,
        warp_mode=warp_mode,
        pyramid_levels=pyramid_levels,
    )

    return warp_matrices


def save(
    capture,
    warp_matrices,
    generateThumbnails=True,
):
    """Save a single capture."""
    try:
        capture.dls_irradiance = None
        capture.compute_undistorted_radiance()
        capture.create_aligned_capture(
            irradiance_list=None,
            img_type="radiance",
            warp_matrices=warp_matrices,
        )
        capture.save_capture_as_stack(
            capture.fullOutputPath,
            sort_by_wavelength=True,
        )
        if generateThumbnails:
            capture.save_capture_as_rgb(capture.fullThumbnailPath)
        capture.clear_image_data()
    except Exception as e:
        # Log the error with capture information
        logger.warning(f"Failed to save {capture.fullOutputPath}: {e}")
        raise  # Re-raise with full traceback


def save_images(
    img_set,
    output_path,
    thumbnail_path,
    warp_img_capture,
    generateThumbnails=True,
):
    """Process captures in parallel using threading."""
    # Create output directories
    os.makedirs(output_path, exist_ok=True)
    if generateThumbnails:
        os.makedirs(thumbnail_path, exist_ok=True)

    warp_matrices = get_warp_matrix(warp_img_capture)

    start = datetime.datetime.now()

    logger.info("output_path: %s", output_path)

    for idx, capture in enumerate(img_set.captures):
        outputFilename = f"capture_{idx + 1}.tif"
        thumbnailFilename = f"capture_{idx + 1}.jpg"
        fullOutputPath = os.path.join(output_path, outputFilename)
        fullThumbnailPath = os.path.join(thumbnail_path, thumbnailFilename)

        capture.fullOutputPath = fullOutputPath
        capture.fullThumbnailPath = fullThumbnailPath

        save(capture, warp_matrices)

    end = datetime.datetime.now()
    elapsed = (end - start).total_seconds()

    logger.info(
        "Saving time: %.2f",
        elapsed,
    )


def process_micasense_images(
    sky=False,
    generateThumbnails=True,
):
    """
    Process MicaSense multispectral images to calibrated radiance units.

    This function is a wrapper for save_images() that reads raw MicaSense image
    captures from a directory, applies radiometric calibration and band alignment,
    and produces georeferenced TIFF files with radiance units (W/sr/nm). It handles
    both water surface imagery and sky reference imagery, automatically organizing
    outputs into appropriate directories and generating metadata files.

    Parameters
    ----------
    sky : bool, optional
        Processing mode flag:
        - True: Process sky reference images from raw_sky_dir, save to sky_lt_dir
        - False: Process water surface images from raw_water_dir, save to lt_dir
        Default is False.
    generateThumbnails : bool, optional
        If True, generates RGB thumbnail JPEG images for quick visualization of
        each processed capture. Thumbnails are saved to separate thumbnail
        directories. Default is True.

    Returns
    -------
    str
        Output directory path where processed radiance TIFF files were saved.
        Either settings.sky_lt_dir or settings.lt_dir depending on sky parameter.
    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    if sky:
        img_dir = settings.raw_sky_dir
        # just have the sky images go into a different dir and
        # the water imgs go into a default 'lt_imgs' dir
        output_path = settings.sky_lt_dir
        thumbnail_path = settings.main_dir / "sky_lt_thumbnails"
    else:
        img_dir = settings.raw_water_dir
        output_path = settings.lt_dir
        thumbnail_path = settings.main_dir / "lt_thumbnails"

    img_set = imageset.ImageSet.from_directory(img_dir)
    thumbnail_path.mkdir(exist_ok=True)

    if sky:
        warp_img_capture = img_set.captures[0]
    else:
        warp_img_capture = imageset.ImageSet.from_directory(
            settings.warp_img_dir,
        ).captures[0]
        logger.info("Used warp dir: %s", settings.warp_img_dir)

    save_images(
        img_set=img_set,
        output_path=output_path,
        thumbnail_path=thumbnail_path,
        warp_img_capture=warp_img_capture,
        generateThumbnails=generateThumbnails,
    )

    logger.info("Finished saving images at: %s", output_path)
    return output_path


def read_file(file: Path) -> Image:
    """Reads tiff file from a filepath."""
    with rasterio.open(file, "r") as src:
        data = np.array(src.read(), dtype=np.float32)
        profile = src.profile
        file_name = file.name
        idx = int(file_name.split("_")[-1].split(".")[0])
        lt_img = Image(file_name, file, "lt", profile, data, idx)
    return lt_img


def write_data(data, output_path, profile) -> None:
    """Windowed data write to a filepath using rasterio."""
    with rasterio.open(
        output_path,
        "w",
        **profile,
    ) as dst:
        height, width = data.shape[-2:]
        chunk_size = 256

        for row in range(0, height, chunk_size):
            for col in range(0, width, chunk_size):
                row_end = min(row + chunk_size, height)
                col_end = min(col + chunk_size, width)

                window = Window(col, row, col_end - col, row_end - row)

                if data.ndim == 3:
                    window_data = data[:, row:row_end, col:col_end]
                else:
                    window_data = data[row:row_end, col:col_end]

                dst.write(window_data, window=window)


def save_img(img: Image, output_folder: Path):
    """Saves image."""
    # Getting the main dir filepath from the image
    # instead of settings.main_dir because
    # settings is not getting shared in between
    # processes. TODO: Have to fix this.
    profile = img.profile
    profile["count"] = 5
    output_path = output_folder.joinpath(img.file_name)
    write_data(img.data, output_path, profile)
