import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

from dronewq.lw_methods.blackpixel import Blackpixel
from dronewq.lw_methods.mobley_rho import Mobley_rho
from dronewq.masks.std_masking import StdMasking
from dronewq.masks.threshold_masking import ThresholdMasking
from dronewq.utils.data_types import Base_Compute_Method
from dronewq.utils.images import process_micasense_images, read_file, save_img
from dronewq.utils.metadata import write_metadata_csv
from dronewq.utils.settings import settings
from dronewq.utils.utils import get_filepaths, validate_folder

logger = logging.getLogger(__name__)

ctx = mp.get_context("spawn")


class RrsPipeline:
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
    masking_method : Base_Compute_Method | None, optional
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
        lw_method: Base_Compute_Method,
        ed_method: Base_Compute_Method,
        masking_method: Base_Compute_Method | None = None,
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
        if settings.output_dir is None:
            raise LookupError(
                "Please set the output_dir path in settings."
                "settings.configure(output_dir='path')"
            )

        self.main_dir = validate_folder(settings.main_dir)
        self.lw_method = lw_method
        self.ed_method = ed_method
        self.masking_method = masking_method
        self.overwrite_lt = overwrite_lt
        self.generate_thumbnails = generate_thumbnails
        self.workers = workers

        self.__make_dirs()

    def __make_dirs(self) -> None:
        """Create the directories if they don't already exist."""
        # Make all these directories if they don't already exist
        all_dirs = {
            "lt_dir": settings.lt_dir,
            "output_dir": settings.output_dir,
            "lw_dir": settings.lw_dir,
            "rrs_dir": settings.rrs_dir,
        }
        for dir in all_dirs.keys():
            self.__setattr__(dir, all_dirs[dir])
            all_dirs[dir].mkdir(parents=True, exist_ok=True)

        if self.masking_method is not None:
            self.masked_rrs_dir = Path(settings.masked_rrs_dir)
            self.masked_rrs_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Run the pipeline."""
        logger.info(
            "Processing a total of %d images.",
            len(list(Path(settings.raw_water_dir).glob("*.tif"))),
        )
        if not settings.lt_dir.exists():
            print(
                f"{settings.lt_dir} does not exist. Setting the overwrite_lt flag to True."
            )
            self.overwrite_lt = True

        filepaths = get_filepaths(settings.lt_dir)
        if not filepaths:
            print(
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

        filepaths = get_filepaths(settings.lt_dir)
        fullCsvPath = write_metadata_csv(settings.raw_water_dir, settings.main_dir)
        logger.info("Finished saving image metadata at: %s", fullCsvPath)

        # The Lw methods need their respective additional preprocessing
        # Such as finding the median of the sky images or
        # mean minimum lt NIR value
        self.lw_method.preprocess()
        self.ed_method.preprocess()

        with ProcessPoolExecutor(max_workers=self.workers, mp_context=ctx) as executor:
            results = executor.map(self.rrs_worker, filepaths)

            # Use tqdm to show progress of processed images
            for _ in tqdm(results, total=len(filepaths), desc="Processing images"):
                pass

            if isinstance(self.masking_method, StdMasking):
                print("STD Masking Rrs images")
                filepaths = get_filepaths(settings.rrs_dir)
                self.masking_method.preprocess_masking(settings.rrs_dir)
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
            save_img(lw_img, self.lw_dir)
        rrs_img = self.ed_method(lw_img)
        save_img(rrs_img, self.rrs_dir)

        if isinstance(self.masking_method, ThresholdMasking):
            rrs_img = self.masking_method(rrs_img)
            save_img(rrs_img, self.masked_rrs_dir)

        return filepath

    def mask_worker(self, filepath: Path) -> Path:
        rrs_img = read_file(filepath)
        masked_rrs_img = self.masking_method(rrs_img)
        save_img(masked_rrs_img, self.masked_rrs_dir)
        return filepath
