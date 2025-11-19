# Checks wq_algs edge cases
import numpy as np

import dronewq

algs = [
    dronewq.chl_hu,
    dronewq.chl_ocx,
    dronewq.chl_hu_ocx,
    dronewq.chl_gitelson,
    dronewq.tsm_nechad,
]


def test_wq_algs_normal_image():
    # Create a normal test image (5 bands, 10x10)
    img = np.random.rand(5, 10, 10)
    for alg in algs:
        result = alg(img)
        assert result.shape == (10, 10)
        # Should not be NaN
        assert not np.isnan(result).all()


def test_wq_algs_all_nan_image():
    # All NaN image
    img = np.full((5, 10, 10), np.nan)
    for alg in algs:
        result = alg(img)
        assert isinstance(result, np.ndarray)
        assert result.shape == (10, 10)
        assert np.isnan(result).all()


def test_wq_algs_values_array_homogeneous():
    # Simulate a batch of images including normal, all-NaN
    imgs = [
        np.random.rand(5, 10, 10),
        np.full((5, 10, 10), np.nan),
    ]
    for alg in algs:
        values = []
        for img in imgs:
            result = alg(img)
            values.append(result)
        arr = np.array(values)
        assert arr.shape == (2, 10, 10)
        assert arr.dtype.kind in {"f", "d"}
