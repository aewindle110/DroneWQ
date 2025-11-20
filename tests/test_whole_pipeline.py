import dronewq
import numpy as np
import pandas as pd
import os
from dronewq import settings
from numpy.testing import assert_allclose

test_path = os.path.abspath(__file__)
test_path = os.path.join(os.path.dirname(test_path), "test_set")

if not os.path.exists(test_path):
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
    lt_imgs = dronewq.load_imgs(settings.lt_dir)
    results = []

    for lt_img in lt_imgs:
        med = np.nanmean(lt_img, axis=(1, 2))
        results.append(med)
    results = np.array(results)
    results = np.squeeze(results)
    assert_allclose(actual, results, rtol=1e-2)


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
    lw_imgs = dronewq.load_imgs(settings.lw_dir)
    results = []

    for lw_img in lw_imgs:
        med = np.nanmean(lw_img, axis=(1, 2))
        results.append(med)
    results = np.array(results)
    results = np.squeeze(results)

    assert_allclose(actual, results, rtol=1e-2)


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
    rrs_imgs = dronewq.load_imgs(settings.rrs_dir)
    results = []

    for rrs_img in rrs_imgs:
        med = np.nanmean(rrs_img, axis=(1, 2))
        results.append(med)
    results = np.array(results)

    results = np.squeeze(results)

    assert_allclose(actual, results, rtol=1e-2)


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

    dls_path = os.path.join(test_path, "dls_ed.csv")
    df = pd.read_csv(dls_path)

    row = df[df["image"] == "capture_1"].to_numpy()

    results = np.array(row[0, 1:], dtype=np.float32)

    results = np.squeeze(results)

    assert_allclose(actual, results, rtol=1e-2)


def test_chl_hu_ocx():
    actual = 1.0326097
    rrs_imgs = dronewq.load_imgs(settings.rrs_dir)

    results = []
    for rrs_img in rrs_imgs:
        med = dronewq.chl_hu_ocx(rrs_img)
        results.append(np.nanmean(med))
    results = np.array(results)
    results = np.squeeze(results)

    assert_allclose(actual, results, rtol=1e-2)


def test_tsm_nechad():
    actual = 1.6712015
    rrs_imgs = dronewq.load_imgs(settings.rrs_dir)

    results = []
    for rrs_img in rrs_imgs:
        med = dronewq.tsm_nechad(rrs_img)
        results.append(np.nanmean(med))
    results = np.array(results)
    results = np.squeeze(results)

    assert_allclose(actual, results, rtol=1e-2)
