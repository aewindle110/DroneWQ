# Author: Kurtis
import os
import sys

# Needs access to utils module
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import glob
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.testing import assert_allclose

import dronewq
import dronewq.legacy.utils as utils
from dronewq import settings

test_path = Path(__file__).absolute().parent
test_path = test_path.joinpath("test_set")
if not test_path.exists():
    msg = f"Could not find {test_path}"
    raise LookupError(msg)

settings.configure(main_dir=test_path)
dronewq.write_metadata_csv(settings.raw_water_dir, settings.main_dir)
dronewq.process_raw_to_rrs(settings.main_dir, num_workers=1, clean_intermediates=False)


def test_Lt():
    actual = np.array(
        [
            6.0932446,
            2.4866774,
            0.7276736,
            0.43822095,
            0.27674899,
        ]
    )

    # Test dronewq
    lt_imgs_dronewq = dronewq.load_imgs(settings.lt_dir)
    results_dronewq = []
    for lt_img in lt_imgs_dronewq:
        med = np.nanmean(lt_img, axis=(1, 2))
        results_dronewq.append(med)
    results_dronewq = np.array(results_dronewq)
    results_dronewq = np.squeeze(results_dronewq)
    assert_allclose(actual, results_dronewq, rtol=1e-2)

    # Test utils (uses load_images instead of load_imgs)
    lt_img_list = sorted(glob.glob(os.path.join(settings.lt_dir, "*.tif")))
    lt_imgs_utils = utils.load_images(lt_img_list)
    results_utils = []
    for lt_img in lt_imgs_utils:
        med = np.nanmean(lt_img, axis=(1, 2))
        results_utils.append(med)
    results_utils = np.array(results_utils)
    results_utils = np.squeeze(results_utils)
    assert_allclose(actual, results_utils, rtol=1e-2)
    assert_allclose(results_dronewq, results_utils, rtol=1e-6)


def test_Lw():
    actual = np.array(
        [
            4.7610073,
            1.6122506,
            0.19452204,
            0.09821307,
            0.02420409,
        ]
    )

    # Test dronewq
    lw_imgs_dronewq = dronewq.load_imgs(settings.lw_dir)
    results_dronewq = []
    for lw_img in lw_imgs_dronewq:
        med = np.nanmean(lw_img, axis=(1, 2))
        results_dronewq.append(med)
    results_dronewq = np.array(results_dronewq)
    results_dronewq = np.squeeze(results_dronewq)
    assert_allclose(actual, results_dronewq, rtol=1e-2)

    # Test utils
    lw_img_list = sorted(glob.glob(os.path.join(settings.lw_dir, "*.tif")))
    lw_imgs_utils = utils.load_images(lw_img_list)
    results_utils = []
    for lw_img in lw_imgs_utils:
        med = np.nanmean(lw_img, axis=(1, 2))
        results_utils.append(med)
    results_utils = np.array(results_utils)
    results_utils = np.squeeze(results_utils)
    assert_allclose(actual, results_utils, rtol=1e-2)
    assert_allclose(results_dronewq, results_utils, rtol=1e-6)


def test_Rrs():
    actual = np.array(
        [
            3.3371164e-03,
            1.2021328e-03,
            1.6358867e-04,
            1.1502275e-04,
            3.4010543e-05,
        ]
    )

    # Test dronewq
    rrs_imgs_dronewq = dronewq.load_imgs(settings.rrs_dir)
    results_dronewq = []
    for rrs_img in rrs_imgs_dronewq:
        med = np.nanmean(rrs_img, axis=(1, 2))
        results_dronewq.append(med)
    results_dronewq = np.array(results_dronewq)
    results_dronewq = np.squeeze(results_dronewq)
    assert_allclose(actual, results_dronewq, rtol=1e-2)

    # Test utils
    rrs_img_list = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
    rrs_imgs_utils = utils.load_images(rrs_img_list)
    results_utils = []
    for rrs_img in rrs_imgs_utils:
        med = np.nanmean(rrs_img, axis=(1, 2))
        results_utils.append(med)
    results_utils = np.array(results_utils)
    results_utils = np.squeeze(results_utils)
    assert_allclose(actual, results_utils, rtol=1e-2)
    assert_allclose(results_dronewq, results_utils, rtol=1e-6)


def test_Ed():
    actual = np.array(
        [
            1426.6836703319698,
            1341.158530159746,
            1189.0926660620944,
            853.857851386549,
            711.6641091763706,
        ],
        dtype=np.float32,
    )
    dls_path = test_path.joinpath("dls_ed.csv")
    df = pd.read_csv(dls_path)
    row = df[df["image"] == "capture_1"].to_numpy()
    results = np.array(row[0, 1:], dtype=np.float32)
    results = np.squeeze(results)
    assert_allclose(actual, results, rtol=1e-2)


def test_chl_hu_ocx():
    actual = 1.0326097

    # Test dronewq
    rrs_imgs_dronewq = dronewq.load_imgs(settings.rrs_dir)
    results_dronewq = []
    for rrs_img in rrs_imgs_dronewq:
        med = dronewq.chl_hu_ocx(rrs_img)
        results_dronewq.append(np.nanmean(med))
    results_dronewq = np.array(results_dronewq)
    results_dronewq = np.squeeze(results_dronewq)
    assert_allclose(actual, results_dronewq, rtol=1e-2)

    # Test utils
    # utils.chl_hu_ocx takes (Rrsblue, Rrsgreen, Rrsred) as separate arguments
    rrs_img_list = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
    rrs_imgs_utils = utils.load_images(rrs_img_list)
    results_utils = []
    for rrs_img in rrs_imgs_utils:
        # Band indices: 0=blue, 1=green, 2=red, 3=red_edge, 4=nir
        med = utils.chl_hu_ocx(rrs_img[0, :, :], rrs_img[1, :, :], rrs_img[2, :, :])
        results_utils.append(np.nanmean(med))
    results_utils = np.array(results_utils)
    results_utils = np.squeeze(results_utils)
    assert_allclose(actual, results_utils, rtol=1e-2)
    assert_allclose(results_dronewq, results_utils, rtol=1e-2)


def test_tsm_nechad():
    actual = 1.6712015

    # Test dronewq
    rrs_imgs_dronewq = dronewq.load_imgs(settings.rrs_dir)
    results_dronewq = []
    for rrs_img in rrs_imgs_dronewq:
        med = dronewq.tsm_nechad(rrs_img)
        results_dronewq.append(np.nanmean(med))
    results_dronewq = np.array(results_dronewq)
    results_dronewq = np.squeeze(results_dronewq)
    assert_allclose(actual, results_dronewq, rtol=1e-2)

    # Test utils
    # utils.tsm_nechad takes Rrsred as argument
    rrs_img_list = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
    rrs_imgs_utils = utils.load_images(rrs_img_list)
    results_utils = []
    for rrs_img in rrs_imgs_utils:
        # Band index 2 = red band
        med = utils.tsm_nechad(rrs_img[2, :, :])
        results_utils.append(np.nanmean(med))
    results_utils = np.array(results_utils)
    results_utils = np.squeeze(results_utils)
    assert_allclose(actual, results_utils, rtol=1e-2)
    assert_allclose(results_dronewq, results_utils, rtol=1e-2)


def test_chl_hu():
    """Test utils.chl_hu algorithm"""
    rrs_img_list = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
    rrs_imgs = utils.load_images(rrs_img_list)

    for rrs_img in rrs_imgs:
        # Band indices: 0=blue, 1=green, 2=red
        result = utils.chl_hu(rrs_img[0, :, :], rrs_img[1, :, :], rrs_img[2, :, :])
        # Just verify it runs and produces valid output
        assert result.shape == rrs_img[0, :, :].shape
        assert not np.all(np.isnan(result))


def test_chl_ocx():
    """Test utils.chl_ocx algorithm"""
    rrs_img_list = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
    rrs_imgs = utils.load_images(rrs_img_list)

    for rrs_img in rrs_imgs:
        # Band indices: 0=blue, 1=green
        result = utils.chl_ocx(rrs_img[0, :, :], rrs_img[1, :, :])
        # Just verify it runs and produces valid output
        assert result.shape == rrs_img[0, :, :].shape
        assert not np.all(np.isnan(result))


def test_chl_gitelson():
    """Test utils.chl_gitelson algorithm"""
    rrs_img_list = sorted(glob.glob(os.path.join(settings.rrs_dir, "*.tif")))
    rrs_imgs = utils.load_images(rrs_img_list)

    for rrs_img in rrs_imgs:
        # Band indices: 2=red, 3=red_edge
        result = utils.chl_gitelson(rrs_img[2, :, :], rrs_img[3, :, :])
        # Just verify it runs and produces valid output
        assert result.shape == rrs_img[2, :, :].shape
        assert not np.all(np.isnan(result))


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

