#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __init__.py

from .utils.settings import settings
from .utils.metadata import write_metadata_csv
from .utils.images import (
    load_imgs,
    load_metadata,
    process_micasense_images,
    downsample,
)
from .lw_methods import *
from .ed_methods import *
from .masks import *
from .core.raw_to_rss import process_raw_to_rrs
from .core.wq_calc import (
    save_wq_imgs,
    chl_hu,
    chl_ocx,
    chl_hu_ocx,
    chl_gitelson,
    tsm_nechad,
)
from .core.georeference import compute_flight_lines, georeference
from .core.plot_map import plot_basemap, plot_georeferenced_data
from .core.mosaic import (
    mosaic,
)

# Singleton definitions and aliasing
configure = settings.configure


__version__ = "1.0"
