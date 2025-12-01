# tests/test_std_masking.py
import os
import glob
import shutil
from pathlib import Path

import numpy as np
import pytest
import rasterio

from dronewq import settings
from dronewq.masks.std_masking import _compute, std_masking


# ----------------------------------------------------------------------
# Test data setup
# ----------------------------------------------------------------------
test_path = Path(__file__).absolute().parent
test_path = test_path.joinpath("test_set")

if not test_path.exists():
    msg = f"Could not find {test_path}"
    raise LookupError(msg)

# Configure settings to point to the small test dataset
settings.configure(main_dir=test_path)


# ----------------------------------------------------------------------
# Tests for the private _compute function (new signature)
# ----------------------------------------------------------------------
class TestComputeFunctionNew:
    """Test cases for the updated _compute worker (dynamic NIR threshold)"""

    def test_compute_creates_output_file(self):
        """Test _compute creates the masked output file"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        assert len(rrs_files) > 0, "Need at least one Rrs file for testing"

        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Dummy statistics – just need something realistic
        _compute(
            filepath=filepath,
            masked_rrs_dir=output_dir,
            rrs_nir_mean=0.005,
            rrs_nir_std=0.002,
            mask_std_factor=1.0,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        assert os.path.exists(output_file), "Output masked file should be created"

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_masks_nir_above_threshold(self):
        """Test that pixels with NIR > mean + std*factor become NaN"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        mean_nir = 0.005
        std_nir = 0.001
        factor = 2.0
        threshold = mean_nir + std_nir * factor

        _compute(
            filepath=filepath,
            masked_rrs_dir=output_dir,
            rrs_nir_mean=mean_nir,
            rrs_nir_std=std_nir,
            mask_std_factor=factor,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        with rasterio.open(output_file) as src:
            nir_band = src.read(5)  # NIR is band 5 (1-based)

            valid_nir = nir_band[~np.isnan(nir_band)]
            if valid_nir.size > 0:
                assert np.all(valid_nir <= threshold + 1e-6), (
                    "All remaining NIR values must be <= calculated threshold"
                )

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_nan_consistency_across_bands(self):
        """Test that NaN mask from NIR is applied identically to all bands"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        _compute(
            filepath=filepath,
            masked_rrs_dir=output_dir,
            rrs_nir_mean=0.005,
            rrs_nir_std=0.002,
            mask_std_factor=1.0,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        with rasterio.open(output_file) as src:
            data = src.read()  # shape: (bands, h, w)

            # Use first band as reference NaN mask
            ref_nan = np.isnan(data[0])

            for b in range(1, data.shape[0]):
                assert np.array_equal(ref_nan, np.isnan(data[b])), (
                    f"NaN pattern mismatch between band 0 and band {b}"
                )

        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_preserves_profile_except_band_count(self):
        """Test that output profile is preserved (band count changes to 5)"""
        rrs_files = glob.glob(os.path.join(settings.rrs_dir, "*.tif"))
        filepath = rrs_files[0]
        output_dir = settings.masked_rrs_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with rasterio.open(filepath) as src:
            original_profile = src.profile.copy()

        _compute(
            filepath=filepath,
            masked_rrs_dir=output_dir,
            rrs_nir_mean=0.005,
            rrs_nir_std=0.002,
            mask_std_factor=1.0,
        )

        output_file = os.path.join(output_dir, os.path.basename(filepath))
        with rasterio.open(output_file) as src:
            new_profile = src.profile

            assert new_profile["width"] == original_profile["width"]
            assert new_profile["height"] == original_profile["height"]
            assert new_profile["crs"] == original_profile["crs"]
            assert new_profile["transform"] == original_profile["transform"]
            assert new_profile["dtype"] == original_profile["dtype"]
            assert new_profile["count"] == 5  # stacked to exactly 5 bands

        shutil.rmtree(output_dir, ignore_errors=True)


# # ----------------------------------------------------------------------
# # Tests for the public std_masking function
# # ----------------------------------------------------------------------
# class TestStdMaskingFunction:
#     """Test cases for the full std_masking pipeline"""

#     def test_std_masking_runs_and_creates_files(self):
#         """End-to-end test: runs std_masking and checks output files exist"""
#         output_dir = settings.masked_rrs_dir
#         if output_dir.exists():
#             shutil.rmtree(output_dir)

#         results = std_masking(
#             num_images=5,
#             mask_std_factor=1,
#             num_workers=1,        # keep deterministic in tests
#         )

#         assert isinstance(results, list)
#         assert len(results) == len(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))

#         masked_files = glob.glob(os.path.join(output_dir, "*.tif"))
#         assert len(masked_files) > 0, "Masked output files should be created"

#     # def test_std_masking_with_zero_std_does_not_crash(self):
#     #     """Edge case: if std=0 (all NIR identical), should still work"""
#     #     # Force a situation where NIR is constant across sampled images
#     #     # (not easy without mocking, but at least ensure it doesn't divide-by-zero)
#     #     results = std_masking(
#     #         num_images=3,
#     #         mask_std_factor=0,   # very aggressive masking
#     #         num_workers=1,
#     #     )
#     #     assert results is not None

#     # def test_std_masking_respects_num_workers_and_executor(self, monkeypatch):
#     #     """Test that custom executor is used when provided"""
#     #     call_count = 0

#     #     class DummyExecutor:
#     #         def __enter__(self): return self
#     #         def __exit__(self, *args): pass
#     #         def map(self, func, iterable):
#     #             nonlocal call_count
#     #             call_count += 1
#     #             return map(func, iterable)

#     #     results = std_masking(
#     #         num_images=3,
#     #         mask_std_factor=1,
#     #         num_workers=4,
#     #         executor=DummyExecutor(),
#     #     )
#     #     assert call_count == 1  # executor.map was used