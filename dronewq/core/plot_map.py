from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from pyproj import Transformer
from typing import Tuple
from xyzservices import Bunch
import matplotlib.pyplot as plt
from matplotlib.image import AxesImage
import contextily as cx
import numpy as np
import rioxarray
import rasterio


def plot_basemap(
    ax: plt.Axes,
    west: float,
    south: float,
    east: float,
    north: float,
    source: str | Bunch = cx.providers.OpenStreetMap.Mapnik,
    clip: bool = False,
) -> plt.Axes:
    """
    This function loads a basemap and plot in the axes provides using pseudo-Mercator projection (epsg:3857).

    NOTE:
        - west, east, south and north must longitudes and latitudes based on crs=epsg:4326.
        - local basemaps like Sentinel-2 must be georeferenced with crs=epsg:4326.
        - If basemap param is a string (filename) it is loaded and plotted; Otherwise a basemap is searched with contextily based on west, east, south and north params.

    Parameters:
        ax (plt.Axes): axes where to plot

        west (float): minimum longitude

        south (float): minimum latitude

        east (float): maximum longitude

        north (float): maximum latitude

        source (str | Bunch, optional): Filename or Basemap provider from contextily to plot. Defaults to cx.providers.OpenStreetMap.Mapnik.

        clip (bool, optional): If True and source is a filename, the local basemap will be clipped base on west, east, south and north params. Defaults to False.

    Returns:
        plt.Axes: axes with the basemap plotted
    """

    if isinstance(source, str):
        latlon_projection: str = "epsg:4326"
        pseudo_mercator_projection: str = "epsg:3857"
        transformer: Transformer = Transformer.from_crs(
            latlon_projection, pseudo_mercator_projection, always_xy=True
        )

        with rioxarray.open_rasterio(source) as src:
            if clip:
                mask_lon = (src.x >= west) & (src.x <= east)
                mask_lat = (src.y >= south) & (src.y <= north)
                new_src = src.where(mask_lon & mask_lat, drop=True)
            else:

                new_src = src

            data = np.transpose(new_src.values, (1, 2, 0))
            new_west, new_north = transformer.transform(
                new_src.x.min(), new_src.y.max()
            )
            new_east, new_south = transformer.transform(
                new_src.x.max(), new_src.y.min()
            )
            extent = new_west, new_east, new_south, new_north

    else:
        data, extent = cx.bounds2img(west, south, east, north, ll=True, source=source)

    ax.imshow(data, extent=extent)
    gl = ax.gridlines(
        draw_labels=True, linewidth=0.8, color="black", alpha=0.3, linestyle="-"
    )
    gl.top_labels = gl.right_labels = False
    gl.xformatter, gl.yyformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER

    return ax


def plot_georeferenced_data(
    ax: plt.Axes,
    filename: str,
    vmin: float,
    vmax: float,
    cmap: str,
    norm: None = None,
    basemap: Bunch | str = None,
) -> Tuple[plt.Axes, AxesImage]:
    """
    This function loads a raster in .tif format, and plot it (using pseudo-Mercator projection (epsg:3857)) over a given axes with its values georeferenced.

    NOTE: The raster must have only one band.

    Args:
        ax (plt.Axes): axes where to plot

        filename (str): tif file to plot

        vmin (float): minimum value for colormap

        vmax (float): maximum value for colormap

        cmap (str): colormap name from matplotlib defaults

        norm (None, optional): norm for colormap like Linear, Log10. If None it's applied Linear Norm. Defaults to None.

        basemap (str | Bunch, optional): Filename or Basemap provider from contextily to plot. If it's specified, plot_basemap function will be executed with tif bounds.  Defaults to None

    Returns:
        Tuple[plt.Axes, AxesImage]: axes with data plotted and a new axes for colobar settings.
    """

    latlon_projection: str = "epsg:4326"
    pseudo_mercator_projection: str = "epsg:3857"
    transformer: Transformer = Transformer.from_crs(
        latlon_projection, pseudo_mercator_projection, always_xy=True
    )

    with rasterio.open(filename) as src:
        cols, rows = np.meshgrid(np.arange(src.width), np.arange(src.height))
        xs, ys = rasterio.transform.xy(src.transform, rows, cols)
        lons, lats = np.array(xs), np.array(ys)

        if basemap is not None:
            ax = plot_basemap(
                ax,
                src.bounds.left,
                src.bounds.bottom,
                src.bounds.right,
                src.bounds.top,
                basemap,
                True,
            )

    with rioxarray.open_rasterio(filename) as src:
        lon, lat = transformer.transform(lons, lats)
        src.coords["lon"] = (("y", "x"), lon)
        src.coords["lat"] = (("y", "x"), lat)

        mappable = src.plot(
            ax=ax,
            x="lon",
            y="lat",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            norm=norm,
            add_colorbar=False,
        )

    return ax, mappable
