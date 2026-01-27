from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Queue

import numpy as np
from rasterio.profiles import Profile

from dronewq.utils.settings import settings


@dataclass
class Image:
    """Image Class used to transfer GEOTIFF images."""

    file_name: str
    file_path: str | Path
    method: str
    profile: Profile
    data: np.ndarray

    @classmethod
    def from_image(cls, src: Image, data: np.ndarray, method: str = ""):
        """Creates another Image instance from another Image."""
        return cls(
            file_name=src.file_name,
            file_path=src.file_path,
            method=method,
            profile=src.profile,
            data=data,
        )


class Base_Compute_Method:
    """Base class for all computation methods."""

    def __init__(self, save_images: bool = False):
        if settings.main_dir is None:
            raise ValueError("Please set the main_dir path.")
        self.save_images = save_images
        self.name = self.__class__.__name__

    def __call__(self, lt_img: Image) -> Image:
        pass

    def send_to_save(self, lw_img: Image, queue: Queue):
        queue.put(lw_img, block=True, timeout=None)
