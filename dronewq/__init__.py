from dronewq.utils.settings import settings
from dronewq.utils.metadata import write_metadata_csv
from dronewq.utils.images import retrieve_imgs_and_metadata
import dronewq.lw_methods
import dronewq.lecacy

# Singleton definitions and aliasing
configure = settings.configure
