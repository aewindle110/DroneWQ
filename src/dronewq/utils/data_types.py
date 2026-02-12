from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dronewq.utils.settings import settings

if TYPE_CHECKING:
    from pathlib import Path
    from queue import Queue

    import numpy as np
    from rasterio.profiles import Profile


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

    def __init__(self, save_images: bool = False) -> None:
        if settings.main_dir is None:
            msg = "Please set the main_dir path."
            raise ValueError(msg)
        self.save_images = save_images
        self.name = self.__class__.__name__

    def __call__(self, img: Image) -> Image:
        pass

    def __preprocess(self):
        pass
