from dronewq.utils.settings import settings
from dronewq.utils.metadata import write_metadata_csv
from dronewq.utils.images import retrieve_imgs_and_metadata
from dronewq.lw_methods import *
import dronewq.lecacy

# Singleton definitions and aliasing
configure = settings.configure
