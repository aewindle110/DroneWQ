from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

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
    idx: int

    @classmethod
    def from_image(cls, src: Image, data: np.ndarray, method: str):
        """Creates another Image instance from another Image."""
        return cls(
            file_name=src.file_name,
            file_path=src.file_path,
            method=method,
            profile=src.profile,
            data=data,
            idx=src.idx,
        )


class Base_Compute_Method:
    """Base class for all computation methods."""

    def __init__(self, save_images: bool = False) -> None:
        self.save_images = save_images
        self.name = self.__class__.__name__

    def __call__(self, img: Image) -> Image:
        pass

    def preprocess(self) -> None:
        pass
