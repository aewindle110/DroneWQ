# tests/test_wq_calc.py
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pytest
import rasterio

from dronewq.utils.settings import settings

TEST_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".test_project"))
os.makedirs(TEST_PROJECT_ROOT, exist_ok=True)
settings.main_dir = TEST_PROJECT_ROOT # Configure main_dir for tests


from dronewq.core.wq_calc import (
    save_wq_imgs,
    _compute,
    chl_hu,
    chl_ocx,
    chl_hu_ocx,
    chl_gitelson,
    tsm_nechad,
)


REAL_RRS_DIR = str(Path(__file__).parent / "test_set" / "rrs_imgs")


@pytest.fixture(scope="function")
def clean_rrs_dir():
    """Fresh directory with exactly 3 real + 1 high-index file"""
    rrs_dir = os.path.join(TEST_PROJECT_ROOT, "rrs_input")
    if os.path.exists(rrs_dir):
        shutil.rmtree(rrs_dir)
    os.makedirs(rrs_dir)

    # Copy real images
    real_files = sorted(Path(REAL_RRS_DIR).glob("*.tif"))[:3]
    for i, src in enumerate(real_files):
        # Force predictable naming so sorting works reliably
        dst_name = f"capture_{i+1:06d}.tif"
        shutil.copy(src, os.path.join(rrs_dir, dst_name))

    yield rrs_dir
    shutil.rmtree(rrs_dir, ignore_errors=True)


@pytest.mark.parametrize("alg", [chl_hu, chl_ocx, chl_hu_ocx, chl_gitelson, tsm_nechad])
def test_alg_basic(alg):
    img = np.random.uniform(0.001, 0.03, size=(5, 30, 30)).astype(np.float32)
    out = alg(img)
    assert out.shape == (30, 30)
    assert np.isfinite(out).any()

# def test_chl_hu_ocx_global_blending_behavior():
#     Rrs = np.zeros((5, 100, 100), dtype=np.float32)

#     # Case 1: ALL pixels low → should use pure CI
#     Rrs[0] = 0.003; Rrs[1] = 0.002; Rrs[2] = 0.0005
#     assert np.all(chl_hu_ocx(Rrs.copy()) == chl_hu(Rrs))

#     # Case 2: ALL pixels high → should use pure OCx
#     Rrs[0] = 0.02; Rrs[1] = 0.001
#     assert np.all(chl_hu_ocx(Rrs.copy()) == chl_ocx(Rrs))

#     # Case 3: ALL pixels in transition → should blend (same for whole image)
#     Rrs[0] = 0.008; Rrs[1] = 0.005; Rrs[2] = 0.0015
#     result = chl_hu_ocx(Rrs.copy())
#     ci_val = chl_hu(Rrs)[0,0]  # scalar
#     ocx_val = chl_ocx(Rrs)[0,0]
#     expected = ocx_val * (ci_val - 0.15)/0.05 + ci_val * (0.20 - ci_val)/0.05
#     assert np.allclose(result, expected)


def test_compute_one_file(clean_rrs_dir):
    tif = Path(clean_rrs_dir) / "capture_000001.tif"
    out_dir = os.path.join(TEST_PROJECT_ROOT, "masked_test")
    os.makedirs(out_dir, exist_ok=True)

    assert _compute(str(tif), "chl_gitelson", out_dir) is True
    assert (Path(out_dir) / tif.name).exists()


# def test_save_wq_imgs_basic(clean_rrs_dir):
#     save_wq_imgs(rrs_dir=clean_rrs_dir, wq_alg="chl_gitelson", num_workers=1)

#     out_dir = Path(TEST_PROJECT_ROOT) / "masked_chl_gitelson_imgs"
#     output_files = list(out_dir.glob("*.tif"))
#     assert len(output_files) == 1
#     assert getattr(settings, "chl_gitelson_dir", None) == str(out_dir)


@pytest.mark.parametrize("alg", ["chl_hu", "chl_ocx", "chl_hu_ocx", "chl_gitelson", "tsm_nechad"])
def test_save_wq_imgs_all_algorithms(clean_rrs_dir, alg):
    save_wq_imgs(rrs_dir=clean_rrs_dir, wq_alg=alg, num_workers=1)
    out_dir = Path(TEST_PROJECT_ROOT) / f"masked_{alg}_imgs"
    assert out_dir.exists()
    assert any(f.suffix == ".tif" for f in out_dir.iterdir())


def test_save_wq_imgs_external_executor(clean_rrs_dir):
    with ProcessPoolExecutor(max_workers=2) as exec:
        save_wq_imgs(rrs_dir=clean_rrs_dir, wq_alg="tsm_nechad", executor=exec)

    out_dir = Path(TEST_PROJECT_ROOT) / "masked_tsm_nechad_imgs"
    assert len(list(out_dir.glob("*.tif"))) >= 1