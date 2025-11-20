import numpy as np
import rasterio
from rasterio.transform import Affine
from tqdm import tqdm

from .geometry import (
    Paralelogram2D,
    euclidean_distance,
    get_center,
)

def __latlon_to_index(dst, src):
    """
    Given a source dataset and a destination dataset.
    Get the latitudes and longitudes that correspond
    to move the source data to the destination data.

    Parameters
        dst (_type_): Destination dataset

        src (DatasetReader): Source dataset

    Returns
        ndarray: List of latitudes and longitudes
    """
    cols, rows = np.meshgrid(np.arange(src.width), np.arange(src.height))

    xs, ys = rasterio.transform.xy(src.transform, rows, cols)
    lons, lats = np.array(xs), np.array(ys)

    coords_to_index = np.array(
        [dst.index(lons[i], lats[i]) for i in np.arange(src.height)],
    )
    lons, lats = coords_to_index[:, 0, :], coords_to_index[:, 1, :]

    return lons, lats


def __get_raster_corners(raster_path):
    """
    Given a raster path, return a list of its corners based on its transformation matrix.

    Parameters
        raster_path (str): path of the raster to be processed

    Returns
        List[Tuple[float, float]]: List with the 4 corners of the raster
    """
    with rasterio.open(raster_path) as raster:
        w, h = raster.width, raster.height
        result = [
            raster.transform * p
            for p in [(0, 0), (0, h - 1), (w - 1, h - 1), (w - 1, 0)]
        ]

    return result


def __get_raster_corners_by_params(transform, width, height):
    """
    Given a transformation matrix, a width and a height, return a list of corners based on the given transformation matrix.

    Parameters
        transform (Affine): transformation matrix

        width (int): transformation width

        height (int): transformation height

    Returns
        List[Tuple[float, float]]: List with the 4 corners of the raster
    """
    return [
        transform * p
        for p in [(0, 0), (0, height - 1), (width - 1, height - 1), (width - 1, 0)]
    ]


def __get_merge_transform(raster_paths, max_iterations=10000):
    """
    This function returns a transform matrix that contains of the specified rasters

    Parameters
        raster_paths (set): raster paths to merge

        max_iterations (int, optional): additional merge parameters. Default is 2000

    Returns
        Tuple[int, int, Affine]: width, height and transformation matrix of the merge
    """
    with rasterio.open(raster_paths[0]) as src:
        original_transform = src.transform
        transform = src.transform
        width = src.width
        height = src.height
        res = src.res

    # NOTE: This loop seems unnecessary. Questionable...
    for raster_path in raster_paths:
        with rasterio.open(raster_path) as src:
            if res[0] < src.res[0]:
                original_transform = src.transform
                transform = src.transform
                res = src.res

    raster_corners = np.array(
        [__get_raster_corners(raster_path=raster_path) for raster_path in raster_paths],
    ).reshape(-1, 2)

    mid_point = get_center(raster_corners)
    mid_point_first_capture = get_center(raster_corners[0:4])
    c, f = (
        mid_point[0] + (raster_corners[0][0] - mid_point_first_capture[0]),
        mid_point[1] + (raster_corners[0][1] - mid_point_first_capture[1]),
    )

    transform = Affine(
        a=original_transform.a,
        b=original_transform.b,
        c=c,
        d=original_transform.d,
        e=original_transform.e,
        f=f,
    )

    paralelo = Paralelogram2D(
        np.array(__get_raster_corners_by_params(transform, width, height)),
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
        round(euclidean_distance(paralelo.points[0], paralelo.points[-1]) / res[0]),
    )
    height = int(
        round(euclidean_distance(paralelo.points[0], paralelo.points[1]) / res[1]),
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
    dst,
    raster_paths,
    n_bands,
    width,
    height,
    dtype=np.float32,
    band_index=None,
):
    """
    Merge method that calculates the mean value in those positions where more than one raster write its values.

    Parameters
        dst (_type_): destination raster

        raster_paths (List[str]): raster paths to merge

        n_bands (int): bands of each raster

        width (int): width of the merge raster

        height (int): height of the merge raster

        dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

        band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

    Returns
        ndarray: resulting merge
    """
    final_data = np.zeros(shape=(n_bands, height, width), dtype=dtype)
    count = np.zeros(shape=(n_bands, height, width), dtype=np.uint8)

    for raster_path in tqdm(raster_paths):
        with rasterio.open(raster_path, "r") as src:
            data = (
                src.read() if band_index is None else np.array([src.read(band_index)])
            )

            lons, lats = __latlon_to_index(dst, src)

            final_data[:, lons, lats] = np.nansum(
                [data, final_data[:, lons, lats]],
                axis=0,
            )
            count[:, lons, lats] = np.nansum(
                [~np.isnan(data), count[:, lons, lats]],
                axis=0,
            )

    return np.divide(final_data, count)


def __first(
    dst,
    raster_paths,
    n_bands,
    width,
    height,
    dtype=np.float32,
    band_index=None,
):
    """
    Merge method that keeps the first value in write those positions where more than one raster write its values.

    Parameters
        dst (_type_): destination raster

        raster_paths (List[str]): raster paths to merge

        n_bands (int): bands of each raster

        width (int): width of the merge raster

        height (int): height of the merge raster

        dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

        band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

    Returns
        ndarray: resulting merge
    """
    final_data = np.empty(shape=(n_bands, height, width), dtype=dtype)
    final_data[:] = np.nan

    for raster_path in tqdm(raster_paths):
        with rasterio.open(raster_path, "r") as src:
            data = (
                src.read() if band_index is None else np.array([src.read(band_index)])
            )

            lons, lats = __latlon_to_index(dst, src)

            dst_arr = final_data[:, lons, lats]
            np.copyto(dst_arr, data, where=np.isnan(dst_arr) * ~np.isnan(data))
            final_data[:, lons, lats] = dst_arr

    return final_data


def __max(dst, raster_paths, n_bands, width, height, dtype=np.float32, band_index=None):
    """
    Merge method that calculates the max value in those positions where more than one raster write its values.

    Parameters
        dst (_type_): destination raster

        raster_paths (List[str]): raster paths to merge

        n_bands (int): bands of each raster

        width (int): width of the merge raster

        height (int): height of the merge raster

        dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

        band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

    Returns
        ndarray: resulting merge
    """
    final_data = np.empty(shape=(n_bands, height, width), dtype=dtype)
    final_data[:] = np.nan

    for raster_path in tqdm(raster_paths):
        with rasterio.open(raster_path, "r") as src:
            data = (
                src.read() if band_index is None else np.array([src.read(band_index)])
            )

            lons, lats = __latlon_to_index(dst, src)

            final_data[:, lons, lats] = np.nanmax(
                [data, final_data[:, lons, lats]],
                axis=0,
            )

    return final_data


def __min(dst, raster_paths, n_bands, width, height, dtype=np.float32, band_index=None):
    """
    Merge method that calculates the min value in those positions where more than one raster write its values.

    Parameters
        dst (_type_): destination raster

        raster_paths (List[str]): raster paths to merge

        n_bands (int): bands of each raster

        width (int): width of the merge raster

        height (int): height of the merge raster

        dtype (dtype, optional): dtype of the merge raster. Defaults to np.float32.

        band_index (int | None, optional): if not None we only merge the specified band. Defaults to None.

    Returns
        ndarray: resulting merge
    """
    final_data = np.empty(shape=(n_bands, height, width), dtype=dtype)
    final_data[:] = np.nan

    for raster_path in tqdm(raster_paths):
        with rasterio.open(raster_path, "r") as src:
            data = (
                src.read() if band_index is None else np.array([src.read(band_index)])
            )

            lons, lats = __latlon_to_index(dst, src)

            final_data[:, lons, lats] = np.nanmin(
                [data, final_data[:, lons, lats]],
                axis=0,
            )

    return final_data
