"""
Not much is changed from the original code
Refactored docstrings: Temuulen
"""
import os

import cameratransform as ct
import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS
from tqdm import tqdm


def compute_flight_lines(
    captures_yaw,
    altitude,
    pitch,
    roll,
    threshold=10,
) -> list[dict[str, float]]:
    """
    Identify contiguous flight transects based on yaw measurements and compute
    representative orientation parameters for each transect.

    The function groups captures into two broad yaw directions—those below the
    global median yaw and those above it. For each direction, it computes a
    filtered median yaw by selecting captures whose yaw values fall within
    `± threshold` degrees of that direction's median. Contiguous index ranges
    within these filtered captures are treated as individual flight lines.

    Each flight line is returned as a dictionary containing:
    - start/end indices of the transect,
    - the median yaw of that transect,
    - the supplied altitude, pitch, and roll values.

    Parameters
    ----------
    captures_yaw : array-like
        Sequence of yaw values (in degrees) for each capture.

    altitude : float
        Altitude to assign to all generated flight lines.

    pitch : float
        Pitch angle (in degrees) assigned to all flight lines.

    roll : float
        Roll angle (in degrees) assigned to all flight lines.

    threshold : float, optional
        Accepted deviation (in degrees) from a direction's median yaw when
        determining valid captures. Default is 10.

    Returns
    -------
    list[dict[str, float]]
        A list of flight-line descriptions. Each dictionary contains:
            - "start": index of first capture in transect,
            - "end": index after the last capture in transect,
            - "yaw": median yaw for the transect,
            - "pitch": pitch angle,
            - "roll": roll angle,
            - "alt": altitude value.
    """

    def __compute_lines(
        lines: list[tuple[int, int]],
        indexes: list[int] | np.ndarray,
        start: int = 0,
        end: int = 0,
    ) -> list[tuple[int, int]]:
        """
        A function that given a list of indexes where there are gaps,
        returns a list of pairs(start, end) for each interval

        Parameters
        ----------
            lines (list[tuple[int, int]]): list where to write the result

            indexes (list[int] | np.ndarray): list of indexes

            start (int, optional): first index. Defaults to 0.

            end (int, optional): last index. Defaults to 0.

        Returns
        -------
            list[set]: list of pairs(start, end) for each interval
        """
        for index in indexes:
            if abs(end - index) > 1:
                if start != end:
                    lines.append((int(start), int(end)))
                start = index
            end = index
        if start != end:
            lines.append((int(start), int(end)))

        return lines

    median_yaw = np.median(captures_yaw)
    indexes = np.where(captures_yaw < median_yaw)[0]
    indexes = np.where(
        (np.median(captures_yaw[indexes]) - threshold <= captures_yaw)
        & (captures_yaw <= np.median(captures_yaw[indexes]) + threshold),
    )[0]

    lines = __compute_lines([], indexes)

    median_yaw = np.median(captures_yaw)
    indexes = np.where(captures_yaw > median_yaw)[0]

    indexes = np.where(
        (np.median(captures_yaw[indexes]) - threshold <= captures_yaw)
        & (captures_yaw <= np.median(captures_yaw[indexes]) + threshold),
    )[0]

    lines = __compute_lines(lines, indexes)
    lines.sort()

    flight_lines = [
        {
            "start": line[0],
            "end": line[1] + 1,
            "yaw": float(np.median(captures_yaw[line[0]: line[1]])),
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
) -> None:
    """
    Georeference a set of image captures using their metadata and orientation
    parameters, producing georeferenced GeoTIFF files.

    For each capture, this function builds an affine transformation using:
    - focal length,
    - sensor size,
    - image dimensions,
    - GPS coordinates,
    - yaw/pitch/roll (from metadata or provided overrides).

    The function then applies the transform and saves the output as a GeoTIFF
    in `output_dir`. Captures may be restricted to specific flight lines
    (as produced by `compute_flight_lines()`).

    Parameters
    ----------
    metadata : pandas.DataFrame
        DataFrame containing per-image metadata. Must include:
        FocalLength, SensorX, SensorY, ImageWidth, ImageHeight,
        Latitude, Longitude, Altitude, Pitch, Roll, Yaw, filename.

    input_dir : str
        Directory containing the source images.

    output_dir : str
        Directory where georeferenced images are written.

    lines : list[dict] or None, optional
        Flight line definitions such as those returned by
        `compute_flight_lines()`. If None, all captures are processed.

    altitude : float or None, optional
        Override altitude for all captures. If None, metadata altitude is used.

    yaw : float or None, optional
        Override yaw for all captures. If None, metadata yaw is used.

    pitch : float, optional
        Override pitch angle for all captures. Default is 0.

    roll : float, optional
        Override roll angle for all captures. Default is 0.

    axis_to_flip : int or None, optional
        Axis along which to flip the image before writing. Default is 1.
        Set to None to disable flipping.

    Returns
    -------
    None
        Writes georeferenced `.tif` files into `output_dir`.
    """

    def __get_transform(
        f,
        sensor_size,
        image_size,
        lat,
        lon,
        alt,
        yaw,
        pitch,
        roll,
    ):
        """
        Compute an affine geotransformation matrix for a single capture.

        A rectilinear camera model is constructed using the capture’s intrinsic
        parameters (focal length, sensor size, image dimensions) and its pose
        (GPS position and yaw/pitch/roll). The four image corners are projected
        to geographic coordinates, and these coordinates are used as ground
        control points to derive an affine transform.

        Parameters
        ----------
        f : float
            Focal length in millimeters.

        sensor_size : tuple[float, float]
            Sensor dimensions in millimeters, ordered (width, height).

        image_size : tuple[int, int]
            Image dimensions in pixels, ordered (width, height).

        lat : float
            Camera latitude.

        lon : float
            Camera longitude.

        alt : float
            Camera altitude in meters.

        yaw : float
            Yaw angle in degrees.

        pitch : float
            Pitch angle in degrees.

        roll : float
            Roll angle in degrees.

        Returns
        -------
        Affine
            Affine transformation derived from the four GCPs.
        """
        cam = ct.Camera(
            ct.RectilinearProjection(
                focallength_mm=f,
                sensor=sensor_size,
                image=image_size,
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
            ],
        )

        gcp1 = rasterio.control.GroundControlPoint(
            row=0,
            col=0,
            x=coords[0, 1],
            y=coords[0, 0],
            z=coords[0, 2],
        )
        gcp2 = rasterio.control.GroundControlPoint(
            row=image_size[0] - 1,
            col=0,
            x=coords[1, 1],
            y=coords[1, 0],
            z=coords[1, 2],
        )
        gcp3 = rasterio.control.GroundControlPoint(
            row=image_size[0] - 1,
            col=image_size[1] - 1,
            x=coords[2, 1],
            y=coords[2, 0],
            z=coords[2, 2],
        )
        gcp4 = rasterio.control.GroundControlPoint(
            row=0,
            col=image_size[1] - 1,
            x=coords[3, 1],
            y=coords[3, 0],
            z=coords[3, 2],
        )

        return rasterio.transform.from_gcps([gcp1, gcp2, gcp3, gcp4])

    def __get_georefence_by_uuid(
        metadata: pd.DataFrame,
        lines: list[dict[str, float | None]] | None = None,
        altitude: float | None = None,
        yaw: float | None = None,
        pitch: float | None = None,
        roll: float | None = None,
    ):
        """
        Build affine geotransforms for each capture, grouped by flight lines.

        For every capture in every flight line, this function determines the
        orientation parameters (using overrides if provided), computes the
        corresponding affine transform via `__get_transform()`, and stores the
        result in a dictionary keyed by filename.

        Parameters
        ----------
        metadata : pandas.DataFrame
            DataFrame containing capture metadata, indexed by filename.

        lines : list[dict] or None, optional
            List of flight-line dictionaries. If None, a single line spanning
            all captures is used.

        altitude, yaw, pitch, roll : float or None, optional
            Optional parameter overrides applied to all captures in each line.

        Returns
        -------
        dict[str, Affine]
            Mapping from filename (UUID) to its computed affine transformation.
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
            captures = metadata.iloc[line["start"]: line["end"]]
            for _, capture in captures.iterrows():
                focal = capture["FocalLength"]
                image_size = (capture["ImageWidth"],
                              capture["ImageHeight"])[::-1]
                sensor_size = (capture["SensorX"], capture["SensorY"])[::-1]

                lon = float(capture["Longitude"])
                lat = float(capture["Latitude"])
                alt = line["alt"] or float(capture["Altitude"])
                capture_pitch = line["pitch"] if line["pitch"] is not None else float(
                    capture["Pitch"])
                capture_roll = line["roll"] if line["roll"] is not None else float(
                    capture["Roll"])
                capture_yaw = line["yaw"] if line["yaw"] is not None else float(
                    capture["Yaw"])

                filename = os.path.basename(capture["filename"])
                georeference_by_uuid[filename] = __get_transform(
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

        return georeference_by_uuid

    def __convert_to_tif(name):
        return ".".join([name.split(".")[0], "tif"])

    os.makedirs(output_dir, exist_ok=True)

    metadata = metadata.set_index(metadata["filename"])
    georefence_by_uuid = __get_georefence_by_uuid(
        metadata,
        lines,
        altitude,
        yaw,
        pitch,
        roll,
    )

    for uuid, transform in tqdm(
        georefence_by_uuid.items(),
        total=len(georefence_by_uuid.items()),
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
                os.path.join(output_dir, __convert_to_tif(uuid)),
                "w",
                **profile,
            ) as dst:
                dst.write(
                    data if axis_to_flip is None else np.flip(
                        data, axis=axis_to_flip),
                )
