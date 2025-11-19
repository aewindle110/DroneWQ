import math
import os

import pandas as pd

from micasense.imageset import ImageSet

def write_metadata_csv(img_dir, csv_output_path):
    """
    Grabs EXIF metadata from img_set and writes it to outputPath/metadata.csv.

    Parameters
        img_dir: A string containing the filepath of the raw .tifs
        csv_output_path: A string containing the filepath to store metadata.csv

    Returns
        A string path to the generated .csv file
    """
    if not os.path.exists(img_dir):
        raise FileNotFoundError(f"Image directory {img_dir} does not exist.")

    img_set = ImageSet.from_directory(img_dir)

    def decdeg2dms(dd):
        """Convert decimal degrees to degrees, minutes, seconds."""
        minutes, seconds = divmod(abs(dd) * 3600, 60)
        degrees, minutes = divmod(minutes, 60)
        degrees = degrees if dd >= 0 else -degrees
        return (degrees, minutes, seconds)

    # Build list of dictionaries instead of nested lists
    data_records = []

    for i, capture in enumerate(img_set.captures):
        filename = f"capture_{i + 1}.tif"
        fullOutputPath = os.path.join(img_dir, filename)

        img = capture.images[0]
        width, height = img.meta.image_size()
        lat, lon, alt = capture.location()

        # Vectorizable latitude/longitude calculations
        latdeg = decdeg2dms(lat)[0]
        londeg = decdeg2dms(lon)[0]
        latdir = "S" if latdeg < 0 else "N"
        londir = "W" if londeg < 0 else "E"
        latdeg = abs(latdeg)
        londeg = abs(londeg)

        # Extract timestamp once
        utc_time = capture.utc_time()
        datestamp = utc_time.strftime("%Y-%m-%d")
        timestamp = utc_time.strftime("%H:%M:%S")

        resolution = img.focal_plane_resolution_px_per_mm
        focal_length = img.focal_length
        sensor_size_x = width / resolution[0]
        sensor_size_y = height / resolution[1]

        # Build record dictionary
        record = {
            "filename": filename,
            "dirname": fullOutputPath,
            "DateStamp": datestamp,
            "TimeStamp": timestamp,
            "Latitude": lat,
            "LatitudeRef": latdir,
            "Longitude": lon,
            "LongitudeRef": londir,
            "Altitude": alt,
            "SensorX": sensor_size_x,
            "SensorY": sensor_size_y,
            "FocalLength": focal_length,
            "Yaw": (img.dls_yaw * 180 / math.pi) % 360,
            "Pitch": (img.dls_pitch * 180 / math.pi) % 360,
            "Roll": (img.dls_roll * 180 / math.pi) % 360,
            "SolarElevation": img.solar_elevation,
            "ImageWidth": width,
            "ImageHeight": height,
            "XResolution": resolution[1],
            "YResolution": resolution[0],
            "ResolutionUnits": "mm",
        }

        data_records.append(record)

    # Create DataFrame from list of dictionaries (more efficient)
    df = pd.DataFrame(data_records)

    # Set index and save
    df = df.set_index("filename")

    # Optional: Parse datetime column in vectorized manner
    # df['UTC-Time'] = pd.to_datetime(df['DateStamp'] + ' ' + df['TimeStamp'],
    #                                  format="%Y-%m-%d %H:%M:%S")

    fullCsvPath = os.path.join(csv_output_path, "metadata.csv")
    df.to_csv(fullCsvPath)

    return fullCsvPath
