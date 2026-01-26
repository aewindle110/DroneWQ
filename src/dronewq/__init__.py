#!/usr/bin/env python
# __init__.py

from .core.georeference import compute_flight_lines, georeference
from .core.mosaic import downsample, mosaic
from .core.pipeline import RRS_Pipeline
from .core.plot_map import plot_basemap, plot_georeferenced_data
from .core.raw_to_rss import process_raw_to_rrs
from .core.wq_calc import (
    chl_gitelson,
    chl_hu,
    chl_hu_ocx,
    chl_ocx,
    save_wq_imgs,
    tsm_nechad,
)
from .ed_methods import *
from .lw_methods import *
from .masks import *
from .utils.images import load_imgs, load_metadata, process_micasense_images
from .utils.metadata import write_metadata_csv
from .utils.settings import settings

# Singleton definitions and aliasing
configure = settings.configure


__version__ = "1.0"
