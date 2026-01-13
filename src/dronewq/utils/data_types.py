from __future__ import annotations

from pathlib import Path

import numpy as np
from rasterio.profiles import Profile


class Image:
    """Image Class used to transfer GEOTIFF images."""

    def __init__(
        self,
        file_name: str,
        file_path: str | Path,
        profile: Profile,
        data: np.ndarray,
    ):
        self.file_name = file_name
        self.file_path = file_path
        self.profile = profile
        self.data = data

    @classmethod
    def from_image(cls, src: Image, data: np.ndarray) -> Image:
        """Creates another Image instance from another Image"""
        return cls(
            file_name=src.file_name,
            file_path=src.file_path,
            profile=src.profile,
            data=data,
        )
