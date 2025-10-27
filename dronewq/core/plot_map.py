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
    Loads a single-band GeoTIFF, projects it to pseudo-Mercator (EPSG:3857),
    and plots it over the given matplotlib Axes.

    Args:
        ax (plt.Axes): Matplotlib axes to plot on.
        filename (str): Path to GeoTIFF file.
        vmin (float): Minimum colormap value.
        vmax (float): Maximum colormap value.
        cmap (str): Matplotlib colormap name.
        norm (optional): Colormap normalization (e.g. LogNorm). Default None.
        basemap (optional): Contextily basemap provider or path. Default None.

    Returns:
        Tuple[plt.Axes, AxesImage]: The plot axes and the raster mappable.
    """

    latlon_projection = "EPSG:4326"
    pseudo_mercator_projection = "EPSG:3857"
    transformer = Transformer.from_crs(latlon_projection, pseudo_mercator_projection, always_xy=True)

    # --- Open raster to get geometry and basemap ---
    with rasterio.open(filename) as src_rio:
        # Build pixel coordinate grid
        cols, rows = np.meshgrid(np.arange(src_rio.width), np.arange(src_rio.height))
        xs, ys = rasterio.transform.xy(src_rio.transform, rows, cols)
        xs, ys = np.array(xs), np.array(ys)

        # Convert to pseudo-Mercator
        lon, lat = transformer.transform(xs, ys)

        # Add basemap if requested
        if basemap is not None:
            ax = plot_basemap(
                ax,
                src_rio.bounds.left,
                src_rio.bounds.bottom,
                src_rio.bounds.right,
                src_rio.bounds.top,
                basemap,
                True,
            )

    # --- Open again via rioxarray for plotting ---
    with rioxarray.open_rasterio(filename) as src:
        # Remove band dimension if it's a single-band raster
        src = src.squeeze()

        # Ensure lon/lat have same shape as raster
        lon = np.array(lon).reshape(src.shape)
        lat = np.array(lat).reshape(src.shape)

        # Assign coordinates
        src = src.assign_coords({"lon": (("y", "x"), lon), "lat": (("y", "x"), lat)})

        # Plot the data
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

