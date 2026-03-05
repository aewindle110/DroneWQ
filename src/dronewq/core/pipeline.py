"""Main pipeline for dronewq."""

import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

from dronewq.lw_methods.blackpixel import Blackpixel
from dronewq.lw_methods.mobley_rho import Mobley_rho
from dronewq.masks.std_masking import StdMasking
from dronewq.utils.data_types import Base_Compute_Method
from dronewq.utils.images import (
    get_filepaths,
    process_micasense_images,
    read_file,
    save_img,
)
from dronewq.utils.settings import settings
from dronewq.utils.utils import validate_folder

logger = logging.getLogger(__name__)


class RRSPipeline:
    """Main pipeline for dronewq.

    Parameters
    ----------
    output_folder : Path | str
        Path to the output folder.
    lw_method : Base_Compute_Method
        Method used to calculate water leaving radiance.
        If uncertain, you can start with `Mobley_rho()`.
    ed_method : Base_Compute_Method
        Method used to calculate downwelling irradiance (Ed).
        If uncertain, you can start with `Dls_ed()`.
    pixel_masking_method : Base_Compute_Method | None, optional
        Method to mask pixels. Options are
        `ThresholdMasking`, `StdMasking`, or None. Default is None.
    overwrite_lt : bool, optional
        Whether to overwrite existing Lt images.
        Should have this set to True if you are running the pipeline for the
        first time. Defaults to False, which saves time if you are rerunning.
    generate_thumbnails : bool, optional
        Whether to generate thumbnails. Defaults to True.
    workers : int, optional
        Number of parallel image processing instances. Defaults to 1.
    """

    def __init__(
        self,
        output_folder: Path | str,
        lw_method: Base_Compute_Method,
        ed_method: Base_Compute_Method,
        pixel_masking_method: Base_Compute_Method | None = None,
        overwrite_lt: bool = False,  # noqa: FBT001, FBT002
        generate_thumbnails: bool = True,  # noqa: FBT001, FBT002
        workers: int = 1,
    ):
        """Initialize the pipeline."""

        if settings.main_dir is None:
            raise LookupError(
                "Please set the main_dir path in settings."
                "settings.configure(main_dir='path')"
            )

        self.main_dir = validate_folder(settings.main_dir)
        self.output_folder = (
            Path(output_folder) if isinstance(output_folder, str) else output_folder
        )
        self.lw_method = lw_method
        self.ed_method = ed_method
        self.pixel_masking_method = pixel_masking_method
        self.overwrite_lt = overwrite_lt
        self.generate_thumbnails = generate_thumbnails
        self.workers = workers

        self.__make_dirs()

    def __make_dirs(self) -> None:
        """Create the directories if they don't already exist."""
        # Make all these directories if they don't already exist
        settings.lt_dir.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)

        all_methods = [self.lw_method, self.ed_method]
        for method in all_methods:
            directory = self.output_folder.joinpath(method.name)
            Path(directory).mkdir(parents=True, exist_ok=True)

        if self.pixel_masking_method is not None:
            self.masked_rrs_dir = self.output_folder.joinpath(
                self.pixel_masking_method.name,
            )
            Path(self.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Run the pipeline."""
        logger.info(
            "Processing a total of %d images.",
            len(list(Path(settings.raw_water_dir).glob("*.tif"))),
        )
        if not settings.lt_dir.exists():
            logger.warning(
                f"{settings.lt_dir} does not exist. Setting the overwrite_lt flag to True."
            )
            self.overwrite_lt = True

        filepaths = get_filepaths(settings.lt_dir)
        if not filepaths:
            logger.warning(
                f"{settings.lt_dir} does not have any files. Setting the overwrite_lt flag to True."
            )
            self.overwrite_lt = True

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

        # The Lw methods need their respective additional preprocessing
        # Such as finding the median of the sky images or
        # mean minimum lt NIR value
        self.lw_method.preprocess()
        self.ed_method.preprocess()

        with ProcessPoolExecutor(max_workers=self.workers) as executor:
            results = executor.map(self.rrs_worker, filepaths)

            # Use tqdm to show progress of processed images
            for _ in tqdm(results, total=len(filepaths), desc="Processing images"):
                pass

            if self.pixel_masking_method is not None:
                print("Masking rrs images")
                rrs_dir = self.output_folder / self.ed_method.name
                filepaths = get_filepaths(rrs_dir)
                if isinstance(self.pixel_masking_method, StdMasking):
                    self.pixel_masking_method.preprocess_masking(rrs_dir)
                results = executor.map(self.mask_worker, filepaths)
                for _ in tqdm(results, total=len(filepaths), desc="Processing images"):
                    pass

        logger.info("Pipeline Finished.")

    def rrs_worker(self, filepath: Path) -> Path:
        """
        Process a single image.

        This function is what actually happens in the pipeline.
        """
        # TODO: Should have a try/except here
        # Maybe to catch saving errors, since
        # the processing methods have error handling
        lt_img = read_file(filepath)
        lw_img = self.lw_method(lt_img)
        if self.lw_method.save_images:
            save_img(lw_img, self.output_folder)
        rrs_img = self.ed_method(lw_img)
        save_img(rrs_img, self.output_folder)

        return filepath

    def mask_worker(self, filepath: Path) -> Path:
        rrs_img = read_file(filepath)
        masked_rrs_img = self.pixel_masking_method(rrs_img)
        save_img(masked_rrs_img, self.output_folder)
        return filepath
