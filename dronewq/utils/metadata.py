import os
import pandas as pd
import math


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
        img = capture.images[0]
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
