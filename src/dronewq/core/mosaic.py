import glob
import os

import numpy as np
import rasterio
import rasterio.transform
from rasterio.enums import Resampling
from rasterio.transform import Affine
from tqdm import tqdm

from .mosaic_methods import (
    __first,
    __get_merge_transform,
    __max,
    __mean,
    __min,
)

# Geometry functions
def mosaic(
    input_dir,
    output_dir,
    output_name,
    method="mean",
    dtype=np.float32,
    band_names=None,
):
    """
    This function moasics all the given rasters into a single raster file

    Parameters
        input_dir: a string containing the directory filepath of images to be mosaicked

        output_dir: a string containing the directory filepath to save the output

        output_name: a string of the output name of mosaicked .tif

        method: Method to be used when multiple captures coincide at same location. Options: 'mean', 'first', 'min', 'max'. Defaults to 'mean'.

        dtype: dtype of the mosaicked raster. Defaults to np.float32.

        band_names: List of band names. If it is not None, it writes one file for each band instead of one file with all the bands. Defaults to None.

    Returns
        Mosaicked .tif file
    """

    def listdir_fullpath(d):
        return [os.path.join(d, f) for f in os.listdir(d)]

    raster_paths = listdir_fullpath(input_dir)

    out_folder_path = output_dir
    os.makedirs(out_folder_path, exist_ok=True)

    output_name = os.path.join(out_folder_path, f"{output_name}.tif")

    methods = {
        "mean": __mean,
        "first": __first,
        "max": __max,
        "min": __min,
    }

    method = methods.get(method)

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
            output_name.replace(".", f"_band_{band_names[0]}."),
            "w",
            **profile,
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


def downsample(
    input_dir,
    output_dir,
    scale_x,
    scale_y,
    method=Resampling.average,
):
    """
    This function performs a downsampling to reduce the spatial resolution of
    the final mosaic. The downsampled raster is written to output_dir.

    Parameters
        input_dir: A string containing input directory filepath

        output_dir: A string containing output directory filepath

        scale_x: proportion by which the width of each file will be resized

        scale_y: proportion by which the height of each file will be resized

        method: the resampling method to perform.
            Defaults to Resampling.average
            Please see `https://rasterio.readthedocs.io/en/stable/api/rasterio.enums.html#rasterio.enums.Resampling`
            for other resampling methods.
    """
    os.makedirs(output_dir, exist_ok=True)
    raster_paths = glob.glob(os.path.join(input_dir, "*"))

    for raster_path in tqdm(raster_paths):
        raster_name = os.path.basename(raster_path)
        out_name = os.path.join(
            output_dir,
            f"{raster_name.split('.')[0]}_x_{scale_x}_y_{scale_y}_method_{method.name}.tif",
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
                (dataset.width / data.shape[-1]),
                (dataset.height / data.shape[-2]),
            )

            dst_kwargs = dataset.meta.copy()
            dst_kwargs.update(
                {
                    "crs": dataset.crs,
                    "transform": dst_transform,
                    "width": data.shape[-1],
                    "height": data.shape[-2],
                },
            )

            with rasterio.open(out_name, "w", **dst_kwargs) as dst:
                dst.write(data)


# END Mosaicking
