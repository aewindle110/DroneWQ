"""
Not much is changed from the original code
Refactored docstrings: Temuulen
"""
import numpy as np


class Paralelogram2D:
    """
    Represents a 2D parallelogram defined by four corner points.

    The class assumes the points are ordered consecutively around
    the shape. It automatically determines the line segments and
    opposite-line pairs.

    Parameters
    ----------
    points : np.ndarray (shape: (4, 2))
        Array of the four corner points of the parallelogram,
        ordered clockwise or counter-clockwise.
    """

    def __init__(self, points):
        self.points = points
        self.lines = [[0, 1], [1, 2], [2, 3], [3, 0]]
        self.pairs = [[0, 2], [1, 3]]

    def get_line_center(self, index):
        """
        Compute the midpoint of one of the parallelogram's edges.

        Parameters
        ----------
        index : int
            Index of the line segment in ``self.lines``.

        Returns
        -------
        np.ndarray (shape: (2,))
            The midpoint of the selected line.
        """
        return sum(self.points[self.lines[index]]) / 2

    def get_offset_to_lines(self, index, point):
        """
        Compute a vector pointing from a point toward the center
        of a specific edge.

        Parameters
        ----------
        index : int
            Line index.

        point : np.ndarray (shape: (2,))
            The reference point.

        Returns
        -------
        np.ndarray (shape: (2,))
            Direction vector pointing toward the line's midpoint.
        """
        return self.get_line_center(index) - point

    def get_center(self):
        """
        Compute the centroid of the parallelogram.

        Returns
        -------
        np.ndarray (shape: (2,))
            The center point of the parallelogram.
        """
        return get_center(self.points)

    def move_line_from_offset(self, index, offset):
        """
        Translate a line segment by a given offset vector.
        This moves the two points belonging to the line.

        Parameters
        ----------
        index : int
            Line index.

        offset : np.ndarray (shape: (2,))
            Offset vector applied to the line’s two endpoints.
        """
        self.points[self.lines[index]] += offset

    def are_on_right_side_of_line(self, index, points):
        """
        Check whether a list of points lies on the right side
        of the specified line segment.

        Parameters
        ----------
        index : int
            Line index.

        points : np.ndarray (shape: (N, 2))
            Points to test.

        Returns
        -------
        bool
            True if all points lie on the right side of the line,
            otherwise False.
        """
        return all(
            [
                is_on_right_side(*point, *self.points[self.lines[index]])
                for point in points
            ],
        )


def is_on_right_side(x, y, xy0, xy1):
    """
    Determine whether a point lies on the right side of a directed line.

    The line is interpreted as directed from ``xy0`` to ``xy1``.
    “Right side” is computed using the standard 2D line equation.

    Parameters
    ----------
    x, y : float
        Coordinates of the point to test.

    xy0, xy1 : Tuple[float, float]
        Two points defining the directed line segment.

    Returns
    -------
    bool
        True if the point is on the right side of the line,
        otherwise False.
    """
    x0, y0 = xy0
    x1, y1 = xy1
    a = float(y1 - y0)
    b = float(x0 - x1)
    c = -a * x0 - b * y0
    return a * x + b * y + c > 0


def is_point_within_vertices(x, y, vertices):
    """
    Check whether a point lies inside or on the boundary of a polygon.

    The polygon is defined by a list of vertices in order. The method
    checks whether the point lies consistently on the same side
    (all left or all right) of every polygon edge.

    Parameters
    ----------
    x, y : float
        Coordinates of the point to test.

    vertices : List[Tuple[float, float]]
        Ordered list of polygon vertices.

    Returns
    -------
    bool
        True if the point is inside or on the polygon boundary.
    """
    num_vert = len(vertices)
    is_right = [
        is_on_right_side(x, y, vertices[i], vertices[(i + 1) % num_vert])
        for i in range(num_vert)
    ]
    all_left = not any(is_right)
    all_right = all(is_right)
    return all_left or all_right


def are_points_within_vertices(vertices, points):
    """
    Check whether multiple points all lie inside a polygon.

    Parameters
    ----------
    vertices : List[Tuple[float, float]]
        Ordered polygon vertices.

    points : List[Tuple[float, float]] or np.ndarray
        Points to test.

    Returns
    -------
    bool
        True if every point is inside or on the polygon boundary.
    """
    all_points_in_merge = True

    for point in points:
        all_points_in_merge &= is_point_within_vertices(
            x=point[0],
            y=point[1],
            vertices=vertices,
        )

    return all_points_in_merge


def euclidean_distance(p1, p2):
    """
    Compute the 2D Euclidean distance between two points.

    Parameters
    ----------
    p1, p2 : Tuple[float, float]
        Input points.

    Returns
    -------
    float
        Euclidean distance.
    """
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_center(points):
    """
    Compute the centroid (mean point) of a list of 2D points.

    Parameters
    ----------
    points : np.ndarray (shape: (N, 2))
        Array of points.

    Returns
    -------
    np.ndarray (shape: (2,))
        The centroid of the points.
    """
    x = points[:, 0]
    y = points[:, 1]

    m_x = sum(x) / points.shape[0]
    m_y = sum(y) / points.shape[0]

    return np.array([m_x, m_y])
