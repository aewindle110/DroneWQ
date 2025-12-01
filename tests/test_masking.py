import sys
import os

# Needs access to dronewq module
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import dronewq
import numpy as np
import glob
import shutil
from pathlib import Path
from dronewq import settings
from dronewq.masks import std_masking as dronewq_std_masking

test_path = Path(__file__).absolute().parent
test_path = test_path.joinpath("test_set")
if not test_path.exists():
    msg = f"Could not find {test_path}"
    raise LookupError(msg)

settings.configure(main_dir=test_path)


def setup_module():
    """Setup: Process raw images to Rrs before running masking tests"""
    dronewq.write_metadata_csv(settings.raw_water_dir, settings.main_dir)
    dronewq.process_raw_to_rrs(
        settings.main_dir,
        num_workers=1,
        clean_intermediates=False,
        pixel_masking_method=None,  # Don't mask during initial processing
    )


def teardown_module():
    """Cleanup: Remove masked directories after tests"""
    if os.path.exists(settings.masked_rrs_dir):
        shutil.rmtree(settings.masked_rrs_dir, ignore_errors=True)


class TestStdMasking:
    """Test cases for dronewq.std_masking function"""

    def setup_method(self):
        """Setup for each test method"""
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(settings.masked_rrs_dir):
            shutil.rmtree(settings.masked_rrs_dir, ignore_errors=True)

    def test_std_masking_creates_output_files(self):
        """Test that std_masking creates output files"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))

        assert len(masked_files) > 0, "Should create masked files"
        assert len(masked_files) == len(rrs_files), \
            "Should create same number of masked files as input Rrs files"

    def test_std_masking_default_factor(self):
        """Test std masking with default mask_std_factor=1"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"

        # Load and verify masked images have valid structure
        import rasterio
        for masked_file in masked_files:
            with rasterio.open(masked_file, "r") as src:
                data = src.read()
                assert data.shape[0] == 5, "Should have 5 bands"
                # At least some valid (non-NaN) pixels should remain
                assert not np.all(np.isnan(data)), \
                    "Should have some valid pixels remaining"

    def test_std_masking_factor_2(self):
        """Test std masking with mask_std_factor=2 (more lenient)"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=2,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"

        import rasterio
        for masked_file in masked_files:
            with rasterio.open(masked_file, "r") as src:
                data = src.read()
                nan_ratio = np.sum(np.isnan(data)) / data.size
                assert nan_ratio < 1.0, "Should not mask all pixels"

    def test_std_masking_factor_3(self):
        """Test std masking with mask_std_factor=3 (very lenient)"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=3,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"

        import rasterio
        for masked_file in masked_files:
            with rasterio.open(masked_file, "r") as src:
                data = src.read()
                nan_ratio = np.sum(np.isnan(data)) / data.size
                assert nan_ratio < 1.0, "Should not mask all pixels"

    def test_std_masking_preserves_shape(self):
        """Test that std masking preserves image shape"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        original_files = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
        masked_files = sorted(glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif")))

        import rasterio
        for orig_file, masked_file in zip(original_files, masked_files):
            with rasterio.open(orig_file, "r") as orig_src:
                orig_data = orig_src.read()
            with rasterio.open(masked_file, "r") as masked_src:
                masked_data = masked_src.read()

            assert orig_data.shape == masked_data.shape, \
                "Masked image should have same shape as original"

    def test_std_masking_consistent_nan_across_bands(self):
        """Test that NaN masking is consistent across all bands"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))

        import rasterio
        for masked_file in masked_files:
            with rasterio.open(masked_file, "r") as src:
                data = src.read()

                # Get NaN mask from first band
                nan_mask_band0 = np.isnan(data[0, :, :])

                # Check all bands have same NaN pattern
                for band_idx in range(1, data.shape[0]):
                    nan_mask_current = np.isnan(data[band_idx, :, :])
                    assert np.array_equal(nan_mask_band0, nan_mask_current), \
                        f"NaN pattern should be consistent across all bands (band 0 vs band {band_idx})"

    def test_std_masking_masks_high_nir_values(self):
        """Test that high NIR values are masked"""
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        # Load original and masked to compare
        original_files = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
        masked_files = sorted(glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif")))

        import rasterio
        for orig_file, masked_file in zip(original_files, masked_files):
            with rasterio.open(orig_file, "r") as orig_src:
                orig_nir = orig_src.read(5)  # NIR band
            with rasterio.open(masked_file, "r") as masked_src:
                masked_nir = masked_src.read(5)  # NIR band

            # Masked image should have >= NaN values than original
            orig_nan_count = np.sum(np.isnan(orig_nir))
            masked_nan_count = np.sum(np.isnan(masked_nir))

            assert masked_nan_count >= orig_nan_count, \
                "Masked image should have >= NaN values than original"

    def test_std_masking_different_num_images(self):
        """Test std masking with different num_images parameter"""
        for num_images in [5, 10]:
            # Clean up before each iteration
            if os.path.exists(settings.masked_rrs_dir):
                shutil.rmtree(settings.masked_rrs_dir)
            Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

            dronewq_std_masking(
                num_images=num_images,
                mask_std_factor=1,
                num_workers=1,
            )

            masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
            assert len(masked_files) > 0, \
                f"Should create masked files with num_images={num_images}"

    def test_std_masking_returns_results(self):
        """Test that std_masking returns results list"""
        results = dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))

        assert results is not None, "Should return results"
        assert len(results) == len(rrs_files), \
            "Results length should match number of input files"

    def test_std_masking_stricter_factor_masks_more(self):
        """Test that stricter factor (lower value) masks more pixels"""
        # First run with factor=2 (lenient)
        dronewq_std_masking(
            num_images=10,
            mask_std_factor=2,
            num_workers=1,
        )

        masked_files_lenient = sorted(glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif")))

        import rasterio
        lenient_nan_counts = []
        for masked_file in masked_files_lenient:
            with rasterio.open(masked_file, "r") as src:
                data = src.read()
                lenient_nan_counts.append(np.sum(np.isnan(data)))

        # Clean up and run with factor=1 (stricter)
        shutil.rmtree(settings.masked_rrs_dir)
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

        dronewq_std_masking(
            num_images=10,
            mask_std_factor=1,
            num_workers=1,
        )

        masked_files_strict = sorted(glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif")))

        strict_nan_counts = []
        for masked_file in masked_files_strict:
            with rasterio.open(masked_file, "r") as src:
                data = src.read()
                strict_nan_counts.append(np.sum(np.isnan(data)))

        # Stricter factor should mask more or equal pixels
        total_lenient = sum(lenient_nan_counts)
        total_strict = sum(strict_nan_counts)

        assert total_strict >= total_lenient, \
            f"Stricter factor should mask more pixels: strict={total_strict}, lenient={total_lenient}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])