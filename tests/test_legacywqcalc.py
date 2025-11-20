import sys
import os

# Needs access to
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
import numpy as np
from numpy.testing import assert_allclose
import dronewq
import utils

algs_dronewq = [
    dronewq.chl_hu,
    dronewq.chl_ocx,
    dronewq.chl_hu_ocx,
    dronewq.chl_gitelson,
    dronewq.tsm_nechad,
]


def test_chl_hu():
    """Test chl_hu algorithm comparing utils to dronewq"""
    # Test case 1: Simple values
    Rrsblue = np.array([[1.0, 2.0], [3.0, 4.0]])
    Rrsgreen = np.array([[1.5, 2.5], [3.5, 4.5]])
    Rrsred = np.array([[0.5, 1.5], [2.5, 3.5]])

    out_utils = utils.chl_hu(Rrsblue, Rrsgreen, Rrsred)
    Rrs_stacked = np.stack([Rrsblue, Rrsgreen, Rrsred], axis=0)
    out_dronewq = dronewq.chl_hu(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

    # Test case 2: Different values
    Rrsblue = np.array([[0.001]])
    Rrsgreen = np.array([[0.002]])
    Rrsred = np.array([[0.0005]])

    out_utils = utils.chl_hu(Rrsblue, Rrsgreen, Rrsred)
    Rrs_stacked = np.stack([Rrsblue, Rrsgreen, Rrsred], axis=0)
    out_dronewq = dronewq.chl_hu(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)


def test_chl_ocx():
    """Test chl_ocx algorithm comparing utils to dronewq"""
    # Test case 1: Basic test
    Rrsblue = np.array([[2.0, 3.0], [4.0, 5.0]])
    Rrsgreen = np.array([[1.0, 1.5], [2.0, 2.5]])

    out_utils = utils.chl_ocx(Rrsblue, Rrsgreen)
    Rrs_stacked = np.stack([Rrsblue, Rrsgreen], axis=0)
    out_dronewq = dronewq.chl_ocx(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

    # Test case 2: Different ratio
    Rrsblue = np.array([[0.5]])
    Rrsgreen = np.array([[1.0]])

    out_utils = utils.chl_ocx(Rrsblue, Rrsgreen)
    Rrs_stacked = np.stack([Rrsblue, Rrsgreen], axis=0)
    out_dronewq = dronewq.chl_ocx(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)


def test_chl_hu_ocx():
    """Test chl_hu_ocx blended algorithm comparing utils to dronewq"""
    # Test case 1: Multiple values
    Rrsblue = np.array([[1.0, 1.5]])
    Rrsgreen = np.array([[1.2, 1.7]])
    Rrsred = np.array([[0.8, 1.3]])

    out_utils = utils.chl_hu_ocx(Rrsblue, Rrsgreen, Rrsred)
    Rrs_stacked = np.stack([Rrsblue, Rrsgreen, Rrsred], axis=0)
    out_dronewq = dronewq.chl_hu_ocx(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

    # Test case 2: Single pixel
    val = np.array([[2.0]])

    out_utils = utils.chl_hu_ocx(val, val, val)
    Rrs_stacked = np.stack([val, val, val], axis=0)
    out_dronewq = dronewq.chl_hu_ocx(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)


def test_chl_gitelson():
    """Test chl_gitelson 2-band algorithm comparing utils to dronewq"""
    # Test case 1: Basic test
    Rrsred = np.array([[1.0, 2.0], [3.0, 4.0]])
    Rrsrededge = np.array([[2.0, 3.0], [4.0, 5.0]])

    out_utils = utils.chl_gitelson(Rrsred, Rrsrededge)

    dummy = np.zeros_like(Rrsred)
    Rrs_stacked = np.stack([dummy, dummy, Rrsred, Rrsrededge], axis=0)
    out_dronewq = dronewq.chl_gitelson(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

    # Test case 2: Different ratio
    Rrsred = np.array([[0.5]])
    Rrsrededge = np.array([[1.5]])

    out_utils = utils.chl_gitelson(Rrsred, Rrsrededge)
    dummy = np.zeros_like(Rrsred)
    Rrs_stacked = np.stack([dummy, dummy, Rrsred, Rrsrededge], axis=0)
    out_dronewq = dronewq.chl_gitelson(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)


def test_tsm_nechad():
    """Test tsm_nechad algorithm comparing utils to dronewq"""
    # Test case 1: Basic test
    Rrsred = np.array([[1.0, 2.0], [3.0, 4.0]])

    out_utils = utils.tsm_nechad(Rrsred)

    dummy = np.zeros_like(Rrsred)
    Rrs_stacked = np.stack([dummy, dummy, Rrsred], axis=0)
    out_dronewq = dronewq.tsm_nechad(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

    # Test case 2: Single pixel
    Rrsred = np.array([[0.5]])

    out_utils = utils.tsm_nechad(Rrsred)
    dummy = np.zeros_like(Rrsred)
    Rrs_stacked = np.stack([dummy, dummy, Rrsred], axis=0)
    out_dronewq = dronewq.tsm_nechad(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

    # Test case 3: Larger array
    Rrsred = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

    out_utils = utils.tsm_nechad(Rrsred)
    dummy = np.zeros_like(Rrsred)
    Rrs_stacked = np.stack([dummy, dummy, Rrsred], axis=0)
    out_dronewq = dronewq.tsm_nechad(Rrs_stacked)

    assert_allclose(out_utils, out_dronewq, rtol=1e-10)

