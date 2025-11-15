from osgeo import gdal
import numpy as np
import pandas as pd
import rasterio
import os
import cv2
import datetime
import dronewq
import glob
from tqdm import tqdm
import concurrent.futures
from rasterio.transform import Affine
from rasterio.enums import Resampling
from dronewq.utils.settings import settings
import micasense

# FIXME: Should rename this file


def load_imgs(
    img_dir,
    count=10000,
    start=0,
    altitude_cutoff=0,
    random=False,
):
    """
    This function loads all images in a directory as a multidimensional numpy array.

    Parameters:
        img_dir: A string containing the directory filepath of images to be retrieved

    Returns:
        An iterator over numpy arrays of all image captures in a directory

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
    This function returns a pandas dataframe of captures and associated metadata with the options of how many to list and what number of image to start on.

    Parameters:
        img_dir: A string containing the directory filepath of images to be retrieved

        count: The amount of images to load. Default is 10000

        start: The image to start loading from. Default is 0 (first image the .csv).

        random: A boolean to load random images. Default is False

    Returns:
        Pandas dataframe of image metadata

    """
    if "sky" in img_dir:
        base = img_dir
    else:
        base = os.path.dirname(img_dir)

    csv_path = os.path.join(base, "metadata.csv")

    df = pd.read_csv(csv_path)
    df = df.set_index("filename")
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
    This function uses the MicaSense imageutils.align_capture() function to determine an alignment (warp) matrix of a single capture that can be applied to all images. From MicaSense: "For best alignment results it's recommended to select a capture which has features which visible in all bands. Man-made objects such as cars, roads, and buildings tend to work very well, while captures of only repeating crop rows tend to work poorly. Remember, once a good transformation has been found for flight, it can be generally be applied across all of the images." Ref: https://github.com/micasense/imageprocessing/blob/master/Alignment.ipynb

    Parameters:
        img_capture: A capture is a set of images taken by one MicaSense camera which share the same unique capture identifier (capture_id). These images share the same filename prefix, such as IMG_0000_*.tif. It is defined by running ImageSet.from_directory().captures.

        match_index: Index of the band. Default is 0.

        warp_mode: MOTION_HOMOGRAPHY or MOTION_AFFINE. For Altum images only use MOTION_HOMOGRAPHY

        pyramid_levels: Default is 1. For images with RigRelatives, setting this to 0 or 1 may improve alignment

        max_alignment_iterations: The maximum number of solver iterations.

    Returns:
        A numpy.ndarray of the warp matrix from a single image capture.
    """

    print(
        "Aligning images. Depending on settings this can take from a few seconds to many minutes"
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
    """Save a single capture with proper error handling."""
    gdal.UseExceptions()
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
        print(f"Failed to save {capture.fullOutputPath}: {e}")
        raise  # Re-raise with full traceback


def save_images(
    img_set,
    output_path,
    thumbnail_path,
    warp_img_capture,
    generateThumbnails=True,
    overwrite_lt_lw=False,
    max_workers=4,  # None uses default based on CPU count
):
    """Process captures in parallel using threading."""

    # Create output directories
    os.makedirs(output_path, exist_ok=True)
    if generateThumbnails:
        os.makedirs(thumbnail_path, exist_ok=True)

    warp_matrices = get_warp_matrix(warp_img_capture)

    # Use processes instead of threads for CPU-bound work
    # For I/O-bound (file writing), threads are acceptable
    max_workers = max_workers or os.cpu_count()

    start = datetime.datetime.now()

    print("output_path: ", output_path)

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
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
            future = executor.submit(save, capture, warp_matrices, generateThumbnails)
            futures[future] = idx

        # Wait for all tasks to complete and collect results
        results = []
        completed = 0

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()  # Blocks until this specific future completes
                results.append(result)
                completed += 1
            except Exception as e:
                idx = futures[future]
                print(f"Capture {idx} failed: {e}")
                results.append(False)

    end = datetime.datetime.now()
    elapsed = (end - start).total_seconds()

    print(f"Saving time: {end - start}")
    print(
        f"Alignment+Saving rate: {len(img_set.captures)/elapsed:.2f} images per second"
    )
    print(f"Successfully processed: {sum(results)}/{len(results)} captures")

    return results


def process_micasense_images(
    warp_img_dir=None,
    overwrite_lt_lw=False,
    sky=False,
    generateThumbnails=True,
):
    """
    This function is wrapper function for the save_images() function to read in an image directory and produce new .tifs with units of radiance (W/sr/nm).

    Parameters:
        warp_img_dir: a string containing the filepath of the capture to use to create the warp matrix

        overwrite_lt_lw: Option to overwrite lt and lw files that have been written previously. Default is False

        sky: Option to run raw sky captures to collected Lsky. If True, the save_images() is run on raw .tif files and saves new .tifs in sky_lt directories. If False, save_images() is run on raw .tif files and saves new .tifs in lt directories.

    Returns:
        New .tif files for each capture in image directory with units of radiance (W/sr/nm) and optional new RGB thumbnail .jpg files for each capture.

    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    img_dir = settings.raw_sky_dir if sky else settings.raw_water_dir

    img_set = micasense.imageset.ImageSet.from_directory(img_dir)

    if warp_img_dir:
        warp_img_capture = micasense.imageset.ImageSet.from_directory(
            warp_img_dir
        ).captures[0]
        print("used warp dir", warp_img_dir)
    else:
        warp_img_capture = img_set.captures[0]

    # just have the sky images go into a different dir and the water imgs go into a default 'lt_imgs' dir
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
    )

    print("Finished saving images.")
    fullCsvPath = dronewq.write_metadata_csv(img_dir, output_path)
    print("Finished saving image metadata.")

    return output_path


# TODO: Fix method default
def downsample(input_dir, output_dir, scale_x, scale_y, method=Resampling.average):
    """
    This function performs a downsampling to reduce the spatial resolution of the final mosaic.

    Parameters:
        input_dir: A string containing input directory filepath

        output_dir: A string containing output directory filepath

        scale_x: proportion by which the width of each file will be resized

        scale_y: proportion by which the height of each file will be resized

        method: the resampling method to perform. Defaults to Resampling.nearest. Please see https://rasterio.readthedocs.io/en/stable/api/rasterio.enums.html#rasterio.enums.Resampling for other resampling methods.

    Returns:
        None, downsampled raster is written to output_dir.
    """

    os.makedirs(output_dir, exist_ok=True)
    raster_paths = glob.glob(os.path.join(input_dir, "*"))

    for raster_path in tqdm(raster_paths):
        raster_name = os.path.basename(raster_path)
        out_name = os.path.join(
            output_dir,
            f'{raster_name.split(".")[0]}_x_{scale_x}_y_{scale_y}_method_{method.name}.tif',
        )

        with rasterio.open(raster_path, "r") as dataset:
            data = dataset.read(
                out_shape=(
                    dataset.count,
                    dataset.height // scale_x,
                    dataset.width // scale_y,
                ),
                resampling=method,
            )

            dst_transform: Affine = dataset.transform * dataset.transform.scale(
                (dataset.width / data.shape[-1]), (dataset.height / data.shape[-2])
            )

            dst_kwargs = dataset.meta.copy()
            dst_kwargs.update(
                {
                    "crs": dataset.crs,
                    "transform": dst_transform,
                    "width": data.shape[-1],
                    "height": data.shape[-2],
                }
            )

            with rasterio.open(out_name, "w", **dst_kwargs) as dst:
                dst.write(data)
