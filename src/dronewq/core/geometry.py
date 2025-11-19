import numpy as np

class Paralelogram2D:
    """This class represents a paralelogram"""

    def __init__(self, points):
        """
        This constructor receives a list of points and sets the pairs of lines

        Parameters
            points (List[Tuple[float, float]]): list of corner points that determinate a paralelogram
        """
        self.points = points
        self.lines = [[0, 1], [1, 2], [2, 3], [3, 0]]
        self.pairs = [[0, 2], [1, 3]]

    def get_line_center(self, index):
        """
        This functions returns the center of a specific line of the paralelogram

        Parameters
            index (int): line index

        Returns
            np.ndarray: center
        """
        return sum(self.points[self.lines[index]]) / 2

    def get_offset_to_lines(self, index, point):
        """
        This functions returns a Vector that represents what should be direction of point for being in the specified line

        Parameters
            index (int): line index

            point (np.ndarray): point

        Returns
            np.ndarray: direction vector
        """
        return self.get_line_center(index) - point

    def get_center(self):
        """
        This function returns the center of the paralelogram

        Returns:
            np.ndarray: center
        """
        return get_center(self.points)

    def move_line_from_offset(self, index, offset):
        """
        This function moves a specific line given an offset vector

        Parameters
            index (int): line index

            offset (np.ndarray): offset vector
        """
        self.points[self.lines[index]] += offset

    def are_on_right_side_of_line(self, index, points):
        """
        This function checks if a list of points is on the right side of a specific line

        Parameters
            index (int): line index

            points (np.ndarray): a list of points

        Returns
            bool: whether the list is on the right side or not
        """
        return all(
            [
                is_on_right_side(*point, *self.points[self.lines[index]])
                for point in points
            ],
        )


def is_on_right_side(x, y, xy0, xy1):
    """
    Given a point and 2 points defining a rect, check if the point is on the right side or not.

    Parameters
        x (float): value in the x-axis of the point

        y (float): value in the y-axis of the point

        xy0 (Tuple[float, float]): point 0 of the rect

        xy1 (Tuple[float, float]): point 1 of the rect

    Returns
        bool: is on right side or not
    """
    x0, y0 = xy0
    x1, y1 = xy1
    a = float(y1 - y0)
    b = float(x0 - x1)
    c = -a * x0 - b * y0
    return a * x + b * y + c > 0


def is_point_within_vertices(x, y, vertices):
    """
    This fuction checks if a point is within the given vertices

    Parameters
        x (float): value in the width axis for the point

        y (float): value in the height axis for the point

        vertices (List[Tuple[float, float]]): bounding vertices

    Returns
        bool: whether the point is within the vertices or not
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
    Given a list of vertices and a list of points,
    generate every rect determined by the vertices
    and check if the points are within the polygon or not.

    Parameters
        vertices (List[Tuple[float, float]]): List of vertices defining a polygon
        points (List[Tuple[float, float]]): List of points to study is they are within the polygon or not

    Returns
        bool: the given points are within the given vertices or not
    """
    all_points_in_merge = True

    for point in points:
        all_points_in_merge &= is_point_within_vertices(
            x=point[0], y=point[1], vertices=vertices,
        )

    return all_points_in_merge


def euclidean_distance(p1, p2):
    """
    Euclidean distance between two points

    Parameters
        p1 (Tuple[float, float]): 2D point 1

        p2 (Tuple[float, float]): 2D point 2

    Returns
        float: euclidean distance between two points
    """
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_center(points):
    """
    This function receives a list of points and returns
    the point at the center of all points

    Parameters
        points (np.ndarray): a list of points

    Returns
        np.ndarray: center of all points
    """
    x = points[:, 0]
    y = points[:, 1]

    m_x = sum(x) / points.shape[0]
    m_y = sum(y) / points.shape[0]

    return np.array([m_x, m_y])
