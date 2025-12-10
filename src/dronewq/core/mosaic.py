"""
Not much is changed from the original code
Only separated the methods from the main
part of the code.
Refactored by: Temuulen
"""

import os

import numpy as np
import rasterio
import rasterio.transform
from rasterio.enums import Resampling
from rasterio.transform import Affine

from .mosaic_methods import __first, __get_merge_transform, __max, __mean, __min


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
    Mosaic multiple raster files into a single GeoTIFF.

    This function reads all raster files in `input_dir` and merges them into
    one mosaic using the specified merging method. If `band_names` is provided,
    the mosaicked result is written as multiple single-band files—one file per
    band—named using the provided band names. Otherwise, a single multi-band
    raster is written.

    Parameters
    ----------
    input_dir : str
        Path to a directory containing the input rasters to mosaic.

    output_dir : str
        Path to the directory where the output raster(s) will be saved.
        The directory is created if it does not exist.

    output_name : str
        Base filename (without extension) for the mosaicked output.

    method : {"mean", "first", "min", "max"}, optional
        Method used to combine overlapping pixels when multiple rasters
        cover the same area. Default is `"mean"`.

    dtype : numpy.dtype, optional
        Data type of the output raster. Defaults to `np.float32`.

    band_names : list[str] or None, optional
        If provided, one output file will be created per band, using the given
        band names (e.g., `["red", "green", "blue"]`).
        The number of entries must match the number of bands in the input
        rasters.

    Returns
    -------
    str
        The filepath of the generated mosaic (or the first band file if
        `band_names` is provided).

    Notes
    -----
    - This function assumes all rasters share the same coordinate reference
      system (CRS).
    - When multiple input files are found, the output extent is computed to
      cover all rasters.
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
    input_tif,
    output_dir,
    scale_x,
    scale_y,
    method=Resampling.average,
):
    """
    Downsample a raster by reducing its spatial resolution.

    This function reads the input raster and resizes it by the specified
    factors (`scale_x`, `scale_y`) using the given resampling method.
    The resulting downsampled raster is saved to `output_dir`.

    Parameters
    ----------
    input_tif : str
        Path to the input GeoTIFF to downsample.

    output_dir : str
        Directory where the downsampled raster will be saved.
        The directory is created if it does not exist.

    scale_x : int
        Horizontal downsampling factor.
        For example, `scale_x=2` halves the raster width.

    scale_y : int
        Vertical downsampling factor.
        For example, `scale_y=2` halves the raster height.

    method : rasterio.enums.Resampling, optional
        The resampling algorithm to apply (e.g., `Resampling.average`,
        `Resampling.nearest`, `Resampling.bilinear`).
        Default is `Resampling.average`.

    Returns
    -------
    str
        The filepath of the generated downsampled raster.

    Notes
    -----
    - The affine transform is automatically scaled to match the new resolution.
    - For a full list of resampling methods, see Rasterio's documentation.
    """

    os.makedirs(output_dir, exist_ok=True)

    raster_name = os.path.basename(input_tif)
    out_name = os.path.join(
        output_dir,
        f"{raster_name.split('.')[0]}_x_{scale_x}_y_{scale_y}_method_{method.name}.tif",
    )

    with rasterio.open(input_tif, "r") as dataset:
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
    return out_name
