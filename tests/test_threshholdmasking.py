import os
import glob
import shutil
import tempfile
import concurrent.futures
from pathlib import Path

import numpy as np
import pytest
import rasterio

import dronewq
from dronewq import settings
from dronewq.masks import threshold_masking as dronewq_threshold_masking
from dronewq.masks.threshold_masking import _compute
from dronewq.utils.images import load_imgs as dronewq_load_imgs

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


class TestThresholdMasking:
    """Test cases for dronewq.threshold_masking function"""

    def setup_method(self):
        """Setup for each test method"""
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(settings.masked_rrs_dir):
            shutil.rmtree(settings.masked_rrs_dir, ignore_errors=True)

    def test_threshold_masking_creates_output_files(self):
        """Test that threshold_masking creates output files"""
        dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.005,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))

        assert len(masked_files) > 0, "Should create masked files"
        assert len(masked_files) == len(rrs_files), \
            "Should create same number of masked files as input Rrs files"

    def test_threshold_masking_default_values(self):
        """Test threshold masking with default NIR=0.01 and green=0.005 thresholds"""
        nir_threshold = 0.01
        green_threshold = 0.005

        dronewq_threshold_masking(
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"

        # Load and verify masked images using dronewq
        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        for data in masked_imgs:
            assert data.shape[0] == 5, "Should have 5 bands"

            # Check that NIR band (index 4) values above threshold are masked (NaN)
            nir_band = data[4, :, :]
            valid_nir = nir_band[~np.isnan(nir_band)]
            if len(valid_nir) > 0:
                assert np.all(valid_nir <= nir_threshold), \
                    "All valid NIR values should be <= threshold"

            # Check that green band (index 1) values below threshold are masked (NaN)
            green_band = data[1, :, :]
            valid_green = green_band[~np.isnan(green_band)]
            if len(valid_green) > 0:
                assert np.all(valid_green >= green_threshold), \
                    "All valid green values should be >= threshold"

    def test_threshold_masking_strict_nir(self):
        """Test threshold masking with strict NIR threshold"""
        nir_threshold = 0.005  # Stricter threshold
        green_threshold = 0.005

        dronewq_threshold_masking(
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"

        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        for data in masked_imgs:
            nir_band = data[4, :, :]
            valid_nir = nir_band[~np.isnan(nir_band)]
            if len(valid_nir) > 0:
                assert np.all(valid_nir <= nir_threshold), \
                    "All valid NIR values should be <= strict threshold"

    def test_threshold_masking_strict_green(self):
        """Test threshold masking with strict green threshold"""
        nir_threshold = 0.01
        green_threshold = 0.01  # Stricter threshold

        dronewq_threshold_masking(
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            num_workers=1,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"

        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        for data in masked_imgs:
            green_band = data[1, :, :]
            valid_green = green_band[~np.isnan(green_band)]
            if len(valid_green) > 0:
                assert np.all(valid_green >= green_threshold), \
                    "All valid green values should be >= strict threshold"

    def test_threshold_masking_preserves_shape(self):
        """Test that threshold masking preserves image shape"""
        dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.005,
            num_workers=1,
        )

        original_imgs = list(dronewq_load_imgs(settings.rrs_dir))
        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))

        for orig_data, masked_data in zip(original_imgs, masked_imgs):
            assert orig_data.shape == masked_data.shape, \
                "Masked image should have same shape as original"

    def test_threshold_masking_consistent_nan_across_bands(self):
        """Test that NaN masking is consistent across all bands"""
        dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.005,
            num_workers=1,
        )

        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        for data in masked_imgs:
            # Get NaN mask from first band
            nan_mask_band0 = np.isnan(data[0, :, :])

            # Check all bands have same NaN pattern
            for band_idx in range(1, data.shape[0]):
                nan_mask_current = np.isnan(data[band_idx, :, :])
                assert np.array_equal(nan_mask_band0, nan_mask_current), \
                    f"NaN pattern should be consistent across all bands (band 0 vs band {band_idx})"

    def test_threshold_masking_masks_high_nir_values(self):
        """Test that high NIR values are masked"""
        nir_threshold = 0.01

        dronewq_threshold_masking(
            nir_threshold=nir_threshold,
            green_threshold=0.005,
            num_workers=1,
        )

        original_imgs = list(dronewq_load_imgs(settings.rrs_dir))
        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))

        for orig_data, masked_data in zip(original_imgs, masked_imgs):
            orig_nir = orig_data[4, :, :]  # NIR band
            masked_nir = masked_data[4, :, :]  # NIR band

            # Check pixels that were above threshold in original are now NaN
            high_nir_mask = orig_nir > nir_threshold
            if np.any(high_nir_mask):
                assert np.all(np.isnan(masked_nir[high_nir_mask])), \
                    "Pixels with NIR > threshold should be masked (NaN)"

    def test_threshold_masking_masks_low_green_values(self):
        """Test that low green values are masked"""
        green_threshold = 0.005

        dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=green_threshold,
            num_workers=1,
        )

        original_imgs = list(dronewq_load_imgs(settings.rrs_dir))
        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))

        for orig_data, masked_data in zip(original_imgs, masked_imgs):
            orig_green = orig_data[1, :, :]  # Green band
            masked_green = masked_data[1, :, :]  # Green band

            # Check pixels that were below threshold in original are now NaN
            low_green_mask = orig_green < green_threshold
            if np.any(low_green_mask):
                assert np.all(np.isnan(masked_green[low_green_mask])), \
                    "Pixels with green < threshold should be masked (NaN)"

    def test_threshold_masking_returns_results(self):
        """Test that threshold_masking returns results list"""
        results = dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.005,
            num_workers=1,
        )

        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))

        assert results is not None, "Should return results"
        assert len(results) == len(rrs_files), \
            "Results length should match number of input files"

    def test_threshold_masking_stricter_nir_masks_more(self):
        """Test that stricter NIR threshold masks more pixels"""
        # First run with lenient threshold
        dronewq_threshold_masking(
            nir_threshold=0.02,  # Lenient
            green_threshold=0.005,
            num_workers=1,
        )

        lenient_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        lenient_nan_counts = [np.sum(np.isnan(data)) for data in lenient_imgs]

        # Clean up and run with stricter threshold
        shutil.rmtree(settings.masked_rrs_dir)
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

        dronewq_threshold_masking(
            nir_threshold=0.005,  # Stricter
            green_threshold=0.005,
            num_workers=1,
        )

        strict_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        strict_nan_counts = [np.sum(np.isnan(data)) for data in strict_imgs]

        # Stricter threshold should mask more or equal pixels
        total_lenient = sum(lenient_nan_counts)
        total_strict = sum(strict_nan_counts)

        assert total_strict >= total_lenient, \
            f"Stricter NIR threshold should mask more pixels: strict={total_strict}, lenient={total_lenient}"

    def test_threshold_masking_stricter_green_masks_more(self):
        """Test that stricter green threshold masks more pixels"""
        # First run with lenient threshold
        dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.001,  # Lenient
            num_workers=1,
        )

        lenient_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        lenient_nan_counts = [np.sum(np.isnan(data)) for data in lenient_imgs]

        # Clean up and run with stricter threshold
        shutil.rmtree(settings.masked_rrs_dir)
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

        dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.01,  # Stricter
            num_workers=1,
        )

        strict_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        strict_nan_counts = [np.sum(np.isnan(data)) for data in strict_imgs]

        # Stricter threshold should mask more or equal pixels
        total_lenient = sum(lenient_nan_counts)
        total_strict = sum(strict_nan_counts)

        assert total_strict >= total_lenient, \
            f"Stricter green threshold should mask more pixels: strict={total_strict}, lenient={total_lenient}"

    def test_threshold_masking_combined_mask(self):
        """Test that masking combines both NIR and green conditions with OR logic"""
        nir_threshold = 0.01
        green_threshold = 0.005

        dronewq_threshold_masking(
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            num_workers=1,
        )

        original_imgs = list(dronewq_load_imgs(settings.rrs_dir))
        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))

        for orig_data, masked_data in zip(original_imgs, masked_imgs):
            # Calculate expected mask (OR logic)
            nir_mask = orig_data[4, :, :] > nir_threshold
            green_mask = orig_data[1, :, :] < green_threshold
            expected_mask = nir_mask | green_mask

            # Verify masked pixels match expected
            actual_mask = np.isnan(masked_data[0, :, :])

            # All expected masked pixels should be NaN
            assert np.all(actual_mask[expected_mask]), \
                "All pixels violating either threshold should be masked"

    def test_threshold_masking_with_executor(self):
        """Test threshold_masking with external executor"""
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            results = dronewq_threshold_masking(
                nir_threshold=0.01,
                green_threshold=0.005,
                num_workers=1,
                executor=executor,
            )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        assert len(masked_files) > 0, "Should create masked files"
        assert results is not None, "Should return results"


class TestComputeFunction:
    """Test cases for the _compute worker function directly"""

    def setup_method(self):
        """Setup for each test method"""
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(settings.masked_rrs_dir):
            shutil.rmtree(settings.masked_rrs_dir, ignore_errors=True)

    def test_compute_basic(self):
        """Test _compute function directly with basic parameters"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        assert len(rrs_files) > 0, "Need at least one Rrs file for testing"

        filepath = rrs_files[0]
        nir_threshold = 0.01
        green_threshold = 0.005

        result = _compute(
            filepath=filepath,
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            masked_rrs_dir=settings.masked_rrs_dir,
        )

        assert result is True, "_compute should return True on success"

        # Verify output file was created
        output_file = os.path.join(settings.masked_rrs_dir, os.path.basename(filepath))
        assert os.path.exists(output_file), "Output file should be created"

    def test_compute_masks_correctly(self):
        """Test that _compute applies masking correctly"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        nir_threshold = 0.01
        green_threshold = 0.005

        # Read original data
        with rasterio.open(filepath, "r") as src:
            original_data = src.read()

        _compute(
            filepath=filepath,
            nir_threshold=nir_threshold,
            green_threshold=green_threshold,
            masked_rrs_dir=settings.masked_rrs_dir,
        )

        # Read masked data
        output_file = os.path.join(settings.masked_rrs_dir, os.path.basename(filepath))
        with rasterio.open(output_file, "r") as src:
            masked_data = src.read()

        # Verify shape preserved
        assert original_data.shape == masked_data.shape, "Shape should be preserved"

        # Verify NIR masking
        nir_band = masked_data[4, :, :]
        valid_nir = nir_band[~np.isnan(nir_band)]
        if len(valid_nir) > 0:
            assert np.all(valid_nir <= nir_threshold), \
                "All valid NIR values should be <= threshold"

        # Verify green masking
        green_band = masked_data[1, :, :]
        valid_green = green_band[~np.isnan(green_band)]
        if len(valid_green) > 0:
            assert np.all(valid_green >= green_threshold), \
                "All valid green values should be >= threshold"

    def test_compute_consistent_nan_across_bands(self):
        """Test that _compute applies NaN consistently across all bands"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]

        _compute(
            filepath=filepath,
            nir_threshold=0.01,
            green_threshold=0.005,
            masked_rrs_dir=settings.masked_rrs_dir,
        )

        output_file = os.path.join(settings.masked_rrs_dir, os.path.basename(filepath))
        with rasterio.open(output_file, "r") as src:
            masked_data = src.read()

        # Get NaN mask from first band
        nan_mask_band0 = np.isnan(masked_data[0, :, :])

        # Check all bands have same NaN pattern
        for band_idx in range(1, masked_data.shape[0]):
            nan_mask_current = np.isnan(masked_data[band_idx, :, :])
            assert np.array_equal(nan_mask_band0, nan_mask_current), \
                f"NaN pattern should be consistent (band 0 vs band {band_idx})"

    def test_compute_with_invalid_filepath(self):
        """Test _compute raises exception with invalid filepath"""
        with pytest.raises(Exception):
            _compute(
                filepath="/nonexistent/path/to/file.tif",
                nir_threshold=0.01,
                green_threshold=0.005,
                masked_rrs_dir=settings.masked_rrs_dir,
            )

    def test_compute_preserves_profile(self):
        """Test that _compute preserves rasterio profile metadata"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]

        # Read original profile
        with rasterio.open(filepath, "r") as src:
            original_profile = src.profile.copy()

        _compute(
            filepath=filepath,
            nir_threshold=0.01,
            green_threshold=0.005,
            masked_rrs_dir=settings.masked_rrs_dir,
        )

        # Read masked profile
        output_file = os.path.join(settings.masked_rrs_dir, os.path.basename(filepath))
        with rasterio.open(output_file, "r") as src:
            masked_profile = src.profile

        # Check key profile attributes are preserved
        assert masked_profile["width"] == original_profile["width"]
        assert masked_profile["height"] == original_profile["height"]
        assert masked_profile["count"] == 5
        assert masked_profile["dtype"] == original_profile["dtype"]


class TestThresholdMaskingEdgeCases:
    """Test edge cases for threshold_masking"""

    def setup_method(self):
        """Setup for each test method"""
        Path(settings.masked_rrs_dir).mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(settings.masked_rrs_dir):
            shutil.rmtree(settings.masked_rrs_dir, ignore_errors=True)

    def test_threshold_masking_no_settings(self):
        """Test threshold_masking raises LookupError when main_dir is None"""
        from dronewq.utils.settings import Settings
        
        # Create a fresh settings instance without configuration
        unconfigured_settings = Settings()
        
        # Patch the settings module to use unconfigured settings
        import dronewq.masks.threshold_masking as threshold_module
        original_settings = threshold_module.settings
        
        try:
            threshold_module.settings = unconfigured_settings

            with pytest.raises(LookupError, match="Please set the main_dir path"):
                dronewq_threshold_masking(
                    nir_threshold=0.01,
                    green_threshold=0.005,
                    num_workers=1,
                )
        finally:
            # Restore original settings
            threshold_module.settings = original_settings

    def test_threshold_masking_extreme_thresholds_high(self):
        """Test with very high thresholds (should mask nothing)"""
        dronewq_threshold_masking(
            nir_threshold=1.0,  # Very high
            green_threshold=0.0,  # Very low
            num_workers=1,
        )

        original_imgs = list(dronewq_load_imgs(settings.rrs_dir))
        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))

        for orig_data, masked_data in zip(original_imgs, masked_imgs):
            orig_nan_count = np.sum(np.isnan(orig_data))
            masked_nan_count = np.sum(np.isnan(masked_data))
            assert masked_nan_count == orig_nan_count, \
                "With extreme thresholds, no additional masking should occur"

    def test_threshold_masking_extreme_thresholds_low(self):
        """Test with very low NIR threshold (should mask most NIR)"""
        dronewq_threshold_masking(
            nir_threshold=0.0,  # Zero threshold
            green_threshold=0.005,
            num_workers=1,
        )

        masked_imgs = list(dronewq_load_imgs(settings.masked_rrs_dir))
        for data in masked_imgs:
            nir_band = data[4, :, :]
            valid_nir = nir_band[~np.isnan(nir_band)]
            if len(valid_nir) > 0:
                assert np.all(valid_nir <= 0.0), \
                    "All valid NIR should be <= 0 with zero threshold"

    def test_threshold_masking_multiple_workers(self):
        """Test with multiple workers"""
        results = dronewq_threshold_masking(
            nir_threshold=0.01,
            green_threshold=0.005,
            num_workers=4,
        )

        masked_files = glob.glob(os.path.join(settings.masked_rrs_dir, "*.tif"))
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))

        assert len(masked_files) == len(rrs_files)
        assert len(results) == len(rrs_files)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])