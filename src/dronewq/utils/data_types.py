from __future__ import annotations

from pathlib import Path

import numpy as np


class Image:
    """Image Class used to transfer GEOTIFF images."""

    def __init__(
        self,
        file_name: str,
        file_path: str | Path,
        data: np.ndarray,
    ):
        self.file_name = file_name
        self.file_path = file_path
        self.data = data

    @classmethod
    def from_image(cls, source: Image, data: np.ndarray) -> Image:
        """Creates another Image instance from another Image"""
        return cls(file_name=source.file_name, data=data)
