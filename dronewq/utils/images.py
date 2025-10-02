import numpy as np
import pandas as pd
import rasterio
import os


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
