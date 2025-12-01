import sys
import os
from pathlib import Path
import shutil

import numpy as np
import rasterio
import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from dronewq import settings
from dronewq.lw_methods.blackpixel import _compute
from dronewq.utils.images import load_imgs

test_path = Path(__file__).absolute().parent / "test_set"
if not test_path.exists():
    raise LookupError(f"Could not find test directory: {test_path}")

settings.configure(main_dir=test_path)


class TestComputeFunction:
    """Test cases for the _compute worker function"""
    
    @pytest.fixture
    def single_test_image(self):
        """Fixture to provide a single test image path"""
        filepath = os.path.join(settings.lt_dir, "capture_1.tif")
        assert os.path.exists(filepath), f"Test image not found: {filepath}"
        return filepath
    
    @pytest.fixture
    def lsky_median(self):
        """Fixture to provide computed lsky_median"""
        sky_imgs = list(load_imgs(settings.sky_lt_dir, count=10, start=0))
        sky_imgs = np.array(sky_imgs)
        return np.median(sky_imgs, axis=(0, 2, 3))
    
    @pytest.fixture
    def output_dir(self):
        """Fixture to provide and clean up output directory"""
        output_dir = settings.lw_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        yield output_dir
        shutil.rmtree(output_dir, ignore_errors=True)

    def test_compute_basic(self, single_test_image, lsky_median, output_dir):
        """Test _compute function creates output file"""
        result = _compute(
            filepath=single_test_image,
            lsky_median=lsky_median,
            lw_dir=output_dir,
        )

        assert result is True, "_compute should return True on success"

        output_file = os.path.join(output_dir, os.path.basename(single_test_image))
        assert os.path.exists(output_file), "Output file should be created"

    def test_compute_output_has_correct_bands(self, single_test_image, lsky_median, output_dir):
        """Test that _compute creates output with 5 bands"""
        _compute(
            filepath=single_test_image,
            lsky_median=lsky_median,
            lw_dir=output_dir,
        )

        output_file = os.path.join(output_dir, os.path.basename(single_test_image))
        with rasterio.open(output_file) as src:
            lw_data = src.read()
            assert lw_data.shape[0] == 5, "Lw must have 5 output bands"

    def test_compute_preserves_spatial_shape(self, single_test_image, lsky_median, output_dir):
        """Test that _compute preserves spatial dimensions"""
        with rasterio.open(single_test_image) as src:
            lt_shape = src.read().shape

        _compute(
            filepath=single_test_image,
            lsky_median=lsky_median,
            lw_dir=output_dir,
        )

        output_file = os.path.join(output_dir, os.path.basename(single_test_image))
        with rasterio.open(output_file) as src:
            lw_data = src.read()
            assert lw_data.shape[1:] == lt_shape[1:], "Spatial shape must match"

    def test_compute_physical_equation_holds(self, single_test_image, lsky_median, output_dir):
        """Check that formula lw = Lt(i) - rho * Lsky(i) is satisfied for sample pixels."""
        _compute(
            filepath=single_test_image,
            lsky_median=lsky_median,
            lw_dir=output_dir,
        )

        output_file = os.path.join(output_dir, os.path.basename(single_test_image))

        with rasterio.open(single_test_image) as lt_src, rasterio.open(output_file) as lw_src:
            lt = lt_src.read()
            lw = lw_src.read()

            nir = 3
            rho = lt[nir] / lsky_median[nir]

            band = 1
            computed_lw = lt[band] - rho * lsky_median[band]

            sample = computed_lw[10:20, 10:20]
            sample_lw = lw[band][10:20, 10:20]

            assert np.allclose(sample, sample_lw, atol=1e-6), \
                "Lw equation should hold for sampled pixels"

    def test_compute_with_invalid_filepath(self, lsky_median, output_dir):
        """Test _compute raises exception with invalid filepath"""
        with pytest.raises(Exception):
            _compute(
                filepath="/nonexistent/path/to/file.tif",
                lsky_median=lsky_median,
                lw_dir=output_dir,
            )