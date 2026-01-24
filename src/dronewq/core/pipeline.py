import logging
from pathlib import Path
from typing import Callable

from dronewq.lw_methods.lw_common import Base_LW_Method
from dronewq.utils.images import process_micasense_images
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        main_dir: str,
        lw_method: Base_LW_Method,
        ed_method: Callable,
        pixel_masking_method: Callable | None = None,
        overwrite_lt_lw: bool = False,
        clean_intermediates: bool = True,
        generate_thumbnails: bool = True,
    ):
        if main_dir is None:
            msg = "Please set the main_dir path."
            raise ValueError(msg)
        self.lw_method = lw_method
        self.ed_method = ed_method
        self.pixel_masking_method = pixel_masking_method
        settings.overwrite_lt_lw = overwrite_lt_lw
        settings.clean_intermediates = clean_intermediates

        settings.configure(main_dir=main_dir)
        self.__make_dirs()

    def __make_dirs(self):
        "Create the directories if they don't already exist."
        lt_dir = settings.lt_dir
        lw_dir = settings.lw_dir
        rrs_dir = settings.rrs_dir
        masked_rrs_dir = settings.masked_rrs_dir
        # Make all these directories if they don't already exist
        all_dirs = [lt_dir, lw_dir, rrs_dir]
        for directory in all_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)

        if self.pixel_masking_method is not None:
            Path(masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def run(self):
        logger.info(
            "Processing a total of %d images.",
            len(Path(settings.raw_water_dir).glob("*.tif")),
        )

        process_micasense_images()
