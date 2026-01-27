"""Main pipeline for dronewq."""

import logging
from pathlib import Path
from queue import Queue
from threading import Thread

from dronewq.lw_methods.blackpixel import Blackpixel
from dronewq.lw_methods.mobley_rho import Mobley_rho
from dronewq.utils.data_types import Base_Compute_Method
from dronewq.utils.images import process_micasense_images, reader_worker, save_worker
from dronewq.utils.settings import settings

logger = logging.getLogger(__name__)


class RRS_Pipeline:
    def __init__(
        self,
        main_dir: str,
        lw_method: Base_Compute_Method,
        ed_method: Base_Compute_Method,
        pixel_masking_method: Base_Compute_Method | None = None,
        overwrite_lt: bool = False,  # noqa: FBT001, FBT002
        generate_thumbnails: bool = True,  # noqa: FBT001, FBT002
    ):
        if not Path(main_dir).exists():
            msg = f"The main directory {main_dir} does not exist."
            raise LookupError(msg)

        self.lw_method = lw_method
        self.ed_method = ed_method
        self.pixel_masking_method = pixel_masking_method
        self.overwrite_lt = overwrite_lt
        self.generate_thumbnails = generate_thumbnails

        self.main_dir = Path(main_dir)

        self.__make_dirs()

    def __make_dirs(self) -> None:
        """Create the directories if they don't already exist."""
        self.lt_dir = settings.lt_dir
        self.lw_dir = self.main_dir.joinpath(self.lw_method.name)
        self.rrs_dir = self.main_dir.joinpath(self.ed_method.name)
        # Make all these directories if they don't already exist
        all_dirs = [self.lt_dir, self.lw_dir, self.rrs_dir]
        for directory in all_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)

        if self.pixel_masking_method is not None:
            self.masked_rrs_dir = self.main_dir.joinpath(
                self.pixel_masking_method.name,
            )
            Path(self.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Run the pipeline."""
        logger.info(
            "Processing a total of %d images.",
            len(list(Path(settings.raw_water_dir).glob("*.tif"))),
        )

        if self.overwrite_lt:
            logger.info("Overwriting existing Lt images.")
            process_micasense_images(
                sky=False,
                generateThumbnails=self.generate_thumbnails,
            )
            if isinstance(self.lw_method, (Mobley_rho, Blackpixel)):
                process_micasense_images(
                    sky=True,
                    generateThumbnails=self.generate_thumbnails,
                )
        # Buffer used to transfer read lt imgs to the pipeline
        reader_buffer = Queue(maxsize=10)
        # Buffer used to save final outputs of the pipeline
        saver_buffer = Queue(maxsize=10)
        # Thread used to read from lt_dir
        reader_thread = Thread(
            target=reader_worker,
            args=(settings.lt_dir, reader_buffer),
        )
        saver_thread = Thread(
            target=save_worker,
            args=(saver_buffer,),
        )

        # Start the reader thread
        reader_thread.start()
        saver_thread.start()

        while True:
            lt_img = reader_buffer.get()
            if lt_img is None:
                logger.info("Buffer Empty. Exiting.")
                break
            lw_img = self.lw_method(lt_img)
            rrs_img = self.ed_method(lw_img)
            if self.pixel_masking_method is not None:
                rrs_img = self.pixel_masking_method(rrs_img)
            saver_buffer.put(rrs_img)
        saver_buffer.put(None)

        # Wait for the saver thread to finish
        saver_thread.join()
        reader_thread.join()

        logger.info("Pipeline Finished.")
