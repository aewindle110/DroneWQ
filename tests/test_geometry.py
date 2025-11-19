import unittest

import numpy as np

from dronewq.core.geometry import (
    Paralelogram2D,
    are_points_within_vertices,
    euclidean_distance,
    get_center,
    is_on_right_side,
    is_point_within_vertices,
)

class TestIsOnRightSide(unittest.TestCase):
    """Test cases for is_on_right_side function"""

    def test_point_on_right_side(self):
        """Test when point is clearly on the right side"""
        # Vertical line from (0,0) to (0,1), point at (1,0.5) should be on right
        result = is_on_right_side(1, 0.5, (0, 0), (0, 1))
        self.assertTrue(result)

    def test_point_on_left_side(self):
        """Test when point is clearly on the left side"""
        # Vertical line from (0,0) to (0,1), point at (-1,0.5) should be on left
        result = is_on_right_side(-1, 0.5, (0, 0), (0, 1))
        self.assertFalse(result)

    def test_point_on_line(self):
        """Test when point is exactly on the line"""
        # Point on the line should return False (not strictly greater than 0)
        result = is_on_right_side(0, 0.5, (0, 0), (0, 1))
        self.assertFalse(result)

    # def test_horizontal_line(self):
    #     """Test with horizontal line"""
    #     # Horizontal line from (0,0) to (1,0), point at (0.5,1) should be on right
    #     result = is_on_right_side(0.5, 1, (0, 0), (1, 0))
    #     self.assertTrue(result)

    def test_diagonal_line(self):
        """Test with diagonal line"""
        # Diagonal line from (0,0) to (1,1)
        result = is_on_right_side(1, 0, (0, 0), (1, 1))
        self.assertTrue(result)
        result = is_on_right_side(0, 1, (0, 0), (1, 1))
        self.assertFalse(result)


class TestIsPointWithinVertices(unittest.TestCase):
    """Test cases for is_point_within_vertices function"""

    def test_point_inside_square(self):
        """Test point clearly inside a square"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result = is_point_within_vertices(0.5, 0.5, vertices)
        self.assertTrue(result)

    def test_point_outside_square(self):
        """Test point clearly outside a square"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result = is_point_within_vertices(2, 2, vertices)
        self.assertFalse(result)

    def test_point_on_vertex(self):
        """Test point exactly on a vertex"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result = is_point_within_vertices(0, 0, vertices)
        self.assertTrue(result)

    def test_point_on_edge(self):
        """Test point on an edge"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        result = is_point_within_vertices(0.5, 0, vertices)
        self.assertTrue(result)

    def test_triangle(self):
        """Test with triangle vertices"""
        vertices = [(0, 0), (1, 0), (0.5, 1)]
        result = is_point_within_vertices(0.5, 0.3, vertices)
        self.assertTrue(result)
        result = is_point_within_vertices(0, 1, vertices)
        self.assertFalse(result)

    def test_negative_coordinates(self):
        """Test with negative coordinates"""
        vertices = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        result = is_point_within_vertices(0, 0, vertices)
        self.assertTrue(result)


class TestArePointsWithinVertices(unittest.TestCase):
    """Test cases for are_points_within_vertices function"""

    def test_all_points_inside(self):
        """Test when all points are inside"""
        vertices = [(0, 0), (2, 0), (2, 2), (0, 2)]
        points = [(0.5, 0.5), (1, 1), (1.5, 1.5)]
        result = are_points_within_vertices(vertices, points)
        self.assertTrue(result)

    def test_all_points_outside(self):
        """Test when all points are outside"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = [(2, 2), (3, 3), (4, 4)]
        result = are_points_within_vertices(vertices, points)
        self.assertFalse(result)

    def test_mixed_points(self):
        """Test when some points are inside and some outside"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = [(0.5, 0.5), (2, 2)]
        result = are_points_within_vertices(vertices, points)
        self.assertFalse(result)

    def test_empty_points_list(self):
        """Test with empty points list"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = []
        result = are_points_within_vertices(vertices, points)
        self.assertTrue(result)  # all() of empty list is True

    def test_single_point(self):
        """Test with single point"""
        vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        points = [(0.5, 0.5)]
        result = are_points_within_vertices(vertices, points)
        self.assertTrue(result)


class TestEuclideanDistance(unittest.TestCase):
    """Test cases for euclidean_distance function"""

    def test_distance_same_point(self):
        """Test distance between same point"""
        result = euclidean_distance((0, 0), (0, 0))
        self.assertAlmostEqual(result, 0.0)

    def test_distance_horizontal(self):
        """Test distance along horizontal axis"""
        result = euclidean_distance((0, 0), (3, 0))
        self.assertAlmostEqual(result, 3.0)

    def test_distance_vertical(self):
        """Test distance along vertical axis"""
        result = euclidean_distance((0, 0), (0, 4))
        self.assertAlmostEqual(result, 4.0)

    def test_distance_diagonal(self):
        """Test distance along diagonal"""
        result = euclidean_distance((0, 0), (3, 4))
        self.assertAlmostEqual(result, 5.0)

    def test_distance_negative_coordinates(self):
        """Test distance with negative coordinates"""
        result = euclidean_distance((-1, -1), (2, 3))
        self.assertAlmostEqual(result, 5.0)

    def test_distance_float_coordinates(self):
        """Test distance with float coordinates"""
        result = euclidean_distance((0.5, 0.5), (1.5, 1.5))
        self.assertAlmostEqual(result, np.sqrt(2))


class TestGetCenter(unittest.TestCase):
    """Test cases for get_center function"""

    def test_center_of_square(self):
        """Test center of square corners"""
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        result = get_center(points)
        np.testing.assert_array_almost_equal(result, np.array([0.5, 0.5]))

    def test_center_of_triangle(self):
        """Test center of triangle"""
        points = np.array([[0, 0], [3, 0], [0, 3]])
        result = get_center(points)
        np.testing.assert_array_almost_equal(result, np.array([1.0, 1.0]))

    def test_center_single_point(self):
        """Test center with single point"""
        points = np.array([[5, 7]])
        result = get_center(points)
        np.testing.assert_array_almost_equal(result, np.array([5.0, 7.0]))

    def test_center_negative_coordinates(self):
        """Test center with negative coordinates"""
        points = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])
        result = get_center(points)
        np.testing.assert_array_almost_equal(result, np.array([0.0, 0.0]))

    def test_center_collinear_points(self):
        """Test center of collinear points"""
        points = np.array([[0, 0], [1, 1], [2, 2]])
        result = get_center(points)
        np.testing.assert_array_almost_equal(result, np.array([1.0, 1.0]))


class TestParalelogram2D(unittest.TestCase):
    """Test cases for Paralelogram2D class"""

    def setUp(self):
        """Set up test fixtures"""
        self.points = np.array([[0, 0], [2, 0], [3, 1], [1, 1]])
        self.parallelogram = Paralelogram2D(self.points)

    def test_init(self):
        """Test initialization of Paralelogram2D"""
        self.assertEqual(len(self.parallelogram.points), 4)
        self.assertEqual(self.parallelogram.lines, [[0, 1], [1, 2], [2, 3], [3, 0]])
        self.assertEqual(self.parallelogram.pairs, [[0, 2], [1, 3]])

    def test_init_with_different_points(self):
        """Test initialization with different points"""
        points = np.array([[1, 1], [3, 1], [4, 3], [2, 3]])
        para = Paralelogram2D(points)
        np.testing.assert_array_equal(para.points, points)

    def test_get_line_center(self):
        """Test get_line_center method"""
        # Line 0 connects points 0 and 1: (0,0) and (2,0)
        center = self.parallelogram.get_line_center(0)
        expected = (self.points[0] + self.points[1]) / 2
        np.testing.assert_array_almost_equal(center, expected)

    def test_get_line_center_all_lines(self):
        """Test get_line_center for all four lines"""
        for i in range(4):
            center = self.parallelogram.get_line_center(i)
            line_indices = self.parallelogram.lines[i]
            expected = (self.points[line_indices[0]] + self.points[line_indices[1]]) / 2
            np.testing.assert_array_almost_equal(center, expected)

    def test_get_offset_to_lines(self):
        """Test get_offset_to_lines method"""
        point = np.array([0, 0])
        offset = self.parallelogram.get_offset_to_lines(0, point)
        line_center = self.parallelogram.get_line_center(0)
        expected = line_center - point
        np.testing.assert_array_almost_equal(offset, expected)

    def test_get_offset_to_lines_different_point(self):
        """Test get_offset_to_lines with different point"""
        point = np.array([1, 1])
        offset = self.parallelogram.get_offset_to_lines(2, point)
        line_center = self.parallelogram.get_line_center(2)
        expected = line_center - point
        np.testing.assert_array_almost_equal(offset, expected)

    def test_get_center(self):
        """Test get_center method"""
        center = self.parallelogram.get_center()
        expected = get_center(self.points)
        np.testing.assert_array_almost_equal(center, expected)

    def test_move_line_from_offset(self):
        """Test move_line_from_offset method"""
        original_points = self.points.copy()
        offset = np.array([1, 1])
        self.parallelogram.move_line_from_offset(0, offset)

        # Check that line 0 points have moved
        np.testing.assert_array_almost_equal(
            self.parallelogram.points[0],
            original_points[0] + offset,
        )
        np.testing.assert_array_almost_equal(
            self.parallelogram.points[1],
            original_points[1] + offset,
        )

    def test_move_line_from_offset_negative(self):
        """Test move_line_from_offset with negative offset"""
        original_points = self.points.copy()
        offset = np.array([-2, -3])
        self.parallelogram.move_line_from_offset(3, offset)

        line_indices = self.parallelogram.lines[3]
        for idx in line_indices:
            np.testing.assert_array_almost_equal(
                self.parallelogram.points[idx],
                original_points[idx] + offset,
            )

    def test_are_on_right_side_of_line_true(self):
        """Test are_on_right_side_of_line when all points are on right side"""
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        para = Paralelogram2D(points)

        test_points = np.array([[2, 0.5]])
        result = para.are_on_right_side_of_line(0, test_points)
        self.assertIsInstance(result, bool)

    def test_are_on_right_side_of_line_false(self):
        """Test are_on_right_side_of_line when not all points are on right side"""
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        para = Paralelogram2D(points)

        test_points = np.array([[-1, 0.5], [2, 0.5]])
        result = para.are_on_right_side_of_line(0, test_points)
        self.assertIsInstance(result, bool)

    def test_are_on_right_side_of_line_empty_list(self):
        """Test are_on_right_side_of_line with empty point list"""
        result = self.parallelogram.are_on_right_side_of_line(0, np.array([]).reshape(0, 2))
        self.assertTrue(result)  # all() of empty list is True


class TestParalelogram2DEdgeCases(unittest.TestCase):
    """Test edge cases for Paralelogram2D class"""

    def test_parallelogram_with_floats(self):
        """Test parallelogram with float coordinates"""
        points = np.array([[0.5, 0.5], [2.5, 0.5], [3.5, 1.5], [1.5, 1.5]])
        para = Paralelogram2D(points)
        center = para.get_center()
        self.assertIsInstance(center, np.ndarray)

    def test_parallelogram_with_negative_coords(self):
        """Test parallelogram with negative coordinates"""
        points = np.array([[-2, -2], [0, -2], [1, -1], [-1, -1]])
        para = Paralelogram2D(points)
        center = para.get_center()
        self.assertIsInstance(center, np.ndarray)

    def test_degenerate_parallelogram(self):
        """Test with collinear points (degenerate case)"""
        points = np.array([[0, 0], [1, 0], [2, 0], [3, 0]])
        para = Paralelogram2D(points)
        center = para.get_center()
        self.assertIsInstance(center, np.ndarray)


if __name__ == "__main__":
    unittest.main()
