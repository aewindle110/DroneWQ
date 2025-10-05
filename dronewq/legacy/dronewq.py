import multiprocessing, glob, shutil, os, datetime, subprocess, math

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import cv2
import exiftool
import rasterio
import scipy.ndimage as ndimage
from skimage.transform import resize
from pathlib import Path

from ipywidgets import FloatProgress, Layout
from IPython.display import display

from micasense import imageset as imageset
from micasense import capture as capture
import micasense.imageutils as imageutils
import micasense.plotutils as plotutils
from micasense import panel
from micasense import image as image

import random
import cameratransform as ct
from rasterio.merge import merge

from tqdm import tqdm
from pyproj import CRS
from rasterio.transform import Affine
from rasterio.enums import Resampling

import contextily as cx
import rioxarray

from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from pyproj import Transformer
from typing import Tuple
from matplotlib.image import AxesImage
from xyzservices import Bunch

# this isn't really good practice but there are a few deprecated tools in the Micasense stack so we'll ignore some of these warnings
import warnings

warnings.filterwarnings("ignore")


def function_that_warns():
    warnings.warn("deprecated", DeprecationWarning)


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    function_that_warns()


def write_metadata_csv(img_set, csv_output_path):
    """
    This function grabs the EXIF metadata from img_set and writes it to outputPath/metadata.csv. Other metadata could be added based on what is needed in your workflow.

    Parameters:
        img_set: An ImageSet is a container for a group of Captures that are processed together. It is defined by running the ImageSet.from_directory() function found in Micasense's imageset.py
        csv_output_path: A string containing the filepath to store metadata.csv containing image EXIF metadata

    Returns:
        A .csv of metadata for each image capture.

    """

    def decdeg2dms(dd):
        minutes, seconds = divmod(abs(dd) * 3600, 60)
        degrees, minutes = divmod(minutes, 60)
        degrees: float = degrees if dd >= 0 else -degrees

        return (degrees, minutes, seconds)

    lines = []
    for i, capture in enumerate(img_set.captures):

        fullOutputPath = os.path.join(csv_output_path, f"capture_{i+1}.tif")

        width, height = capture.images[0].meta.image_size()
        img: Image_micasense = capture.images[0]
        lat, lon, alt = capture.location()

        latdeg, londeg = decdeg2dms(lat)[0], decdeg2dms(lon)[0]
        latdeg, latdir = (-latdeg, "S") if latdeg < 0 else (latdeg, "N")
        londeg, londir = (-londeg, "W") if londeg < 0 else (londeg, "E")

        datestamp, timestamp = (
            capture.utc_time().strftime("%Y-%m-%d,%H:%M:%S").split(",")
        )
        resolution = capture.images[0].focal_plane_resolution_px_per_mm
        focal_length = capture.images[0].focal_length
        sensor_size = (
            width / img.focal_plane_resolution_px_per_mm[0],
            height / img.focal_plane_resolution_px_per_mm[1],
        )

        data = {
            "filename": f"capture_{i+1}.tif",
            "dirname": fullOutputPath,
            "DateStamp": datestamp,
            "TimeStamp": timestamp,
            "Latitude": lat,
            "LatitudeRef": latdir,
            "Longitude": lon,
            "LongitudeRef": londir,
            "Altitude": alt,
            "SensorX": sensor_size[0],
            "SensorY": sensor_size[1],
            "FocalLength": focal_length,
            "Yaw": (capture.images[0].dls_yaw * 180 / math.pi) % 360,
            "Pitch": (capture.images[0].dls_pitch * 180 / math.pi) % 360,
            "Roll": (capture.images[0].dls_roll * 180 / math.pi) % 360,
            "SolarElevation": capture.images[0].solar_elevation,
            "ImageWidth": width,
            "ImageHeight": height,
            "XResolution": resolution[1],
            "YResolution": resolution[0],
            "ResolutionUnits": "mm",
        }

        lines.append(list(data.values()))
        header = list(data.keys())

    fullCsvPath = os.path.join(csv_output_path, "metadata.csv")

    df = pd.DataFrame(columns=header, data=lines)

    df = df.set_index("filename")
    # df['UTC-Time'] = pd.to_datetime(df['DateStamp'] +' '+ df['TimeStamp'],format="%Y:%m:%d %H:%M:%S")

    df.to_csv(fullCsvPath)

    return fullCsvPath


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
    warp_matrices, alignment_pairs = imageutils.align_capture(
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

    if sky:
        img_dir = project_dir + "/raw_sky_imgs"
    else:
        img_dir = project_dir + "/raw_water_imgs"

    imgset = imageset.ImageSet.from_directory(img_dir)

    if warp_img_dir:
        warp_img_capture = imageset.ImageSet.from_directory(warp_img_dir).captures[0]
        print("used warp dir", warp_img_dir)
    else:
        warp_img_capture = imgset.captures[0]

    # just have the sky images go into a different dir and the water imgs go into a default 'lt_imgs' dir
    if sky:
        outputPath = os.path.join(project_dir, "sky_lt_imgs")
        output_csv_path = outputPath
        thumbnailPath = os.path.join(project_dir, "sky_lt_thumbnails")
    else:
        outputPath = os.path.join(project_dir, "lt_imgs")
        output_csv_path = project_dir
        thumbnailPath = os.path.join(project_dir, "lt_thumbnails")

    if (
        save_images(
            imgset,
            outputPath,
            thumbnailPath,
            warp_img_capture,
            overwrite_lt_lw=overwrite_lt_lw,
        )
        == True
    ):
        print("Finished saving images.")
        fullCsvPath = write_metadata_csv(imgset, output_csv_path)
        print("Finished saving image metadata.")

    return outputPath


######## workflow functions ########


def mobley_rho_method(sky_lt_dir, lt_dir, lw_dir, rho=0.028):
    """
    This function calculates water leaving radiance (Lw) by multiplying a single (or small set of) sky radiance (Lsky) images by a single rho value. The default is rho = 0.028, which is based off recommendations described in Mobley, 1999. This approach should only be used if sky conditions are not changing substantially during the flight and winds are less than 5 m/s.

    Parameters:
        sky_lt_dir: A string containing the directory filepath of sky_lt images

        lt_dir: A string containing the directory filepath of lt images

        lw_dir: A string containing the directory filepath of new lw images

        rho = The effective sea-surface reflectance of a wave facet. The default 0.028

    Returns:
        New Lw .tifs with units of W/sr/nm
    """

    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(
        sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True
    )
    lsky_median = np.median(
        sky_imgs, axis=(0, 2, 3)
    )  # here we want the median of each band
    del sky_imgs  # free up the memory

    # go through each Lt image in the dir and subtract out rho*lsky to account for sky reflection
    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, "r") as Lt_src:
            profile = Lt_src.profile
            profile["count"] = 5
            lw_all = []
            for i in range(1, 6):
                # todo this is probably faster if we read them all and divide by the vector
                lt = Lt_src.read(i)
                lw = lt - (rho * lsky_median[i - 1])
                lw_all.append(lw)  # append each band
            stacked_lw = np.stack(lw_all)  # stack into np.array

            # write new stacked lw tifs
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(lw_dir, im_name), "w", **profile) as dst:
                dst.write(stacked_lw)

    return True


def blackpixel_method(sky_lt_dir, lt_dir, lw_dir):
    """
    This function calculates water leaving radiance (Lw) by applying the black pixel assumption which assumes Lw in the NIR is negligable due to strong absorption of water. Therefore, total radiance (Lt) in the NIR is considered to be solely surface reflected light (Lsr) , which allows rho to be calculated if sky radiance (Lsky) is known. This method should only be used for waters where there is little to none NIR signal (i.e. Case 1 waters). The assumption tends to fail in more turbid waters where high concentrations of particles enhance backscattering and Lw in the NIR (i.e. Case 2 waters).

    Parameters:
        sky_lt_dir: A string containing the directory filepath of sky_lt images

        lt_dir: A string containing the directory filepath of lt images

        lw_dir: A string containing the directory filepath of new lw images

    Returns:
        New Lw .tifs with units of W/sr/nm

    """
    # grab the first ten of these images, average them, then delete this from memory
    sky_imgs, sky_img_metadata = retrieve_imgs_and_metadata(
        sky_lt_dir, count=10, start=0, altitude_cutoff=0, sky=True
    )
    lsky_median = np.median(
        sky_imgs, axis=(0, 2, 3)
    )  # here we want the median of each band
    del sky_imgs

    for im in glob.glob(lt_dir + "/*.tif"):
        with rasterio.open(im, "r") as Lt_src:
            profile = Lt_src.profile
            profile["count"] = 5

            Lt = Lt_src.read(4)
            rho = Lt / lsky_median[4 - 1]
            lw_all = []
            for i in range(1, 6):
                # todo this is probably faster if we read them all and divide by the vector
                lt = Lt_src.read(i)
                lw = lt - (rho * lsky_median[i - 1])
                lw_all.append(lw)  # append each band
            stacked_lw = np.stack(lw_all)  # stack into np.array

            # write new stacked lw tifs
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(lw_dir, im_name), "w", **profile) as dst:
                dst.write(stacked_lw)

    return True


def hedley_method(lt_dir, lw_dir, random_n=10):
    """
    This function calculates water leaving radiance (Lw) by modelling a constant 'ambient' NIR brightness level which is removed from all pixels across all bands. An ambient NIR level is calculated by averaging the minimum 10% of Lt(NIR) across a random subset images. This value represents the NIR brightness of a pixel with no sun glint. A linear relationship between Lt(NIR) amd the visible bands (Lt) is established, and for each pixel, the slope of this line is multiplied by the difference between the pixel NIR value and the ambient NIR level.

    Parameters:
        lt_dir: A string containing the directory filepath of lt images

        lw_dir: A string containing the directory filepath of new lw images

        random_n: The amount of random images to calculate ambient NIR level. Default is 10.

    Returns:
         New Lw .tifs with units of W/sr/nm

    """
    lt_all = []

    rand = random.sample(
        glob.glob(lt_dir + "/*.tif"), random_n
    )  # open random n files. n is selected by user in process_raw_to_rrs
    for im in rand:
        with rasterio.open(im, "r") as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_all.append(lt)

    stacked_lt = np.stack(lt_all)
    stacked_lt_reshape = stacked_lt.reshape(
        *stacked_lt.shape[:-2], -1
    )  # flatten last two dims

    # apply linear regression between NIR and visible bands
    min_lt_NIR = []
    for i in range(len(rand)):
        min_lt_NIR.append(
            np.percentile(stacked_lt_reshape[i, 4, :], 0.1)
        )  # calculate minimum 10% of Lt(NIR)
    mean_min_lt_NIR = np.mean(min_lt_NIR)  # take mean of minimum 10% of random Lt(NIR)

    all_slopes = []
    for i in range(len(glob.glob(lt_dir + "/*.tif"))):
        im = glob.glob(lt_dir + "/*.tif")[i]
        im_name = os.path.basename(
            im
        )  # we're grabbing just the .tif file name instead of the whole path
        with rasterio.open(im, "r") as lt_src:
            profile = lt_src.profile
            lt = lt_src.read()
            lt_reshape = lt.reshape(*lt.shape[:-2], -1)  # flatten last two dims

        lw_all = []
        for j in range(0, 5):
            slopes = np.polyfit(lt_reshape[4, :], lt_reshape[j, :], 1)[
                0
            ]  # calculate slope between NIR and all bands of random files
            all_slopes.append(slopes)

            # calculate Lw (Lt - b(Lt(NIR)-min(Lt(NIR))))
            lw = lt[j, :, :] - all_slopes[j] * (lt[4, :, :] - mean_min_lt_NIR)
            lw_all.append(lw)

        stacked_lw = np.stack(lw_all)  # stack into np.array
        profile["count"] = 5

        # write new stacked Rrs tif w/ reflectance units
        with rasterio.open(os.path.join(lw_dir, im_name), "w", **profile) as dst:
            dst.write(stacked_lw)
    return True


def panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path):
    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is calculated from the calibrated reflectance panel. This method does not perform well when light is variable such as partly cloudy days. It is recommended to use in the case of a clear, sunny day.

    Parameters:
        panel_dir: A string containing the directory filepath of the panel image captures

        lw_dir: A string containing the directory filepath of lw images

        rrs_dir: A string containing the directory filepath of new rrs images

        output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) calculated from the panel

    Returns:
        New Rrs .tifs with units of sr^-1

        New .csv file with average Ed measurements (mW/m2/nm) calculated from image cpatures of the calibrated reflectance panel

    """
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

    ed_data = pd.DataFrame.from_records(ed_data, index="image", columns=ed_columns)
    ed_data.to_csv(output_csv_path + "/panel_ed.csv")

    # now divide the lw_imagery by Ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    for im in glob.glob(lw_dir + "/*.tif"):
        with rasterio.open(im, "r") as Lw_src:
            profile = Lw_src.profile
            profile["count"] = 5
            rrs_all = []
            # could vectorize this for speed
            for i in range(1, 6):
                lw = Lw_src.read(i)

                rrs = lw / ed[i - 1]
                rrs_all.append(rrs)  # append each band
            stacked_rrs = np.stack(rrs_all)  # stack into np.array

            # write new stacked Rrs tifs w/ Rrs units
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), "w", **profile) as dst:
                dst.write(stacked_rrs)
    return True


def dls_ed(
    raw_water_dir, lw_dir, rrs_dir, output_csv_path, panel_dir=None, dls_corr=False
):
    """
    This function calculates remote sensing reflectance (Rrs) by dividing downwelling irradiance (Ed) from the water leaving radiance (Lw) .tifs. Ed is derived from the downwelling light sensor (DLS), which is collected at every image capture. This method does not perform well when light is variable such as partly cloudy days. It is recommended to use in overcast, completely cloudy conditions. A DLS correction can be optionally applied to tie together DLS and panel Ed measurements. In this case, a compensation factor derived from the calibration reflectance panel is applied to DLS Ed measurements.The defualt is False.


    Parameters:
        raw_water_dir: A string containing the directory filepath of the raw water images

        lw_dir: A string containing the directory filepath of lw images

        rrs_dir: A string containing the directory filepath of new rrs images

        output_csv_path: A string containing the filepath to save Ed measurements (mW/m2/nm) derived from the DLS

        panel_dir: A string containing the filepath of panel images. Only need if dls_corr=True.

        dls_corr: Option to apply compensation factor from calibration reflectance panel to DLS Ed measurements. Default is False.

    Returns:
        New Rrs .tifs with units of sr^-1

        New .csv file with average Ed measurements (mW/m2/nm) calculated from DLS measurements
    """
    capture_imgset = imageset.ImageSet.from_directory(raw_water_dir).captures
    ed_data = []
    ed_columns = ["image", "ed_475", "ed_560", "ed_668", "ed_717", "ed_842"]

    if not dls_corr:
        for i, capture in enumerate(capture_imgset):
            ed = capture.dls_irradiance()
            ed[3], ed[4] = ed[4], ed[3]  # flip last two bands (red edge and NIR)
            ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(ed[0] * 1000)]
                + [np.mean(ed[1] * 1000)]
                + [np.mean(ed[2] * 1000)]
                + [np.mean(ed[3] * 1000)]
                + [np.mean(ed[4] * 1000)]
            )  # multiply by 1000 to scale to mW
            ed_data.append(ed_row)

        ed_data_df = pd.DataFrame.from_records(
            ed_data, index="image", columns=ed_columns
        )
        ed_data_df.to_csv(output_csv_path + "/dls_ed.csv")

    if dls_corr:
        panel_imgset = imageset.ImageSet.from_directory(panel_dir).captures
        panels = np.array(panel_imgset)

        panel_ed_data = []
        dls_ed_data = []
        for i, capture in enumerate(panels):
            # calculate panel Ed from every panel capture
            panel_ed = np.array(
                panels[i].panel_irradiance()
            )  # this function automatically finds the panel albedo and uses that to calcuate Ed, otherwise raises an error
            panel_ed[3], panel_ed[4] = panel_ed[4], panel_ed[3]  # flip last two bands
            panel_ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(panel_ed[0])]
                + [np.mean(panel_ed[1])]
                + [np.mean(panel_ed[2])]
                + [np.mean(panel_ed[3])]
                + [np.mean(panel_ed[4])]
            )  # multiply by 1000 to scale to mW (but want ed to still be in W to divide by Lw which is in W)
            panel_ed_data.append(panel_ed_row)

            # calculate DLS Ed from every panel capture
            dls_ed = capture.dls_irradiance()
            dls_ed[3], dls_ed[4] = (
                dls_ed[4],
                dls_ed[3],
            )  # flip last two bands (red edge and NIR)
            dls_ed_row = (
                ["capture_" + str(i + 1)]
                + [np.mean(dls_ed[0] * 1000)]
                + [np.mean(dls_ed[1] * 1000)]
                + [np.mean(dls_ed[2] * 1000)]
                + [np.mean(dls_ed[3] * 1000)]
                + [np.mean(dls_ed[4] * 1000)]
            )  # multiply by 1000 to scale to mW
            dls_ed_data.append(dls_ed_row)

        dls_ed_corr = np.array(panel_ed) / (np.array(dls_ed[0:5]) * 1000)

        # this is the DLS ed corrected by the panel correction factor
        dls_ed_corr_data = []
        for i, capture in enumerate(capture_imgset):
            ed = capture.dls_irradiance()
            ed = (ed[0:5] * dls_ed_corr) * 1000
            ed = np.append(ed, [0])  # add zero because other ed ends with a 0
            dls_ed_corr_row = (
                ["capture_" + str(i + 1)]
                + [ed[0]]
                + [ed[1]]
                + [ed[2]]
                + [ed[3]]
                + [ed[4]]
            )
            dls_ed_corr_data.append(dls_ed_corr_row)

        dls_ed_corr_data_df = pd.DataFrame.from_records(
            dls_ed_corr_data, index="image", columns=ed_columns
        )
        dls_ed_corr_data_df.to_csv(output_csv_path + "/dls_corr_ed.csv")

    # now divide the lw_imagery by ed to get rrs
    # go through each Lt image in the dir and divide it by the lsky
    for idx, im in enumerate(glob.glob(lw_dir + "/*.tif")):
        with rasterio.open(im, "r") as Lw_src:
            profile = Lw_src.profile
            profile["count"] = 5
            rrs_all = []
            # could vectorize this for speed
            for i in range(1, 6):
                lw = Lw_src.read(i)
                if dls_corr:
                    rrs = lw / dls_ed_corr_data[idx][i]
                else:
                    rrs = lw / ed_data[idx][i]
                rrs_all.append(rrs)  # append each band
            stacked_rrs = np.stack(rrs_all)  # stack into np.array

            # write new stacked Rrs tifs w/ Rrs units
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(os.path.join(rrs_dir, im_name), "w", **profile) as dst:
                dst.write(stacked_rrs)
    return True


# glint removal
def rrs_threshold_pixel_masking(
    rrs_dir, masked_rrs_dir, nir_threshold=0.01, green_threshold=0.005
):
    """
    This function masks pixels based on user supplied Rrs thresholds in an effort to remove instances of specular sun glint, shadowing, or adjacent land when present in the images.

    Parameters:
        rrs_dir: A string containing the directory filepath to write the new masked .tifs

        masked_rrs_dir: A string containing the name of the directory to store masked Rrs images.

        nir_threshold: An Rrs(NIR) value where pixels above this will be masked. Default is 0.01. These are usually pixels of specular sun glint or land features.

        green_threshold: A Rrs(green) value where pixels below this will be masked. Default is 0.005. These are usually pixels of vegetation shadowing.

    Returns:
        New masked Rrs.tifs with units of sr^-1

    """

    # go through each rrs image in the dir and mask pixels > nir_threshold and < green_threshold
    for im in glob.glob(rrs_dir + "/*.tif"):
        with rasterio.open(im, "r") as rrs_src:
            profile = rrs_src.profile
            profile["count"] = 5
            rrs_mask_all = []
            nir = rrs_src.read(5)
            green = rrs_src.read(2)
            nir[nir > nir_threshold] = np.nan
            green[green < green_threshold] = np.nan

            nir_nan_index = np.isnan(nir)
            green_nan_index = np.isnan(green)

            # filter nan pixel indicies across all bands
            for i in range(1, 6):

                rrs_mask = rrs_src.read(i)
                rrs_mask[nir_nan_index] = np.nan
                rrs_mask[green_nan_index] = np.nan

                rrs_mask_all.append(rrs_mask)

            stacked_rrs_mask = np.stack(rrs_mask_all)  # stack into np.array

            # write new stacked rrs tifs
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(
                os.path.join(masked_rrs_dir, im_name), "w", **profile
            ) as dst:
                dst.write(stacked_rrs_mask)

    return True


def rrs_std_pixel_masking(rrs_dir, masked_rrs_dir, num_images=10, mask_std_factor=1):
    """
    This function masks pixels based on a user supplied value in an effort to remove instances of specular sun glint. The mean and standard deviation of NIR values from the first N images is calculated and any pixels containing an NIR value > mean + std*mask_std_factor is masked across all bands. The lower the mask_std_factor, the more pixels will be masked.

    Parameters:
        rrs_dir: A string containing the directory filepath of images to be processed

        masked_rrs_dir: A string containing the directory filepath to write the new masked .tifs

        num_images: Number of images in the dataset to calculate the mean and std of NIR. Default is 10.

        mask_std_factor: A factor to multiply to the standard deviation of NIR values. Default is 1.

    Returns:
        New masked .tifs

    """
    # grab the first num_images images, finds the mean and std of NIR, then anything times the glint factor is classified as glint
    rrs_imgs, _ = retrieve_imgs_and_metadata(
        rrs_dir, count=num_images, start=0, altitude_cutoff=0, random=True
    )
    rrs_nir_mean = np.nanmean(rrs_imgs, axis=(0, 2, 3))[4]  # mean of NIR band
    rrs_nir_std = np.nanstd(rrs_imgs, axis=(0, 2, 3))[4]  # std of NIR band
    print("The mean and std of Rrs from first N images is: ", rrs_nir_mean, rrs_nir_std)
    print(
        "Pixels will be masked where Rrs(NIR) > ",
        rrs_nir_mean + rrs_nir_std * mask_std_factor,
    )
    del rrs_imgs  # free up the memory

    # go through each Rrs image in the dir and mask any pixels > mean+std*glint factor
    for im in glob.glob(rrs_dir + "/*.tif"):
        with rasterio.open(im, "r") as rrs_src:
            profile = rrs_src.profile
            profile["count"] = 5
            rrs_deglint_all = []
            rrs_nir_deglint = rrs_src.read(5)  # nir band
            rrs_nir_deglint[
                rrs_nir_deglint > (rrs_nir_mean + rrs_nir_std * mask_std_factor)
            ] = np.nan
            nan_index = np.isnan(rrs_nir_deglint)
            # filter nan pixel indicies across all bands
            for i in range(1, 6):
                rrs_deglint = rrs_src.read(i)
                rrs_deglint[nan_index] = np.nan
                rrs_deglint_all.append(rrs_deglint)  # append all for each band
            stacked_rrs_deglint = np.stack(rrs_deglint_all)  # stack into np.array
            # write new stacked tifs
            im_name = os.path.basename(
                im
            )  # we're grabbing just the .tif file name instead of the whole path
            with rasterio.open(
                os.path.join(masked_rrs_dir, im_name), "w", **profile
            ) as dst:
                dst.write(stacked_rrs_deglint)
    return True


def process_raw_to_rrs(
    main_dir,
    rrs_dir_name,
    output_csv_path,
    lw_method="mobley_rho_method",
    mask_pixels=False,
    random_n=10,
    pixel_masking_method="value_threshold",
    mask_std_factor=1,
    nir_threshold=0.01,
    green_threshold=0.005,
    ed_method="dls_ed",
    overwrite_lt_lw=False,
    clean_intermediates=True,
):
    """
    This functions is the main processing script that processs raw imagery to units of remote sensing reflectance (Rrs). Users can select which processing parameters to use to calculate Rrs.

    Parameters:
        main_dir: A string containing the main image directory

        rrs_dir_name: A string containing the directory filepath of new rrs images

        output_csv_path: A string containing the filepath to write the metadata.csv

        lw_method: Method used to calculate water leaving radiance. Default is mobley_rho_method().

        random_n: The amount of random images to calculate ambient NIR level. Default is 10. Only need if lw_method = 'hedley_method'

        mask_pixels: Option to mask pixels containing specular sun glint, shadowing, adjacent vegetation, etc. Default is False.

        pixel_masking_method: Method to mask pixels. Options are 'value_threshold' or 'std_threshold'. Default is value_threshold.

        mask_std_factor: A factor to multiply to the standard deviation of NIR values. Default is 1. Only need if pixel_masking_method = 'std_threshold'

        nir_threshold: An Rrs(NIR) value where pixels above this will be masked. Default is 0.01. These are usually pixels of specular sun glint or land features. Only need if pixel_masking_method = 'value_threshold'.

        green_threshold: A Rrs(green) value where pixels below this will be masked. Default is 0.005. These are usually pixels of vegetation shadowing.  Only need if pixel_masking_method = 'value_threshold'.

        ed_method: Method used to calculate downwelling irradiance (Ed). Default is dls_ed().

        overwrite_lt_lw: Option to overwrite lt and lw files that have been written previously. Default is False but this is only applied to the Lt images.

        clean_intermediates: Option to erase intermediates of processing (Lt, Lw, unmasked Rrs)

    Returns:
        New Rrs tifs (masked or unmasked) with units of sr^-1.
    """

    ############################
    #### setup the workspace ###
    ############################

    # specify the locations of the different levels of imagery
    # I do this partially so I can just change these pointers to the data and not have to copy it or have complex logic repeated

    ### os join here
    raw_water_img_dir = os.path.join(main_dir, "raw_water_imgs")
    raw_sky_img_dir = os.path.join(main_dir, "raw_sky_imgs")

    lt_dir = os.path.join(main_dir, "lt_imgs")
    sky_lt_dir = os.path.join(main_dir, "sky_lt_imgs")
    lw_dir = os.path.join(main_dir, "lw_imgs")
    panel_dir = os.path.join(main_dir, "panel")
    rrs_dir = os.path.join(main_dir, rrs_dir_name)
    masked_rrs_dir = os.path.join(main_dir, "masked_" + rrs_dir_name)
    warp_img_dir = os.path.join(main_dir, "align_img")

    # make all these directories if they don't already exist
    all_dirs = [lt_dir, lw_dir, rrs_dir]
    for directory in all_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)

    if mask_pixels == True:
        Path(masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    # this makes an assumption that there is only one panel image put in this directory
    panel_names = glob.glob(os.path.join(panel_dir, "IMG_*.tif"))

    files = os.listdir(raw_water_img_dir)  # your directory path
    num_bands = imageset.ImageSet.from_directory(warp_img_dir).captures[0].num_bands
    print(
        f"Processing a total of {len(files)} images or {round(len(files)/num_bands)} captures."
    )

    ### convert raw imagery to radiance (Lt)
    print("Converting raw images to radiance (raw -> Lt).")
    process_micasense_images(
        main_dir, warp_img_dir=warp_img_dir, overwrite_lt_lw=overwrite_lt_lw, sky=False
    )

    # deciding if we need to process raw sky images to radiance
    if lw_method in ["mobley_rho_method", "blackpixel_method"]:
        print("Converting raw sky images to radiance (raw sky -> Lsky).")
        # we're also making an assumption that we don't need to align/warp these images properly because they'll be medianed
        process_micasense_images(
            main_dir, warp_img_dir=None, overwrite_lt_lw=overwrite_lt_lw, sky=True
        )

    ##################################
    ### correct for surface reflected light ###
    ##################################

    if lw_method == "mobley_rho_method":
        print("Applying the mobley_rho_method (Lt -> Lw).")
        mobley_rho_method(sky_lt_dir, lt_dir, lw_dir)

    elif lw_method == "blackpixel_method":
        print("Applying the blackpixel_method (Lt -> Lw)")
        blackpixel_method(sky_lt_dir, lt_dir, lw_dir)

    elif lw_method == "hedley_method":
        print("Applying the Hochberg/Hedley (Lt -> Lw)")
        hedley_method(lt_dir, lw_dir, random_n)

    else:  # just change this pointer if we didn't do anything the lt over to the lw dir
        print("Not doing any Lw calculation.")
        lw_dir = lt_dir

    #####################################
    ### normalize Lw by Ed to get Rrs ###
    #####################################

    if ed_method == "panel_ed":
        print("Normalizing by panel irradiance (Lw/Ed -> Rrs).")
        panel_ed(panel_dir, lw_dir, rrs_dir, output_csv_path)

    elif ed_method == "dls_ed":
        print("Normalizing by DLS irradiance (Lw/Ed -> Rrs).")
        dls_ed(raw_water_img_dir, lw_dir, rrs_dir, output_csv_path)

    elif ed_method == "dls_and_panel_ed":
        print("Normalizing by DLS corrected by panel irradiance (Lw/Ed -> Rrs).")
        dls_ed(
            raw_water_img_dir,
            lw_dir,
            rrs_dir,
            output_csv_path,
            panel_dir=panel_dir,
            dls_corr=True,
        )

    else:
        print(
            "No other irradiance normalization methods implemented yet, panel_ed is recommended."
        )
        return False

    print(
        "All data has been saved as Rrs using the "
        + str(lw_method)
        + " to calculate Lw and normalized by "
        + str(ed_method)
        + " irradiance."
    )

    ########################################
    ### mask pixels in the imagery (from glint, vegetation, shadows) ###
    ########################################
    if mask_pixels == True and pixel_masking_method == "value_threshold":
        print("Masking pixels using NIR and green Rrs thresholds")
        rrs_threshold_pixel_masking(
            rrs_dir,
            masked_rrs_dir,
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
        )
    elif mask_pixels == True and pixel_masking_method == "std_threshold":
        print("Masking pixels using std Rrs(NIR)")
        rrs_std_pixel_masking(rrs_dir, masked_rrs_dir, mask_std_factor=mask_std_factor)

    else:  # if we don't do the glint correction then just change the pointer to the lt_dir
        print("Not masking pixels.")

    ################################################
    ### finalize and add point output ###
    ################################################

    if clean_intermediates:
        dirs_to_delete = [lt_dir, sky_lt_dir, lw_dir]
        for d in dirs_to_delete:
            shutil.rmtree(d, ignore_errors=True)

    return True


############ water quality retrieval algorithms ############


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


def save_wq_imgs(
    main_dir, rrs_img_dir, wq_dir_name, wq_alg="chl_gitelson", start=0, count=10000
):
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


###### Georeferencing #######


def compute_lines(lines, indexes, start=0, end=0):
    """A function that given a list of indexes where there are gaps,
    returns a list of pairs(start, end) for each interval

    Parameters:
        lines (List[Tuple[int, int]]): list where to write the result

        indexes (List[int]): list of indexes

        start (int, optional): first index. Defaults to 0.

        end (int, optional): last index. Defaults to 0.

    Returns:
        List[int]: list of pairs(start, end) for each interval
    """

    for index in indexes:
        if abs(end - index) > 1:
            if start != end:
                lines.append((int(start), int(end)))
            start = index
        end = index
    else:
        if start != end:
            lines.append((int(start), int(end)))

    return list(set(lines))


def compute_flight_lines(captures_yaw, altitude, pitch, roll, threshold=10):
    """
    A function that returns a list of yaw, altitude, pitch, roll values from different flight transects to be used in the georeference() function. The function calculates the median of all yaw angles. For yaw angles < median, it calculates the median of filtered captures. If yaw angle is between filtered median - threshold and filtered median + threshold, it is considered a valid capture. Simiarly, for yaw angles > median, if yaw angle is between filtered median - threshold and filtered median + threshold, it is considered a valid capture.

    Parameters:
        captures_yaw: Can either be a fixed number or pulled from the metadata

        altitude: Can either be a fixed number or pulled from the metadata

        pitch: Can either be a fixed number or pulled from the metadata

        roll: Can either be a fixed number or pulled from the metadata

        threshold: A value to be used to determine what captures have yaw angles that are considered valid. Default is 10.

    Returns:
        List[int]: list of pairs(start, end) for each trasenct
    """

    median_yaw = np.median(captures_yaw)
    indexes = np.where(captures_yaw < median_yaw)[0]
    indexes = np.where(
        (np.median(captures_yaw[indexes]) - threshold <= captures_yaw)
        & (captures_yaw <= np.median(captures_yaw[indexes]) + threshold)
    )[0]

    lines = compute_lines([], indexes)

    median_yaw = np.median(captures_yaw)
    indexes = np.where(captures_yaw > median_yaw)[0]

    indexes = np.where(
        (np.median(captures_yaw[indexes]) - threshold <= captures_yaw)
        & (captures_yaw <= np.median(captures_yaw[indexes]) + threshold)
    )[0]

    lines = compute_lines(lines, indexes)
    lines.sort()

    flight_lines = [
        {
            "start": line[0],
            "end": line[1] + 1,
            "yaw": float(np.median(captures_yaw[line[0] : line[1]])),
            "pitch": pitch,
            "roll": roll,
            "alt": altitude,
        }
        for line in lines
    ]

    return flight_lines


def georeference(
    metadata,
    input_dir,
    output_dir,
    lines=None,
    altitude=None,
    yaw=None,
    pitch=0,
    roll=0,
    axis_to_flip=1,
):
    """
    This function georeferences all the captures indicated in the line parameter following the specification of the other parameters such as altitude, yaw, pitch, roll, axis_to_flip

    Parameters:
        metadata: A Pandas dataframe of the metadata

        input_dir: A string containing the directory filepath of the images to be retrieved for georeferencing.

        output_dir: A string containing the directory filepath to be saved.

        lines: Selection of images to be processed. Defaults to None. Example: [slice(0,10)]

        altitude: sets the altitude where all captures were taken. Defaults to None which uses the altitude data saved in the metadata for each respective capture.

        yaw: sets the sensor's direction angle during all captures. Defaults to None which uses the yaw angle saved in the metadata for each respective capture.

        pitch: sets the sensor's pitch angle during all captures. Defaults to 0 which means the sensor was horizontal to the ground.

        roll: sets the sensor's roll angle during all captures. Defaults to 0 which means the sensor was horizontal to the ground.

        axis_to_flip: The axis to apply a flip. Defaults to 1.

    Returns:
        Georeferenced .tifs in output_dir
    """

    def __get_transform(f, sensor_size, image_size, lat, lon, alt, yaw, pitch, roll):
        """
        Calculates a transformation matrix for a given capture in order to get every lat, lon for each pixel in the image.

        Parameters:
            f (float): focal_length

            sensor_size (Tuple[float, float]): correspondence pixel -> milimeter

            image_size (Tuple[int, int]): number of pixels for width and height

            lat (float): latitude of camera

            lon (float): longitude of camera

            alt (float): altitude of camera

            yaw (float): yaw of camera

            pitch (float): tilt of camera

            roll (float): roll of camera

        Returns:
            Affine: transformation matrix
        """
        cam = ct.Camera(
            ct.RectilinearProjection(
                focallength_mm=f, sensor=sensor_size, image=image_size
            ),
            ct.SpatialOrientation(
                elevation_m=alt,
                tilt_deg=pitch,
                roll_deg=roll,
                heading_deg=yaw,
                pos_x_m=0,
                pos_y_m=0,
            ),
        )

        cam.setGPSpos(lat, lon, alt)

        coords: np.ndarray = np.array(
            [
                cam.gpsFromImage([0, 0]),
                cam.gpsFromImage([image_size[0] - 1, 0]),
                cam.gpsFromImage([image_size[0] - 1, image_size[1] - 1]),
                cam.gpsFromImage([0, image_size[1] - 1]),
            ]
        )

        gcp1 = rasterio.control.GroundControlPoint(
            row=0, col=0, x=coords[0, 1], y=coords[0, 0], z=coords[0, 2]
        )
        gcp2 = rasterio.control.GroundControlPoint(
            row=image_size[0] - 1, col=0, x=coords[1, 1], y=coords[1, 0], z=coords[1, 2]
        )
        gcp3 = rasterio.control.GroundControlPoint(
            row=image_size[0] - 1,
            col=image_size[1] - 1,
            x=coords[2, 1],
            y=coords[2, 0],
            z=coords[2, 2],
        )
        gcp4 = rasterio.control.GroundControlPoint(
            row=0, col=image_size[1] - 1, x=coords[3, 1], y=coords[3, 0], z=coords[3, 2]
        )

        return rasterio.transform.from_gcps([gcp1, gcp2, gcp3, gcp4])

    def __get_georefence_by_uuid(
        metadata, lines=None, altitude=None, yaw=None, pitch=None, roll=None
    ):
        """
        Given a DataFrame and a list of flight lines, calculate a dictionary with the transformation matrix for each capture

        Parameters:
            metadata (DataFrame): Pandas DataFrame that contains information like capture latitude, longitude, ...

            lines (List[slice], optional): List that indicates the flight lines. Defaults to None which means [ slice(0, None) ] = all captures.

            altitude (float, optional): altitude of camera

            yaw (float, optional): yaw of camera

            pitch (float, optional): tilt of camera

            roll (float, optional): roll of camera

        Returns:
            Mapping[str, Affine]: Dictionary that gathers captures IDs and transformation matrices
        """

        lines = (
            lines
            if lines is not None
            else [
                {
                    "start": 0,
                    "end": None,
                    "yaw": yaw,
                    "pitch": pitch,
                    "roll": roll,
                    "alt": altitude,
                },
            ]
        )

        georeference_by_uuid = {}

        for line in lines:
            captures = metadata.iloc[line["start"] : line["end"]]
            for _, capture in captures.iterrows():
                focal = capture["FocalLength"]
                image_size = (capture["ImageWidth"], capture["ImageHeight"])[::-1]
                sensor_size = (capture["SensorX"], capture["SensorY"])[::-1]

                lon = float(capture["Longitude"])
                lat = float(capture["Latitude"])
                alt = line["alt"] or float(capture["Altitude"])
                capture_pitch = (
                    line["pitch"]
                    if line["pitch"] is not None
                    else float(capture["Pitch"])
                )
                capture_roll = (
                    line["roll"] if line["roll"] is not None else float(capture["Roll"])
                )
                capture_yaw = (
                    line["yaw"] if line["yaw"] is not None else float(capture["Yaw"])
                )

                georeference_by_uuid[os.path.basename(capture["filename"])] = (
                    __get_transform(
                        focal,
                        sensor_size,
                        image_size,
                        lat,
                        lon,
                        alt,
                        capture_yaw,
                        capture_pitch,
                        capture_roll,
                    )
                )

        return georeference_by_uuid

    def __convert_to_tif(name):
        return ".".join([name.split(".")[0], "tif"])

    out_folder_path = output_dir
    os.makedirs(out_folder_path, exist_ok=True)

    metadata = metadata.set_index(metadata["filename"])
    georefence_by_uuid = __get_georefence_by_uuid(
        metadata, lines, altitude, yaw, pitch, roll
    )

    for uuid, transform in tqdm(
        georefence_by_uuid.items(), total=len(georefence_by_uuid.items())
    ):

        with rasterio.open(os.path.join(input_dir, uuid), "r") as src:
            data = src.read()

            profile = {
                "dtype": src.profile["dtype"],
                "count": src.profile["count"],
                "height": src.profile["height"],
                "width": src.profile["width"],
                "driver": "GTiff",
                "nodata": 0 if src.profile["dtype"] == rasterio.uint8 else np.nan,
                "crs": CRS.from_user_input(4326),
                "transform": transform,
            }

            with rasterio.open(
                os.path.join(output_dir, __convert_to_tif(uuid)), "w", **profile
            ) as dst:
                dst.write(
                    data if axis_to_flip is None else np.flip(data, axis=axis_to_flip)
                )


##### Mosaicking #####

# Geometry functions


def is_on_right_side(x, y, xy0, xy1):
    """
    Given a point and 2 points defining a rect, check if the point is on the right side or not.

    Parameters:
        x (float): value in the x-axis of the point

        y (float): value in the y-axis of the point

        xy0 (Tuple[float, float]): point 0 of the rect

        xy1 (Tuple[float, float]): point 1 of the rect

    Returns:
        bool: is on right side or not
    """

    x0, y0 = xy0
    x1, y1 = xy1
    a = float(y1 - y0)
    b = float(x0 - x1)
    c = -a * x0 - b * y0
    return a * x + b * y + c > 0


def is_point_within_vertices(x, y, vertices):
    """This fuction checks if a point is within the given vertices

    Parameters:
        x (float): value in the width axis for the point

        y (float): value in the height axis for the point

        vertices (List[Tuple[float, float]]): bounding vertices

    Returns:
        bool: whether the point is within the vertices or not
    """

    num_vert = len(vertices)
    is_right = [
        is_on_right_side(x, y, vertices[i], vertices[(i + 1) % num_vert])
        for i in range(num_vert)
    ]
    all_left = not any(is_right)
    all_right = all(is_right)
    return all_left or all_right


def are_points_within_vertices(vertices, points):
    """
    Given a list of vertices and a list of points, generate every rect determined by the vertices and check if the points are within the polygon or not.

    Parameters:
        vertices (List[Tuple[float, float]]): List of vertices defining a polygon

        points (List[Tuple[float, float]]): List of points to study is they are within the polygon or not

    Returns:
        bool: the given points are within the given vertices or not
    """

    all_points_in_merge = True

    for point in points:
        all_points_in_merge &= is_point_within_vertices(
            x=point[0], y=point[1], vertices=vertices
        )

    return all_points_in_merge


def euclidean_distance(p1, p2):
    """
    euclidean distance between two points

    Parameters:
        p1 (Tuple[float, float]): 2D point 1

        p2 (Tuple[float, float]): 2D point 2

    Returns:
        float: euclidean distance between two points
    """

    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_center(points):
    """This function receives a list of points and returns the point at the center of all points

    Parameters:
        points (np.ndarray): a list of points

    Returns:
        np.ndarray: center of all points
    """

    x = points[:, 0]
    y = points[:, 1]

    m_x = sum(x) / points.shape[0]
    m_y = sum(y) / points.shape[0]

    return np.array([m_x, m_y])


class Paralelogram2D:
    """This class represents a paralelogram"""

    def __init__(self, points):
        """This constructor receives a list of points and sets the pairs of lines

        Parameters:
            points (List[Tuple[float, float]]): list of corner points that determinate a paralelogram
        """

        self.points = points
        self.lines = [[0, 1], [1, 2], [2, 3], [3, 0]]
        self.pairs = [[0, 2], [1, 3]]

    def get_line_center(self, index):
        """This functions returns the center of a specific line of the paralelogram

        Parameters:
            index (int): line index

        Returns:
            np.ndarray: center
        """

        return sum(self.points[self.lines[index]]) / 2

    def get_offset_to_lines(self, index, point):
        """This functions returns a Vector that represents what should be direction of point for being in the specified line

        Parameters:
            index (int): line index

            point (np.ndarray): point

        Returns:
            np.ndarray: direction vector
        """

        return self.get_line_center(index) - point

    def get_center(self):
        """This function returns the center of the paralelogram

        Returns:
            np.ndarray: center
        """

        return get_center(self.points)

    def move_line_from_offset(self, index, offset):
        """This function moves a specific line given an offset vector

        Parameters:
            index (int): line index

            offset (np.ndarray): offset vector
        """

        self.points[self.lines[index]] += offset

    def are_on_right_side_of_line(self, index, points):
        """This function checks if a list of points is on the right side of a specific line

        Parameters:
            index (int): line index

            points (np.ndarray): a list of points

        Returns:
            bool: whether the list is on the right side or not
        """

        return all(
            [
                is_on_right_side(*point, *self.points[self.lines[index]])
                for point in points
            ]
        )


def mosaic(
    input_dir, output_dir, output_name, method="mean", dtype=np.float32, band_names=None
):
    """This function moasics all the given rasters into a single raster file

    Parameters:
        input_dir: a string containing the directory filepath of images to be mosaicked

        output_dir: a string containing the directory filepath to save the output

        output_name: a string of the output name of mosaicked .tif

        method: Method to be used when multiple captures coincide at same location. Options: 'mean', 'first', 'min', 'max'. Defaults to 'mean'.

        dtype: dtype of the mosaicked raster. Defaults to np.float32.

        band_names: List of band names. If it is not None, it writes one file for each band instead of one file with all the bands. Defaults to None.

    Returns:
        Mosaicked .tif file
    """

    def listdir_fullpath(d):
        return [os.path.join(d, f) for f in os.listdir(d)]

    raster_paths = listdir_fullpath(input_dir)

    out_folder_path = output_dir
    os.makedirs(out_folder_path, exist_ok=True)

    output_name = os.path.join(out_folder_path, f"{output_name}.tif")

    def __latlon_to_index(dst, src):
        """
        Given a source dataset and a destination dataset. Get the latitudes and longitudes that correspond to move the source data to the destination data.

        Parameters:
            dst (_type_): Destination dataset

            src (DatasetReader): Source dataset

        Returns:
            ndarray: List of latitudes and longitudes
        """

        cols, rows = np.meshgrid(np.arange(src.width), np.arange(src.height))

        xs, ys = rasterio.transform.xy(src.transform, rows, cols)
        lons, lats = np.array(xs), np.array(ys)

        coords_to_index = np.array(
            [dst.index(lons[i], lats[i]) for i in np.arange(src.height)]
        )
        lons, lats = coords_to_index[:, 0, :], coords_to_index[:, 1, :]

        return lons, lats

    def __get_raster_corners(raster_path):
        """
        Given a raster path, return a list of its corners based on its transformation matrix.

        Parameters:
            raster_path (str): path of the raster to be processed

        Returns:
            List[Tuple[float, float]]: List with the 4 corners of the raster
        """

        raster = rasterio.open(raster_path)
        w, h = raster.width, raster.height

        return [
            raster.transform * p
            for p in [(0, 0), (0, h - 1), (w - 1, h - 1), (w - 1, 0)]
        ]

    def __get_raster_corners_by_params(transform, width, height):
        """
        Given a transformation matrix, a width and a height, return a list of corners based on the given transformation matrix.

        Parameters:
            transform (Affine): transformation matrix

            width (int): transformation width

            height (int): transformation height

        Returns:
            List[Tuple[float, float]]: List with the 4 corners of the raster
        """

        return [
            transform * p
            for p in [(0, 0), (0, height - 1), (width - 1, height - 1), (width - 1, 0)]
        ]

    def __get_merge_transform(raster_paths, max_iterations=10000):
        """This function returns a transform matrix that contains of the specified rasters

        Parameters:
            raster_paths (set): raster paths to merge

            max_iterations (int, optional): additional merge parameters. Default is 2000

        Returns:
            Tuple[int, int, Affine]: width, height and transformation matrix of the merge
        """

        with rasterio.open(raster_paths[0]) as src:
            original_transform = src.transform
            transform = src.transform
            width = src.width
            height = src.height
            res = src.res

        for raster_path in raster_paths:
            with rasterio.open(raster_path) as src:
                if res[0] < src.res[0]:
                    original_transform = src.transform
                    transform = src.transform
                    res = src.res

        raster_corners = np.array(
            [
                __get_raster_corners(raster_path=raster_path)
                for raster_path in raster_paths
            ]
        ).reshape(-1, 2)

        mid_point = get_center(raster_corners)
        mid_point_first_capture = get_center(raster_corners[0:4])
        c, f = mid_point[0] + (
            raster_corners[0][0] - mid_point_first_capture[0]
        ), mid_point[1] + (raster_corners[0][1] - mid_point_first_capture[1])

        transform = Affine(
            a=original_transform.a,
            b=original_transform.b,
            c=c,
            d=original_transform.d,
            e=original_transform.e,
            f=f,
        )

        paralelo = Paralelogram2D(
            np.array(__get_raster_corners_by_params(transform, width, height))
        )

        for line_index in range(len(paralelo.lines)):
            offset = paralelo.get_offset_to_lines(line_index, paralelo.get_center())

            iteration = 0
            while (
                not paralelo.are_on_right_side_of_line(line_index, raster_corners)
                and iteration < max_iterations
            ):
                paralelo.move_line_from_offset(line_index, offset)
                iteration += 1

        width = int(
            round(euclidean_distance(paralelo.points[0], paralelo.points[-1]) / res[0])
        )
        height = int(
            round(euclidean_distance(paralelo.points[0], paralelo.points[1]) / res[1])
        )

        transform = Affine(
            a=original_transform.a,
            b=original_transform.b,
            c=paralelo.points[0][0],
            d=original_transform.d,
            e=original_transform.e,
            f=paralelo.points[0][1],
        )

        return width, height, transform

    def __mean(
        dst, raster_paths, n_bands, width, height, dtype=np.float32, band_index=None
    ):
        """
        Merge method that calculates the mean value in those positions where more than one raster write its values.

        Parameters:
            dst (_type_): destination raster

            raster_paths (List[str]): raster paths to merge

            n_bands (int): bands of each raster

            width (int): width of the merge raster

            height (int): height of the merge raster

            dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

            band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

        Returns:
            ndarray: resulting merge
        """

        final_data = np.zeros(shape=(n_bands, height, width), dtype=dtype)
        count = np.zeros(shape=(n_bands, height, width), dtype=np.uint8)

        for raster_path in tqdm(raster_paths):
            with rasterio.open(raster_path, "r") as src:
                data = (
                    src.read()
                    if band_index is None
                    else np.array([src.read(band_index)])
                )

                lons, lats = __latlon_to_index(dst, src)

                final_data[:, lons, lats] = np.nansum(
                    [data, final_data[:, lons, lats]], axis=0
                )
                count[:, lons, lats] = np.nansum(
                    [~np.isnan(data), count[:, lons, lats]], axis=0
                )

        return np.divide(final_data, count)

    def __first(
        dst, raster_paths, n_bands, width, height, dtype=np.float32, band_index=None
    ):
        """
        Merge method that keeps the first value in write those positions where more than one raster write its values.

        Parameters:
            dst (_type_): destination raster

            raster_paths (List[str]): raster paths to merge

            n_bands (int): bands of each raster

            width (int): width of the merge raster

            height (int): height of the merge raster

            dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

            band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

        Returns:
            ndarray: resulting merge
        """

        final_data = np.empty(shape=(n_bands, height, width), dtype=dtype)
        final_data[:] = np.NaN

        for raster_path in tqdm(raster_paths):
            with rasterio.open(raster_path, "r") as src:
                data = (
                    src.read()
                    if band_index is None
                    else np.array([src.read(band_index)])
                )

                lons, lats = __latlon_to_index(dst, src)

                dst_arr = final_data[:, lons, lats]
                np.copyto(dst_arr, data, where=np.isnan(dst_arr) * ~np.isnan(data))
                final_data[:, lons, lats] = dst_arr

        return final_data

    def __max(
        dst, raster_paths, n_bands, width, height, dtype=np.float32, band_index=None
    ):
        """
        Merge method that calculates the max value in those positions where more than one raster write its values.

        Parameters:
            dst (_type_): destination raster

            raster_paths (List[str]): raster paths to merge

            n_bands (int): bands of each raster

            width (int): width of the merge raster

            height (int): height of the merge raster

            dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

            band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

        Returns:
            ndarray: resulting merge
        """

        final_data = np.empty(shape=(n_bands, height, width), dtype=dtype)
        final_data[:] = np.NaN

        for raster_path in tqdm(raster_paths):
            with rasterio.open(raster_path, "r") as src:
                data = (
                    src.read()
                    if band_index is None
                    else np.array([src.read(band_index)])
                )

                lons, lats = __latlon_to_index(dst, src)

                final_data[:, lons, lats] = np.nanmax(
                    [data, final_data[:, lons, lats]], axis=0
                )

        return final_data

    def __min(
        dst, raster_paths, n_bands, width, height, dtype=np.float32, band_index=None
    ):
        """
        Merge method that calculates the min value in those positions where more than one raster write its values.

        Parameters:
            dst (_type_): destination raster

            raster_paths (List[str]): raster paths to merge

            n_bands (int): bands of each raster

            width (int): width of the merge raster

            height (int): height of the merge raster

            dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

            band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

        Returns:
            ndarray: resulting merge
        """

        final_data = np.empty(shape=(n_bands, height, width), dtype=dtype)
        final_data[:] = np.NaN

        for raster_path in tqdm(raster_paths):
            with rasterio.open(raster_path, "r") as src:
                data = (
                    src.read()
                    if band_index is None
                    else np.array([src.read(band_index)])
                )

                lons, lats = __latlon_to_index(dst, src)

                final_data[:, lons, lats] = np.nanmin(
                    [data, final_data[:, lons, lats]], axis=0
                )

        return final_data

    methods = {
        "mean": __mean,
        "first": __first,
        "max": __max,
        "min": __min,
    }

    method = methods.get(method, method)

    with rasterio.open(raster_paths[0], "r") as raster:
        n_bands = raster.count
        profile = raster.profile
        if len(raster_paths) > 1:
            width, height, transform = __get_merge_transform(raster_paths)
            profile["width"] = width
            profile["height"] = height
            profile["transform"] = transform
        else:
            width, height = raster.width, raster.height

    if band_names is not None and n_bands == len(band_names):
        profile["count"] = 1

        with rasterio.open(
            output_name.replace(".", f"_band_{band_names[0]}."), "w", **profile
        ) as dst:
            data = method(dst, raster_paths, n_bands, width, height, dtype)

        for band_index in range(n_bands):
            with rasterio.open(
                output_name.replace(".", f"_band_{band_names[band_index]}."),
                "w",
                **profile,
            ) as dst:
                dst.write(np.array([data[band_index]]))
    else:
        with rasterio.open(output_name, "w", **profile) as dst:
            dst.write(method(dst, raster_paths, n_bands, width, height, dtype))

    return output_name


### END Mosaicking ###

### START Downsample ###


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


### END Downsample ###

### START Georeferenced Plotting


def plot_basemap(
    ax: plt.Axes,
    west: float,
    south: float,
    east: float,
    north: float,
    source: str | Bunch = cx.providers.OpenStreetMap.Mapnik,
    clip: bool = False,
) -> plt.Axes:
    """
    This function loads a basemap and plot in the axes provides using pseudo-Mercator projection (epsg:3857).

    NOTE:
        - west, east, south and north must longitudes and latitudes based on crs=epsg:4326.
        - local basemaps like Sentinel-2 must be georeferenced with crs=epsg:4326.
        - If basemap param is a string (filename) it is loaded and plotted; Otherwise a basemap is searched with contextily based on west, east, south and north params.

    Parameters:
        ax (plt.Axes): axes where to plot

        west (float): minimum longitude

        south (float): minimum latitude

        east (float): maximum longitude

        north (float): maximum latitude

        source (str | Bunch, optional): Filename or Basemap provider from contextily to plot. Defaults to cx.providers.OpenStreetMap.Mapnik.

        clip (bool, optional): If True and source is a filename, the local basemap will be clipped base on west, east, south and north params. Defaults to False.

    Returns:
        plt.Axes: axes with the basemap plotted
    """

    if isinstance(source, str):
        latlon_projection: str = "epsg:4326"
        pseudo_mercator_projection: str = "epsg:3857"
        transformer: Transformer = Transformer.from_crs(
            latlon_projection, pseudo_mercator_projection, always_xy=True
        )

        with rioxarray.open_rasterio(source) as src:
            if clip:
                mask_lon = (src.x >= west) & (src.x <= east)
                mask_lat = (src.y >= south) & (src.y <= north)
                new_src = src.where(mask_lon & mask_lat, drop=True)
            else:

                new_src = src

            data = np.transpose(new_src.values, (1, 2, 0))
            new_west, new_north = transformer.transform(
                new_src.x.min(), new_src.y.max()
            )
            new_east, new_south = transformer.transform(
                new_src.x.max(), new_src.y.min()
            )
            extent = new_west, new_east, new_south, new_north

    else:
        data, extent = cx.bounds2img(west, south, east, north, ll=True, source=source)

    ax.imshow(data, extent=extent)
    gl = ax.gridlines(
        draw_labels=True, linewidth=0.8, color="black", alpha=0.3, linestyle="-"
    )
    gl.top_labels = gl.right_labels = False
    gl.xformatter, gl.yyformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER

    return ax


def plot_georeferenced_data(
    ax: plt.Axes,
    filename: str,
    vmin: float,
    vmax: float,
    cmap: str,
    norm: None = None,
    basemap: Bunch | str = None,
) -> Tuple[plt.Axes, AxesImage]:
    """
    This function loads a raster in .tif format, and plot it (using pseudo-Mercator projection (epsg:3857)) over a given axes with its values georeferenced.

    NOTE: The raster must have only one band.

    Args:
        ax (plt.Axes): axes where to plot

        filename (str): tif file to plot

        vmin (float): minimum value for colormap

        vmax (float): maximum value for colormap

        cmap (str): colormap name from matplotlib defaults

        norm (None, optional): norm for colormap like Linear, Log10. If None it's applied Linear Norm. Defaults to None.

        basemap (str | Bunch, optional): Filename or Basemap provider from contextily to plot. If it's specified, plot_basemap function will be executed with tif bounds.  Defaults to None

    Returns:
        Tuple[plt.Axes, AxesImage]: axes with data plotted and a new axes for colobar settings.
    """

    latlon_projection: str = "epsg:4326"
    pseudo_mercator_projection: str = "epsg:3857"
    transformer: Transformer = Transformer.from_crs(
        latlon_projection, pseudo_mercator_projection, always_xy=True
    )

    with rasterio.open(filename) as src:
        cols, rows = np.meshgrid(np.arange(src.width), np.arange(src.height))
        xs, ys = rasterio.transform.xy(src.transform, rows, cols)
        lons, lats = np.array(xs), np.array(ys)

        if basemap is not None:
            ax = plot_basemap(
                ax,
                src.bounds.left,
                src.bounds.bottom,
                src.bounds.right,
                src.bounds.top,
                basemap,
                True,
            )

    with rioxarray.open_rasterio(filename) as src:
        lon, lat = transformer.transform(lons, lats)
        src.coords["lon"] = (("y", "x"), lon)
        src.coords["lat"] = (("y", "x"), lat)

        mappable = src.plot(
            ax=ax,
            x="lon",
            y="lat",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            norm=norm,
            add_colorbar=False,
        )

    return ax, mappable


### END Georeferenced Plotting
