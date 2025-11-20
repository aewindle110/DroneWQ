import sys
import os
# Needs access to 
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
import numpy as np
from dronewq.core.geometry import (
    Paralelogram2D as DronewqParalelogram2D,
    are_points_within_vertices as dronewq_are_points_within_vertices,
    euclidean_distance as dronewq_euclidean_distance,
    get_center as dronewq_get_center,
    is_on_right_side as dronewq_is_on_right_side,
    is_point_within_vertices as dronewq_is_point_within_vertices,
)
import utils


class TestIsOnRightSide(unittest.TestCase):

    def test_point_on_right_side(self):
        # Vertical line from (0,0) to (0,1), point at (1,0.5) should be on right
        result_utils = utils.is_on_right_side(1, 0.5, (0, 0), (0, 1))
        result_dronewq = dronewq_is_on_right_side(1, 0.5, (0, 0), (0, 1))
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)

    def test_point_on_left_side(self):
        # Vertical line from (0,0) to (0,1), point at (-1,0.5) should be on left
        result_utils = utils.is_on_right_side(-1, 0.5, (0, 0), (0, 1))
        result_dronewq = dronewq_is_on_right_side(-1, 0.5, (0, 0), (0, 1))
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)

    def test_point_on_line(self):
        # Point on the line should return False (not strictly greater than 0)
        result_utils = utils.is_on_right_side(0, 0.5, (0, 0), (0, 1))
        result_dronewq = dronewq_is_on_right_side(0, 0.5, (0, 0), (0, 1))
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)

    def test_diagonal_line(self):
        # Diagonal line from (0,0) to (1,1)
        result_utils = utils.is_on_right_side(1, 0, (0, 0), (1, 1))
        result_dronewq = dronewq_is_on_right_side(1, 0, (0, 0), (1, 1))
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)
        
        result_utils = utils.is_on_right_side(0, 1, (0, 0), (1, 1))
        result_dronewq = dronewq_is_on_right_side(0, 1, (0, 0), (1, 1))
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)


class TestIsPointWithinVertices(unittest.TestCase):

    def test_point_inside_square(self):
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result_utils = utils.is_point_within_vertices(0.5, 0.5, vertices)
        result_dronewq = dronewq_is_point_within_vertices(0.5, 0.5, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)

    def test_point_outside_square(self):
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result_utils = utils.is_point_within_vertices(2, 2, vertices)
        result_dronewq = dronewq_is_point_within_vertices(2, 2, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)

    def test_point_on_vertex(self):
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result_utils = utils.is_point_within_vertices(0, 0, vertices)
        result_dronewq = dronewq_is_point_within_vertices(0, 0, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)

    def test_point_on_edge(self):
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result_utils = utils.is_point_within_vertices(0.5, 0, vertices)
        result_dronewq = dronewq_is_point_within_vertices(0.5, 0, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)

    def test_triangle(self):
        """Test with triangle vertices"""
        vertices = [(0, 0), (1, 0), (0.5, 1)]
        result_utils = utils.is_point_within_vertices(0.5, 0.3, vertices)
        result_dronewq = dronewq_is_point_within_vertices(0.5, 0.3, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)
        
        result_utils = utils.is_point_within_vertices(0, 1, vertices)
        result_dronewq = dronewq_is_point_within_vertices(0, 1, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)

    def test_negative_coordinates(self):
        """Test with negative coordinates"""
        vertices = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        result_utils = utils.is_point_within_vertices(0, 0, vertices)
        result_dronewq = dronewq_is_point_within_vertices(0, 0, vertices)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)


class TestArePointsWithinVertices(unittest.TestCase):
    """Test cases comparing utils.are_points_within_vertices to dronewq.are_points_within_vertices"""

    def test_all_points_inside(self):
        """Test when all points are inside"""
        vertices = [(0, 0), (2, 0), (2, 2), (0, 2)]
        points = [(0.5, 0.5), (1, 1), (1.5, 1.5)]
        result_utils = utils.are_points_within_vertices(vertices, points)
        result_dronewq = dronewq_are_points_within_vertices(vertices, points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)

    def test_all_points_outside(self):
        """Test when all points are outside"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = [(2, 2), (3, 3), (4, 4)]
        result_utils = utils.are_points_within_vertices(vertices, points)
        result_dronewq = dronewq_are_points_within_vertices(vertices, points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)

    def test_mixed_points(self):
        """Test when some points are inside and some outside"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = [(0.5, 0.5), (2, 2)]
        result_utils = utils.are_points_within_vertices(vertices, points)
        result_dronewq = dronewq_are_points_within_vertices(vertices, points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertFalse(result_utils)

    def test_empty_points_list(self):
        """Test with empty points list"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = []
        result_utils = utils.are_points_within_vertices(vertices, points)
        result_dronewq = dronewq_are_points_within_vertices(vertices, points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)  # all() of empty list is True

    def test_single_point(self):
        """Test with single point"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = [(0.5, 0.5)]
        result_utils = utils.are_points_within_vertices(vertices, points)
        result_dronewq = dronewq_are_points_within_vertices(vertices, points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)


class TestEuclideanDistance(unittest.TestCase):
    """Test cases comparing utils.euclidean_distance to dronewq.euclidean_distance"""

    def test_distance_same_point(self):
        """Test distance between same point"""
        result_utils = utils.euclidean_distance((0, 0), (0, 0))
        result_dronewq = dronewq_euclidean_distance((0, 0), (0, 0))
        self.assertAlmostEqual(result_utils, result_dronewq)
        self.assertAlmostEqual(result_utils, 0.0)

    def test_distance_horizontal(self):
        """Test distance along horizontal axis"""
        result_utils = utils.euclidean_distance((0, 0), (3, 0))
        result_dronewq = dronewq_euclidean_distance((0, 0), (3, 0))
        self.assertAlmostEqual(result_utils, result_dronewq)
        self.assertAlmostEqual(result_utils, 3.0)

    def test_distance_vertical(self):
        """Test distance along vertical axis"""
        result_utils = utils.euclidean_distance((0, 0), (0, 4))
        result_dronewq = dronewq_euclidean_distance((0, 0), (0, 4))
        self.assertAlmostEqual(result_utils, result_dronewq)
        self.assertAlmostEqual(result_utils, 4.0)

    def test_distance_diagonal(self):
        """Test distance along diagonal"""
        result_utils = utils.euclidean_distance((0, 0), (3, 4))
        result_dronewq = dronewq_euclidean_distance((0, 0), (3, 4))
        self.assertAlmostEqual(result_utils, result_dronewq)
        self.assertAlmostEqual(result_utils, 5.0)

    def test_distance_negative_coordinates(self):
        """Test distance with negative coordinates"""
        result_utils = utils.euclidean_distance((-1, -1), (2, 3))
        result_dronewq = dronewq_euclidean_distance((-1, -1), (2, 3))
        self.assertAlmostEqual(result_utils, result_dronewq)
        self.assertAlmostEqual(result_utils, 5.0)

    def test_distance_float_coordinates(self):
        """Test distance with float coordinates"""
        result_utils = utils.euclidean_distance((0.5, 0.5), (1.5, 1.5))
        result_dronewq = dronewq_euclidean_distance((0.5, 0.5), (1.5, 1.5))
        self.assertAlmostEqual(result_utils, result_dronewq)
        self.assertAlmostEqual(result_utils, np.sqrt(2))


class TestGetCenter(unittest.TestCase):
    """Test cases comparing utils.get_center to dronewq.get_center"""

    def test_center_of_square(self):
        """Test center of square corners"""
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        result_utils = utils.get_center(points)
        result_dronewq = dronewq_get_center(points)
        np.testing.assert_array_almost_equal(result_utils, result_dronewq)
        np.testing.assert_array_almost_equal(result_utils, np.array([0.5, 0.5]))

    def test_center_of_triangle(self):
        """Test center of triangle"""
        points = np.array([[0, 0], [3, 0], [0, 3]])
        result_utils = utils.get_center(points)
        result_dronewq = dronewq_get_center(points)
        np.testing.assert_array_almost_equal(result_utils, result_dronewq)
        np.testing.assert_array_almost_equal(result_utils, np.array([1.0, 1.0]))

    def test_center_single_point(self):
        """Test center with single point"""
        points = np.array([[5, 7]])
        result_utils = utils.get_center(points)
        result_dronewq = dronewq_get_center(points)
        np.testing.assert_array_almost_equal(result_utils, result_dronewq)
        np.testing.assert_array_almost_equal(result_utils, np.array([5.0, 7.0]))

    def test_center_negative_coordinates(self):
        """Test center with negative coordinates"""
        points = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])
        result_utils = utils.get_center(points)
        result_dronewq = dronewq_get_center(points)
        np.testing.assert_array_almost_equal(result_utils, result_dronewq)
        np.testing.assert_array_almost_equal(result_utils, np.array([0.0, 0.0]))

    def test_center_collinear_points(self):
        """Test center of collinear points"""
        points = np.array([[0, 0], [1, 1], [2, 2]])
        result_utils = utils.get_center(points)
        result_dronewq = dronewq_get_center(points)
        np.testing.assert_array_almost_equal(result_utils, result_dronewq)
        np.testing.assert_array_almost_equal(result_utils, np.array([1.0, 1.0]))


class TestParalelogram2D(unittest.TestCase):
    """Test cases comparing utils.Paralelogram2D to dronewq.Paralelogram2D"""

    def setUp(self):
        """Set up test fixtures"""
        self.points = np.array([[0, 0], [2, 0], [3, 1], [1, 1]])
        self.parallelogram_utils = utils.Paralelogram2D(self.points.copy())
        self.parallelogram_dronewq = DronewqParalelogram2D(self.points.copy())

    def test_init(self):
        """Test initialization of Paralelogram2D"""
        self.assertEqual(len(self.parallelogram_utils.points), 4)
        self.assertEqual(len(self.parallelogram_dronewq.points), 4)
        self.assertEqual(self.parallelogram_utils.lines, [[0, 1], [1, 2], [2, 3], [3, 0]])
        self.assertEqual(self.parallelogram_dronewq.lines, [[0, 1], [1, 2], [2, 3], [3, 0]])
        self.assertEqual(self.parallelogram_utils.pairs, [[0, 2], [1, 3]])
        self.assertEqual(self.parallelogram_dronewq.pairs, [[0, 2], [1, 3]])

    def test_init_with_different_points(self):
        """Test initialization with different points"""
        points = np.array([[1, 1], [3, 1], [4, 3], [2, 3]])
        para_utils = utils.Paralelogram2D(points.copy())
        para_dronewq = DronewqParalelogram2D(points.copy())
        np.testing.assert_array_equal(para_utils.points, para_dronewq.points)

    def test_get_line_center(self):
        """Test get_line_center method"""
        # Line 0 connects points 0 and 1: (0,0) and (2,0)
        center_utils = self.parallelogram_utils.get_line_center(0)
        center_dronewq = self.parallelogram_dronewq.get_line_center(0)
        np.testing.assert_array_almost_equal(center_utils, center_dronewq)

    def test_get_line_center_all_lines(self):
        """Test get_line_center for all four lines"""
        for i in range(4):
            center_utils = self.parallelogram_utils.get_line_center(i)
            center_dronewq = self.parallelogram_dronewq.get_line_center(i)
            np.testing.assert_array_almost_equal(center_utils, center_dronewq)

    def test_get_offset_to_lines(self):
        """Test get_offset_to_lines method"""
        point = np.array([0, 0])
        offset_utils = self.parallelogram_utils.get_offset_to_lines(0, point)
        offset_dronewq = self.parallelogram_dronewq.get_offset_to_lines(0, point)
        np.testing.assert_array_almost_equal(offset_utils, offset_dronewq)

    def test_get_offset_to_lines_different_point(self):
        """Test get_offset_to_lines with different point"""
        point = np.array([1, 1])
        offset_utils = self.parallelogram_utils.get_offset_to_lines(2, point)
        offset_dronewq = self.parallelogram_dronewq.get_offset_to_lines(2, point)
        np.testing.assert_array_almost_equal(offset_utils, offset_dronewq)

    def test_get_center(self):
        """Test get_center method"""
        center_utils = self.parallelogram_utils.get_center()
        center_dronewq = self.parallelogram_dronewq.get_center()
        np.testing.assert_array_almost_equal(center_utils, center_dronewq)

    def test_move_line_from_offset(self):
        """Test move_line_from_offset method"""
        points_utils = self.points.copy()
        points_dronewq = self.points.copy()
        para_utils = utils.Paralelogram2D(points_utils)
        para_dronewq = DronewqParalelogram2D(points_dronewq)
        
        offset = np.array([1, 1])
        para_utils.move_line_from_offset(0, offset)
        para_dronewq.move_line_from_offset(0, offset)
        
        np.testing.assert_array_almost_equal(para_utils.points, para_dronewq.points)

    def test_move_line_from_offset_negative(self):
        """Test move_line_from_offset with negative offset"""
        points_utils = self.points.copy()
        points_dronewq = self.points.copy()
        para_utils = utils.Paralelogram2D(points_utils)
        para_dronewq = DronewqParalelogram2D(points_dronewq)
        
        offset = np.array([-2, -3])
        para_utils.move_line_from_offset(3, offset)
        para_dronewq.move_line_from_offset(3, offset)
        
        np.testing.assert_array_almost_equal(para_utils.points, para_dronewq.points)

    def test_are_on_right_side_of_line_true(self):
        """Test are_on_right_side_of_line when all points are on right side"""
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        para_utils = utils.Paralelogram2D(points.copy())
        para_dronewq = DronewqParalelogram2D(points.copy())

        test_points = np.array([[2, 0.5]])
        result_utils = para_utils.are_on_right_side_of_line(0, test_points)
        result_dronewq = para_dronewq.are_on_right_side_of_line(0, test_points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertIsInstance(result_utils, bool)

    def test_are_on_right_side_of_line_false(self):
        """Test are_on_right_side_of_line when not all points are on right side"""
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        para_utils = utils.Paralelogram2D(points.copy())
        para_dronewq = DronewqParalelogram2D(points.copy())

        test_points = np.array([[-1, 0.5], [2, 0.5]])
        result_utils = para_utils.are_on_right_side_of_line(0, test_points)
        result_dronewq = para_dronewq.are_on_right_side_of_line(0, test_points)
        self.assertEqual(result_utils, result_dronewq)
        self.assertIsInstance(result_utils, bool)

    def test_are_on_right_side_of_line_empty_list(self):
        """Test are_on_right_side_of_line with empty point list"""
        result_utils = self.parallelogram_utils.are_on_right_side_of_line(
            0, np.array([]).reshape(0, 2),
        )
        result_dronewq = self.parallelogram_dronewq.are_on_right_side_of_line(
            0, np.array([]).reshape(0, 2),
        )
        self.assertEqual(result_utils, result_dronewq)
        self.assertTrue(result_utils)  # all() of empty list is True


class TestParalelogram2DEdgeCases(unittest.TestCase):
    """Test edge cases comparing utils.Paralelogram2D to dronewq.Paralelogram2D"""

    def test_parallelogram_with_floats(self):
        """Test parallelogram with float coordinates"""
        points = np.array([[0.5, 0.5], [2.5, 0.5], [3.5, 1.5], [1.5, 1.5]])
        para_utils = utils.Paralelogram2D(points.copy())
        para_dronewq = DronewqParalelogram2D(points.copy())
        
        center_utils = para_utils.get_center()
        center_dronewq = para_dronewq.get_center()
        
        np.testing.assert_array_almost_equal(center_utils, center_dronewq)
        self.assertIsInstance(center_utils, np.ndarray)

    def test_parallelogram_with_negative_coords(self):
        """Test parallelogram with negative coordinates"""
        points = np.array([[-2, -2], [0, -2], [1, -1], [-1, -1]])
        para_utils = utils.Paralelogram2D(points.copy())
        para_dronewq = DronewqParalelogram2D(points.copy())
        
        center_utils = para_utils.get_center()
        center_dronewq = para_dronewq.get_center()
        
        np.testing.assert_array_almost_equal(center_utils, center_dronewq)
        self.assertIsInstance(center_utils, np.ndarray)

    def test_degenerate_parallelogram(self):
        """Test with collinear points (degenerate case)"""
        points = np.array([[0, 0], [1, 0], [2, 0], [3, 0]])
        para_utils = utils.Paralelogram2D(points.copy())
        para_dronewq = DronewqParalelogram2D(points.copy())
        
        center_utils = para_utils.get_center()
        center_dronewq = para_dronewq.get_center()
        
        np.testing.assert_array_almost_equal(center_utils, center_dronewq)
        self.assertIsInstance(center_utils, np.ndarray)


if __name__ == "__main__":
    unittest.main()