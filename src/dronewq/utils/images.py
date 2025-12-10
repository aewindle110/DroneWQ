import concurrent.futures
import datetime
import logging
import os

import cv2
import numpy as np
import pandas as pd
import rasterio

import dronewq
import micasense
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


def load_imgs(
    img_dir,
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
    img_dir : str
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
    df = load_metadata(
        img_dir,
        count,
        start,
        altitude_cutoff,
        random,
    )

    img_list = [os.path.join(img_dir, fn) for fn in df.index.values]

    for im in img_list:
        with rasterio.open(im, "r") as src:
            yield np.array(src.read())


def load_metadata(
    img_dir,
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
    img_dir : str
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
    if "sky" in img_dir:
        base = img_dir
    else:
        base = os.path.dirname(img_dir)

    csv_path = os.path.join(base, "metadata.csv")

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
    warp_matrices, alignment_pairs = micasense.imageutils.align_capture(
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
        return True
    except Exception as e:
        # Log the error with capture information
        logger.warn(f"Failed to save {capture.fullOutputPath}: {e}")
        raise  # Re-raise with full traceback


def save_images(
    img_set,
    output_path,
    thumbnail_path,
    warp_img_capture,
    generateThumbnails=True,
    overwrite_lt_lw=False,
    num_workers=4,
):
    """Process captures in parallel using threading."""
    # Create output directories
    os.makedirs(output_path, exist_ok=True)
    if generateThumbnails:
        os.makedirs(thumbnail_path, exist_ok=True)

    warp_matrices = get_warp_matrix(warp_img_capture)

    start = datetime.datetime.now()

    logger.info("output_path: %s", output_path)

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers,
    ) as executor:
        futures = {}

        for idx, capture in enumerate(img_set.captures):
            outputFilename = f"capture_{idx + 1}.tif"
            thumbnailFilename = f"capture_{idx + 1}.jpg"
            fullOutputPath = os.path.join(output_path, outputFilename)
            fullThumbnailPath = os.path.join(thumbnail_path, thumbnailFilename)

            # Skip if exists and not overwriting
            if os.path.exists(fullOutputPath) and not overwrite_lt_lw:
                continue

            if len(capture.images) != len(img_set.captures[0].images):
                continue

            capture.fullOutputPath = fullOutputPath
            capture.fullThumbnailPath = fullThumbnailPath

            # Submit task and track it
            future = executor.submit(
                save,
                capture,
                warp_matrices,
                generateThumbnails,
            )
            futures[future] = idx

        # Wait for all tasks to complete and collect results
        results = []
        completed = 0

        for future in concurrent.futures.as_completed(futures):
            try:
                # Blocks until this specific future completes
                result = future.result()
                results.append(result)
                completed += 1
            except Exception as e:
                idx = futures[future]
                logger.error(
                    "Capture %d failed: %s",
                    idx,
                    str(e),
                )
                results.append(False)

    end = datetime.datetime.now()
    elapsed = (end - start).total_seconds()

    logger.info(
        "Saving time: %.2f",
        elapsed,
    )
    logger.info(
        "Alignment+Saving rate: %.2f images per second",
        len(results) / elapsed if elapsed > 0 else 0,
    )
    logger.info(
        "Successfully processed: %d/%d captures",
        sum(results),
        len(results),
    )

    return results


def process_micasense_images(
    warp_img_dir=None,
    overwrite_lt_lw=False,
    sky=False,
    generateThumbnails=True,
    num_workers=4,
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
    warp_img_dir : str, optional
        Directory path containing a representative capture to use for computing
        the band alignment (warp) matrix. If None, uses the first capture from
        the input directory. Should contain a scene with distinct features visible
        in all bands. Default is None.
    overwrite_lt_lw : bool, optional
        If True, overwrites previously processed Lt (total radiance) and Lw
        (water-leaving radiance) files. If False, skips processing for existing
        files. Default is False.
    sky : bool, optional
        Processing mode flag:
        - True: Process sky reference images from raw_sky_dir, save to sky_lt_dir
        - False: Process water surface images from raw_water_dir, save to lt_dir
        Default is False.
    generateThumbnails : bool, optional
        If True, generates RGB thumbnail JPEG images for quick visualization of
        each processed capture. Thumbnails are saved to separate thumbnail
        directories. Default is True.
    num_workers : int, optional
        Number of parallel worker processes for image processing. Higher values
        speed up processing but require more memory and CPU cores. Should be
        tuned based on available hardware. Default is 4.

    Returns
    -------
    str
        Output directory path where processed radiance TIFF files were saved.
        Either settings.sky_lt_dir or settings.lt_dir depending on sky parameter.

    Raises
    ------
    LookupError
        If settings.main_dir is not configured.

    Notes
    -----
    The function performs the following workflow:
    1. Loads raw MicaSense images from the appropriate directory
    2. Computes or loads band alignment (warp) matrices
    3. Applies radiometric calibration to convert DN to radiance (W/sr/nm)
    4. Aligns all bands to a reference band using warp matrices
    5. Saves calibrated, aligned images as GeoTIFF files
    6. Optionally generates RGB thumbnails for visualization
    7. Writes metadata CSV file containing capture information

    Directory structure:
    - Water images: raw_water_dir → lt_dir + lt_thumbnails/
    - Sky images: raw_sky_dir → sky_lt_dir + sky_lt_thumbnails/

    The warp matrix computed from warp_img_dir (or first capture) is applied to
    all captures in the flight, as the relative positions of camera sensors
    remain fixed. For best results, choose a warp_img_dir capture containing:
    - Man-made features (buildings, roads, vehicles)
    - High contrast in all spectral bands
    - Avoid repetitive patterns (crop rows)

    Processing outputs:
    - Calibrated radiance GeoTIFF files (W/sr/nm) with 5 bands
    - Optional RGB thumbnail JPEGs for quick review
    - metadata.csv containing capture times, GPS coordinates, altitude, etc.

    Memory usage scales with image resolution and num_workers. For large datasets
    (>1000 captures), consider processing in batches or reducing num_workers if
    memory is limited.

    Examples
    --------
    >>> # Process water surface images with default settings
    >>> output_dir = process_micasense_images()
    >>> print(f"Water images saved to: {output_dir}")

    >>> # Process sky reference images
    >>> sky_output = process_micasense_images(sky=True, generateThumbnails=False)

    >>> # Use specific capture for alignment with parallel processing
    >>> output_dir = process_micasense_images(
    ...     warp_img_dir='/path/to/representative/capture',
    ...     num_workers=8,
    ...     overwrite_lt_lw=True
    ... )

    >>> # Fast processing without thumbnails, using first capture for alignment
    >>> output_dir = process_micasense_images(
    ...     generateThumbnails=False,
    ...     num_workers=12
    ... )

    >>> # Reprocess with different alignment, overwriting previous results
    >>> output_dir = process_micasense_images(
    ...     warp_img_dir='/path/to/better/capture',
    ...     overwrite_lt_lw=True,
    ...     num_workers=6
    ... )

    See Also
    --------
    save_images : Underlying function that performs the actual processing
    get_warp_matrix : Computes band alignment matrices
    write_metadata_csv : Generates metadata CSV file
    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    img_dir = settings.raw_sky_dir if sky else settings.raw_water_dir

    img_set = micasense.imageset.ImageSet.from_directory(img_dir)

    if warp_img_dir:
        warp_img_capture = micasense.imageset.ImageSet.from_directory(
            warp_img_dir,
        ).captures[0]
        logger.info("Used warp dir: %s", warp_img_dir)
    else:
        warp_img_capture = img_set.captures[0]

    # just have the sky images go into a different dir and
    # the water imgs go into a default 'lt_imgs' dir
    if sky:
        output_path = settings.sky_lt_dir
        thumbnail_path = os.path.join(settings.main_dir, "sky_lt_thumbnails")
    else:
        output_path = settings.lt_dir
        thumbnail_path = os.path.join(settings.main_dir, "lt_thumbnails")

    save_images(
        img_set=img_set,
        output_path=output_path,
        thumbnail_path=thumbnail_path,
        warp_img_capture=warp_img_capture,
        generateThumbnails=generateThumbnails,
        overwrite_lt_lw=overwrite_lt_lw,
        num_workers=num_workers,
    )

    logger.info("Finished saving images at: %s", output_path)
    fullCsvPath = dronewq.write_metadata_csv(img_dir, output_path)
    logger.info("Finished saving image metadata at: %s", fullCsvPath)

    return output_path
