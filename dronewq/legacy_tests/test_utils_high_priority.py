import sys
import os

# Needs access to the repo root to import utils.py
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
from numpy.testing import assert_allclose

import utils


def test_chl_hu_basic():
    # scalar 1x1 arrays
    Rrsblue = np.array([[0.01]])
    Rrsgreen = np.array([[0.02]])
    Rrsred = np.array([[0.015]])

    # manual calculation using the same formula as function
    ci1 = -0.4909
    ci2 = 191.6590
    CI = Rrsgreen - (Rrsblue + (560 - 475) / (668 - 475) * (Rrsred - Rrsblue))
    expected = 10 ** (ci1 + ci2 * CI)

    out = utils.chl_hu(Rrsblue, Rrsgreen, Rrsred)
    assert_allclose(out, expected)


def test_chl_ocx_basic():
    Rrsblue = np.array([[0.02]])
    Rrsgreen = np.array([[0.01]])

    # compute expected according to function coefficients
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    temp = np.log10(Rrsblue / Rrsgreen)
    log10chl = a0 + a1 * (temp) + a2 * (temp) ** 2 + a3 * (temp) ** 3 + a4 * (temp) ** 4
    expected = np.power(10, log10chl)

    out = utils.chl_ocx(Rrsblue, Rrsgreen)
    assert_allclose(out, expected)
