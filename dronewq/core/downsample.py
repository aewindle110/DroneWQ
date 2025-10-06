import os
import glob
import rasterio
from tqdm import tqdm
from rasterio.transform import Affine
from rasterio.enums import Resampling


# TODO: Fix method default
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
