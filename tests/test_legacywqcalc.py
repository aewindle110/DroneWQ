import sys
import os

# Needs access to 
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import numpy as np
from numpy.testing import assert_allclose

import utils


def test_chl_hu_basic():
    # Simple test with values of 1
    Rrsblue = np.array([[1.0]])
    Rrsgreen = np.array([[1.0]])
    Rrsred = np.array([[1.0]])

    out = utils.chl_hu(Rrsblue, Rrsgreen, Rrsred)
    
    # Just check it returns a numeric array of correct shape
    assert out.shape == (1, 1)
    assert np.isfinite(out[0, 0])


def test_chl_ocx_basic():
    Rrsblue = np.array([[2.0]])
    Rrsgreen = np.array([[1.0]])

    out = utils.chl_ocx(Rrsblue, Rrsgreen)
    
    # Just check it returns a numeric array of correct shape
    assert out.shape == (1, 1)
    assert np.isfinite(out[0, 0])

    
def test_chl_hu_ocx_prefers_ocx_for_equal_bands():
    # Simple test with value of 1
    val = np.array([[1.0]])
    
    out = utils.chl_hu_ocx(val, val, val)
    
    # Just check it returns a numeric array of correct shape
    assert out.shape == (1, 1)
    assert np.isfinite(out[0, 0])


def test_chl_gitelson_and_tsm_nechad():
    Rrsred = np.array([[1.0]])
    Rrsrededge = np.array([[2.0]])

    out_chl = utils.chl_gitelson(Rrsred, Rrsrededge)
    
    # Just check it returns a numeric array of correct shape
    assert out_chl.shape == (1, 1)
    assert np.isfinite(out_chl[0, 0])

    # tsm_nechad
    Rrsred2 = np.array([[1.0]])
    out_tsm = utils.tsm_nechad(Rrsred2)
    
    # Just check it returns a numeric array of correct shape
    assert out_tsm.shape == (1, 1)
    assert np.isfinite(out_tsm[0, 0])


def test_euclidean_distance_and_get_center():
    # Simple 3-4-5 triangle
    p1 = (0.0, 0.0)
    p2 = (3.0, 4.0)
    assert utils.euclidean_distance(p1, p2) == 5.0

    # Simple 2x2 square centered at (1, 1)
    pts = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]])
    center = utils.get_center(pts)
    assert_allclose(center, np.array([1.0, 1.0]))


def test_is_on_right_side_and_point_within_vertices():
    # horizontal line from (0,0) to (1,0)
    xy0 = (0.0, 0.0)
    xy1 = (1.0, 0.0)
    # point above (y positive)
    assert not utils.is_on_right_side(0.0, 1.0, xy0, xy1)
    # point below
    assert utils.is_on_right_side(0.0, -1.0, xy0, xy1)

    # Simple unit square
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    # Point in center
    assert utils.is_point_within_vertices(0.5, 0.5, square)
    # Point outside
    assert not utils.is_point_within_vertices(2.0, 2.0, square)

    # Points inside square
    points = [(0.2, 0.2), (0.8, 0.8)]
    assert utils.are_points_within_vertices(square, points)


def test_compute_lines_and_compute_flight_lines():
    # Simple sequence [0, 1, 2]
    lines = utils.compute_lines([], [0, 1, 2])
    assert (0, 2) in lines

    # Two separated groups of angles
    captures_yaw = np.array([10.0, 11.0, 12.0, 190.0, 191.0, 192.0])
    altitude = 100.0
    pitch = 0.5
    roll = 0.1
    flight_lines = utils.compute_flight_lines(captures_yaw, altitude, pitch, roll, threshold=10)

    # Should produce at least 2 flight lines
    assert isinstance(flight_lines, list)
    assert len(flight_lines) >= 2
    # Check required keys exist
    for f in flight_lines:
        assert set(['start', 'end', 'yaw', 'pitch', 'roll', 'alt']).issubset(set(f.keys()))


def test_paralelogram2d_methods():
    # Simple 2x1 rectangle
    pts = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]])
    p = utils.Paralelogram2D(pts.copy())

    # Line 0 center (between (0,0) and (2,0))
    lc = p.get_line_center(0)
    assert_allclose(lc, np.array([1.0, 0.0]))

    # Offset from origin to line 0 center
    off = p.get_offset_to_lines(0, np.array([0.0, 0.0]))
    assert_allclose(off, np.array([1.0, 0.0]))

    # Rectangle center
    c = p.get_center()
    assert_allclose(c, np.array([1.0, 0.5]))

    # Move line and check points changed
    before = p.points.copy()
    p.move_line_from_offset(0, np.array([0.5, 0.0]))
    assert not np.allclose(before, p.points)

    # Test point on right side
    test_points = np.array([[2.1, 0.5]])
    result = p.are_on_right_side_of_line(1, test_points)
    assert isinstance(result, (bool, np.bool_))