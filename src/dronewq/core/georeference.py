import os
from typing import List, Tuple

import cameratransform as ct
import numpy as np
import rasterio
from pyproj import CRS
from tqdm import tqdm

def compute_flight_lines(captures_yaw, altitude, pitch, roll, threshold=10):
    """
    A function that returns a list of yaw, altitude, pitch, roll values from different flight transects to be used in the georeference() function. The function calculates the median of all yaw angles. For yaw angles < median, it calculates the median of filtered captures. If yaw angle is between filtered median - threshold and filtered median + threshold, it is considered a valid capture. Simiarly, for yaw angles > median, if yaw angle is between filtered median - threshold and filtered median + threshold, it is considered a valid capture.

    Parameters
        captures_yaw: Can either be a fixed number or pulled from the metadata

        altitude: Can either be a fixed number or pulled from the metadata

        pitch: Can either be a fixed number or pulled from the metadata

        roll: Can either be a fixed number or pulled from the metadata

        threshold: A value to be used to determine what captures have yaw angles that are considered valid. Default is 10.

    Returns
        List[int]: list of pairs(start, end) for each trasenct
    """

    def __compute_lines(
        lines: List[Tuple[int, int]], indexes: List[int], start: int = 0, end: int = 0,
    ):
        """
        A function that given a list of indexes where there are gaps,
        returns a list of pairs(start, end) for each interval

        Parameters
            lines (List[Tuple[int, int]]): list where to write the result

            indexes (List[int]): list of indexes

            start (int, optional): first index. Defaults to 0.

            end (int, optional): last index. Defaults to 0.

        Returns
            List[int]: list of pairs(start, end) for each interval
        """
        for index in indexes:
            if abs(end - index) > 1:
                if start != end:
                    lines.append((int(start), int(end)))
                start = index
            end = index
        if start != end:
            lines.append((int(start), int(end)))

        return list(set(lines))

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

    Parameters
        metadata: A Pandas dataframe of the metadata

        input_dir: A string containing the directory filepath of the images to be retrieved for georeferencing.

        output_dir: A string containing the directory filepath to be saved.

        lines: Selection of images to be processed. Defaults to None. Example: [slice(0,10)]

        altitude: sets the altitude where all captures were taken. Defaults to None which uses the altitude data saved in the metadata for each respective capture.

        yaw: sets the sensor's direction angle during all captures. Defaults to None which uses the yaw angle saved in the metadata for each respective capture.

        pitch: sets the sensor's pitch angle during all captures. Defaults to 0 which means the sensor was horizontal to the ground.

        roll: sets the sensor's roll angle during all captures. Defaults to 0 which means the sensor was horizontal to the ground.

        axis_to_flip: The axis to apply a flip. Defaults to 1.

    Returns
        Georeferenced .tifs in output_dir
    """

    def __get_transform(f, sensor_size, image_size, lat, lon, alt, yaw, pitch, roll):
        """
        Calculates a transformation matrix for a given capture in order to get every lat, lon for each pixel in the image.

        Parameters
            f (float): focal_length

            sensor_size (Tuple[float, float]): correspondence pixel -> milimeter

            image_size (Tuple[int, int]): number of pixels for width and height

            lat (float): latitude of camera

            lon (float): longitude of camera

            alt (float): altitude of camera

            yaw (float): yaw of camera

            pitch (float): tilt of camera

            roll (float): roll of camera

        Returns
            Affine: transformation matrix
        """
        cam = ct.Camera(
            ct.RectilinearProjection(
                focallength_mm=f, sensor=sensor_size, image=image_size,
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
            row=0, col=0, x=coords[0, 1], y=coords[0, 0], z=coords[0, 2],
        )
        gcp2 = rasterio.control.GroundControlPoint(
            row=image_size[0] - 1, col=0, x=coords[1, 1], y=coords[1, 0], z=coords[1, 2],
        )
        gcp3 = rasterio.control.GroundControlPoint(
            row=image_size[0] - 1,
            col=image_size[1] - 1,
            x=coords[2, 1],
            y=coords[2, 0],
            z=coords[2, 2],
        )
        gcp4 = rasterio.control.GroundControlPoint(
            row=0, col=image_size[1] - 1, x=coords[3, 1], y=coords[3, 0], z=coords[3, 2],
        )

        return rasterio.transform.from_gcps([gcp1, gcp2, gcp3, gcp4])

    def __get_georefence_by_uuid(
        metadata, lines=None, altitude=None, yaw=None, pitch=None, roll=None,
    ):
        """
        Given a DataFrame and a list of flight lines, calculate a dictionary with the transformation matrix for each capture

        Parameters
            metadata (DataFrame): Pandas DataFrame that contains information like capture latitude, longitude, ...

            lines (List[slice], optional): List that indicates the flight lines. Defaults to None which means [ slice(0, None) ] = all captures.

            altitude (float, optional): altitude of camera

            yaw (float, optional): yaw of camera

            pitch (float, optional): tilt of camera

            roll (float, optional): roll of camera

        Returns
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

    os.makedirs(output_dir, exist_ok=True)

    metadata = metadata.set_index(metadata["filename"])
    georefence_by_uuid = __get_georefence_by_uuid(
        metadata, lines, altitude, yaw, pitch, roll,
    )

    for uuid, transform in tqdm(
        georefence_by_uuid.items(), total=len(georefence_by_uuid.items()),
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
                os.path.join(output_dir, __convert_to_tif(uuid)), "w", **profile,
            ) as dst:
                dst.write(
                    data if axis_to_flip is None else np.flip(data, axis=axis_to_flip),
                )
