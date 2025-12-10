import glob
import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import rasterio

from dronewq import settings
from dronewq.masks.threshold_masking import __compute

test_path = Path(__file__).absolute().parent
test_path = test_path.joinpath("test_set")

if not test_path.exists():
    msg = f"Could not find {test_path}"
    raise LookupError(msg)

settings.configure(main_dir=test_path)


class TestComputeFunction:
    """Test cases for the _compute worker function"""

    def test_compute_basic(self):
        """Test _compute function creates output file"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        assert len(rrs_files) > 0, "Need at least one Rrs file for testing"

        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        result = __compute(
            filepath=filepath,
            nir_threshold=0.01,
            green_threshold=0.005,
            masked_rrs_dir=output_dir,
        )

        assert result is True, "_compute should return True on success"

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        assert os.path.exists(output_file), "Output file should be created"

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_masks_correctly(self):
        """Test that _compute applies masking correctly"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        nir_threshold = 0.01
        green_threshold = 0.005

        with rasterio.open(filepath, "r") as src:
            original_data = src.read()

        __compute(
            filepath=filepath,
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            masked_rrs_dir=output_dir,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        with rasterio.open(output_file, "r") as src:
            masked_data = src.read()

        assert original_data.shape == masked_data.shape, "Shape should be preserved"

        nir_band = masked_data[4, :, :]
        valid_nir = nir_band[~np.isnan(nir_band)]
        if len(valid_nir) > 0:
            assert np.all(
                valid_nir <= nir_threshold
            ), "All valid NIR values should be <= threshold"

        green_band = masked_data[1, :, :]
        valid_green = green_band[~np.isnan(green_band)]
        if len(valid_green) > 0:
            assert np.all(
                valid_green >= green_threshold
            ), "All valid green values should be >= threshold"

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_consistent_nan_across_bands(self):
        """Test that _compute applies NaN consistently across all bands"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        __compute(
            filepath=filepath,
            nir_threshold=0.01,
            green_threshold=0.005,
            masked_rrs_dir=output_dir,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        with rasterio.open(output_file, "r") as src:
            masked_data = src.read()

        nan_mask_band0 = np.isnan(masked_data[0, :, :])

        for band_idx in range(1, masked_data.shape[0]):
            nan_mask_current = np.isnan(masked_data[band_idx, :, :])
            assert np.array_equal(
                nan_mask_band0, nan_mask_current
            ), f"NaN pattern should be consistent (band 0 vs band {band_idx})"

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_with_invalid_filepath(self):
        """Test _compute raises exception with invalid filepath"""
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with pytest.raises(Exception):
            __compute(
                filepath="/nonexistent/path/to/file.tif",
                nir_threshold=0.01,
                green_threshold=0.005,
                masked_rrs_dir=output_dir,
            )

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_preserves_profile(self):
        """Test that _compute preserves rasterio profile metadata"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with rasterio.open(filepath, "r") as src:
            original_profile = src.profile.copy()

        __compute(
            filepath=filepath,
            nir_threshold=0.01,
            green_threshold=0.005,
            masked_rrs_dir=output_dir,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        with rasterio.open(output_file, "r") as src:
            masked_profile = src.profile

        assert masked_profile["width"] == original_profile["width"]
        assert masked_profile["height"] == original_profile["height"]
        assert masked_profile["count"] == 5
        assert masked_profile["dtype"] == original_profile["dtype"]

        shutil.rmtree(output_dir, ignore_errors=True)


def test_threshold_masking_defaults():
    """Test threshold_masking function with default parameters"""
    from dronewq.masks.threshold_masking import threshold_masking

    output_dir = settings.masked_rrs_dir
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    threshold_masking()

    rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
    for filepath in rrs_files:
        output_file = os.path.join(output_dir, os.path.basename(filepath))
        assert os.path.exists(
            output_file
        ), f"Output file {output_file} should be created"

    shutil.rmtree(output_dir, ignore_errors=True)

