import os
import rasterio
import rasterio.transform
import tqdm
import numpy as np
from rasterio.transform import Affine

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

