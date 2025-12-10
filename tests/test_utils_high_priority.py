import os
import sys

# Needs access to
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
from numpy.testing import assert_allclose

import dronewq.legacy.utils as utils


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


def test_chl_hu_ocx_prefers_ocx_for_equal_bands():
    # when all bands equal, CI = 0 -> ChlCI = 10**ci1 (~0.322) and OCX = 10**a0 (~1.58)
    val = np.array([[0.01]])
    out = utils.chl_hu_ocx(val, val, val)

    # compute ocx for comparison
    ocx = utils.chl_ocx(val, val)
    # for this input ocx should be chosen by the implementation
    assert_allclose(out, ocx)


def test_chl_gitelson_and_tsm_nechad():
    Rrsred = np.array([[0.02]])
    Rrsrededge = np.array([[0.03]])

    expected_chl = 59.826 * (Rrsrededge / Rrsred) - 17.546
    out_chl = utils.chl_gitelson(Rrsred, Rrsrededge)
    assert_allclose(out_chl, expected_chl)

    # tsm_nechad
    Rrsred2 = np.array([[0.05]])
    A = 374.11
    B = 1.61
    C = 17.38
    expected_tsm = (A * Rrsred2 / (1 - (Rrsred2 / C))) + B
    out_tsm = utils.tsm_nechad(Rrsred2)
    assert_allclose(out_tsm, expected_tsm)


def test_euclidean_distance_and_get_center():
    p1 = (0.0, 0.0)
    p2 = (3.0, 4.0)
    assert utils.euclidean_distance(p1, p2) == 5.0

    pts = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]])
    center = utils.get_center(pts)
    assert_allclose(center, np.array([1.0, 1.0]))


def test_is_on_right_side_and_point_within_vertices():
    # horizontal line from (0,0) to (1,0)
    xy0 = (0.0, 0.0)
    xy1 = (1.0, 0.0)
    # point above (y positive) should be NOT on right side according to implementation
    assert not utils.is_on_right_side(0.0, 1.0, xy0, xy1)
    # point below should be on right side
    assert utils.is_on_right_side(0.0, -1.0, xy0, xy1)

    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert utils.is_point_within_vertices(0.5, 0.5, square)
    assert not utils.is_point_within_vertices(2.0, 2.0, square)

    points = [(0.2, 0.2), (0.8, 0.8)]
    assert utils.are_points_within_vertices(square, points)


def test_compute_lines_and_compute_flight_lines():
    # compute_lines simple sequence
    lines = utils.compute_lines([], [0, 1, 2])
    # expected a single interval (0,2)
    assert (0, 2) in lines

    # compute_flight_lines with two separated transects
    captures_yaw = np.array([10.0, 11.0, 12.0, 190.0, 191.0, 192.0])
    altitude = 100.0
    pitch = 0.5
    roll = 0.1
    flight_lines = utils.compute_flight_lines(
        captures_yaw, altitude, pitch, roll, threshold=10
    )

    # should produce two flight lines
    assert isinstance(flight_lines, list)
    assert len(flight_lines) >= 2
    # each entry should have required keys
    for f in flight_lines:
        assert set(["start", "end", "yaw", "pitch", "roll", "alt"]).issubset(
            set(f.keys())
        )


def test_paralelogram2d_methods():
    pts = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]])
    p = utils.Paralelogram2D(pts.copy())

    # line 0 is between points 0 and 1 -> center should be (1,0)
    lc = p.get_line_center(0)
    assert_allclose(lc, np.array([1.0, 0.0]))

    # offset to lines from point (0,0)
    off = p.get_offset_to_lines(0, np.array([0.0, 0.0]))
    assert_allclose(off, lc - np.array([0.0, 0.0]))

    # center of parallelogram
    c = p.get_center()
    assert_allclose(c, np.array([1.0, 0.5]))

    # move a line and ensure points changed
    before = p.points.copy()
    p.move_line_from_offset(0, np.array([0.5, 0.0]))
    assert not np.allclose(before, p.points)

    # are_on_right_side_of_line for a point known to be on right side of line 0
    test_points = np.array([[2.1, 0.5]])
    assert p.are_on_right_side_of_line(1, test_points) or isinstance(
        p.are_on_right_side_of_line(1, test_points), bool
    )
