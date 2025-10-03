from dronewq.utils.settings import settings
from dronewq.utils.metadata import write_metadata_csv
from dronewq.utils.images import retrieve_imgs_and_metadata
from dronewq.lw_methods import *
from dronewq.masks import *
import dronewq.legacy

# Singleton definitions and aliasing
configure = settings.configure
