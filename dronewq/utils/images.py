import numpy as np
import pandas as pd
import rasterio
import os
import cv2
import datetime
import dronewq
from dronewq.utils.settings import settings
from dronewq.legacy import micasense

# FIXME: Should rename this file


def load_images(img_list):
    """
    This function loads all images in a directory as a multidimensional numpy array.

    Parameters:
        img_list: A list of .tif files, usually called by using glob.glob(filepath)

    Returns:
        A multidimensional numpy array of all image captures in a directory

    """
    all_imgs = []
    for im in img_list:
        with rasterio.open(im, "r") as src:
            all_imgs.append(src.read())
    return np.array(all_imgs)


def load_img_fn_and_meta(csv_path, count=10000, start=0, random=False):
    """
    This function returns a pandas dataframe of captures and associated metadata with the options of how many to list and what number of image to start on.

    Parameters:
        csv_path: A string containing the filepath

        count: The amount of images to load. Default is 10000

        start: The image to start loading from. Default is 0 (first image the .csv).

        random: A boolean to load random images. Default is False

    Returns:
        Pandas dataframe of image metadata

    """
    df = pd.read_csv(csv_path)
    df = df.set_index("filename")
    # df['UTC-Time'] = pd.to_datetime(df['UTC-Time'])
    # cut off if necessary
    df = (
        df.iloc[start : start + count]
        if not random
        else df.loc[np.random.choice(df.index, count)]
    )

    return df


def retrieve_imgs_and_metadata(
    img_dir, count=10000, start=0, altitude_cutoff=0, sky=False, random=False
):
    """
    This function is the main interface we expect the user to use when grabbing a subset of imagery from any stage in processing. This returns the images as a numpy array and metadata as a pandas dataframe.

    Parameters:
        img_dir: A string containing the directory filepath of images to be retrieved

        count: The amount of images you want to list. Default is 10000

        start: The number of image to start on. Default is 0 (first image in img_dir).

        random: A boolean to load random images. Default is False

    Returns:
        A multidimensional numpy array of all image captures in a directory and a Pandas dataframe of image metadata.

    """
    if sky:
        csv_path = os.path.join(img_dir, "metadata.csv")
    else:
        csv_path = os.path.join(os.path.dirname(img_dir), "metadata.csv")

    df = load_img_fn_and_meta(csv_path, count=count, start=start, random=random)

    # apply altitiude threshold and set IDs as the indez
    df = df[df["Altitude"] > altitude_cutoff]

    # this grabs the filenames from the subset of the dataframe we've selected, then preprends the image_dir that we want.
    # the filename is the index
    all_imgs = load_images([os.path.join(img_dir, fn) for fn in df.index.values])

    return (all_imgs, df)


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


def save_images(
    img_set,
    img_output_path,
    thumbnailPath,
    warp_img_capture,
    generateThumbnails=True,
    overwrite_lt_lw=False,
):
    """
    This function processes each capture in an imageset to apply a warp matrix and save new .tifs with units of radiance (W/sr/nm) and optional RGB .jpgs.

    Parameters:
        img_set: An ImageSet is a container for a group of Captures that are processed together. It is defined by running the ImageSet.from_directory() function found in Micasense's imageset.py

        img_output_path: A string containing the filepath to store a new folder of radiance .tifs

        thumbnailPath: A string containing the filepath to store a new folder of RGB thumnail .jpgs

        warp_img_capture: A Capture chosen to align all images. Can be created by using Micasense's ImageSet-from_directory().captures function

        generateThumbnails: Option to create RGB .jpgs of all the images. Default is True

        overwrite_lt_lw: Option to overwrite lt and lw files that have been written previously. Default is False

    Returns:
        New .tif files for each capture in img_set with units of radiance (W/sr/nm) and optional new RGB thumbnail .jpg files for each capture.
    """

    warp_matrices = get_warp_matrix(warp_img_capture)

    if not os.path.exists(img_output_path):
        os.makedirs(img_output_path)
    if generateThumbnails and not os.path.exists(thumbnailPath):
        os.makedirs(thumbnailPath)

    start = datetime.datetime.now()
    for i, capture in enumerate(img_set.captures):
        outputFilename = "capture_" + str(i + 1) + ".tif"
        thumbnailFilename = "capture_" + str(i + 1) + ".jpg"
        fullOutputPath = os.path.join(img_output_path, outputFilename)
        fullThumbnailPath = os.path.join(thumbnailPath, thumbnailFilename)
        if (not os.path.exists(fullOutputPath)) or overwrite_lt_lw:
            if len(capture.images) == len(img_set.captures[0].images):

                capture.dls_irradiance = None
                capture.compute_undistorted_radiance()
                capture.create_aligned_capture(
                    irradiance_list=None,
                    img_type="radiance",
                    warp_matrices=warp_matrices,
                )
                capture.save_capture_as_stack(fullOutputPath, sort_by_wavelength=True)
                if generateThumbnails:
                    capture.save_capture_as_rgb(fullThumbnailPath)
        capture.clear_image_data()
    end = datetime.datetime.now()

    print("Saving time: {}".format(end - start))
    print(
        "Alignment+Saving rate: {:.2f} images per second".format(
            float(len(img_set.captures)) / float((end - start).total_seconds())
        )
    )
    return True


def process_micasense_images(
    project_dir, warp_img_dir=None, overwrite_lt_lw=False, sky=False
):
    """
    This function is wrapper function for the save_images() function to read in an image directory and produce new .tifs with units of radiance (W/sr/nm).

    Parameters:
        project_dir: a string containing the filepath of the raw .tifs

        warp_img_dir: a string containing the filepath of the capture to use to create the warp matrix

        overwrite_lt_lw: Option to overwrite lt and lw files that have been written previously. Default is False

        sky: Option to run raw sky captures to collected Lsky. If True, the save_images() is run on raw .tif files and saves new .tifs in sky_lt directories. If False, save_images() is run on raw .tif files and saves new .tifs in lt directories.

    Returns:
        New .tif files for each capture in image directory with units of radiance (W/sr/nm) and optional new RGB thumbnail .jpg files for each capture.

    """
    if settings.main_dir is None:
        raise LookupError("Please set the main_dir path.")

    if sky:
        img_dir = settings.raw_sky_img_dir
    else:
        img_dir = settings.raw_sky_img_dir

    imgset = micasense.imageset.ImageSet.from_directory(img_dir)

    if warp_img_dir:
        warp_img_capture = micasense.imageset.ImageSet.from_directory(
            warp_img_dir
        ).captures[0]
        print("used warp dir", warp_img_dir)
    else:
        warp_img_capture = imgset.captures[0]

    # just have the sky images go into a different dir and the water imgs go into a default 'lt_imgs' dir
    if sky:
        output_path = settings.sky_lt_dir
        thumbnailPath = os.path.join(project_dir, "sky_lt_thumbnails")
    else:
        output_path = settings.lt_dir
        thumbnailPath = os.path.join(project_dir, "lt_thumbnails")

    if save_images(
        imgset,
        output_path,
        thumbnailPath,
        warp_img_capture,
        overwrite_lt_lw=overwrite_lt_lw,
    ):
        print("Finished saving images.")
        fullCsvPath = dronewq.write_metadata_csv(imgset, output_path)
        print("Finished saving image metadata.")

    return output_path
