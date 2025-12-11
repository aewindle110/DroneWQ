# Author: Temuulen and Kurtis

import numpy as np
import unittest
from dronewq.core.georeference import georeference, compute_flight_lines


class TestComputeFlightLines(unittest.TestCase):
    """Test suite for compute_flight_lines function"""

    def test_compute_flight_lines_simple(self):
        """Test flight line computation with simple yaw angles"""
        # Simple case: two clear flight lines in opposite directions
        captures_yaw = np.array([0, 5, 10, 5, 0,  # first line facing ~0 degrees
                                 180, 175, 185, 180, 175])  # second line facing ~180 degrees
        altitude = 50.0
        pitch = 0.0
        roll = 0.0
        
        result = compute_flight_lines(captures_yaw, altitude, pitch, roll, threshold=10)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # Should detect 2 flight lines
        self.assertTrue(all('start' in line and 'end' in line for line in result))
        self.assertTrue(all(line['alt'] == altitude for line in result))
        self.assertTrue(all(line['pitch'] == pitch for line in result))
        self.assertTrue(all(line['roll'] == roll for line in result))

    def test_compute_flight_lines_single_line(self):
        """Test with all captures in same direction"""
        captures_yaw = np.array([90, 92, 88, 91, 89])  # all facing ~90 degrees
        altitude = 30.0
        
        result = compute_flight_lines(captures_yaw, altitude, 0, 0, threshold=10)
        
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0]['start'], 0)
        self.assertEqual(result[0]['end'], 5)

    def test_compute_flight_lines_threshold(self):
        """Test threshold parameter filters correctly"""
        captures_yaw = np.array([0, 5, 50, 5, 0])  # middle capture is outlier
        
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=10)
        
        # With threshold=10, the 50-degree capture should be filtered out
        # Should result in gaps/multiple lines or filtered captures
        self.assertIsInstance(result, list)

    def test_compute_flight_lines_output_structure(self):
        """Test that output has correct dictionary structure"""
        captures_yaw = np.array([0, 10, 20])
        result = compute_flight_lines(captures_yaw, 100, -5, 2, threshold=15)
        
        for line in result:
            self.assertIn('start', line)
            self.assertIn('end', line)
            self.assertIn('yaw', line)
            self.assertIn('pitch', line)
            self.assertIn('roll', line)
            self.assertIn('alt', line)
            self.assertIsInstance(line['start'], int)
            self.assertIsInstance(line['end'], int)
            self.assertIsInstance(line['yaw'], float)
            self.assertGreater(line['end'], line['start'])

    def test_compute_flight_lines_empty_array(self):
        """Test with minimal data"""
        captures_yaw = np.array([0])
        result = compute_flight_lines(captures_yaw, 50, 0, 0)
        self.assertIsInstance(result, list)

    def test_compute_flight_lines_two_captures(self):
        """Test with only 2 captures"""
        captures_yaw = np.array([0, 180])
        result = compute_flight_lines(captures_yaw, 50, 0, 0)
        self.assertIsInstance(result, list)

    def test_compute_flight_lines_parameter_propagation(self):
        """Test that parameters are correctly propagated to output"""
        captures_yaw = np.array([45, 50, 55])
        altitude = 75.5
        pitch = -10.0
        roll = 5.0
        
        result = compute_flight_lines(captures_yaw, altitude, pitch, roll, threshold=20)
        
        self.assertGreater(len(result), 0)
        for line in result:
            self.assertEqual(line['alt'], altitude)
            self.assertEqual(line['pitch'], pitch)
            self.assertEqual(line['roll'], roll)

    def test_compute_flight_lines_yaw_median(self):
        """Test that yaw values are computed as medians"""
        captures_yaw = np.array([85, 90, 95, 90, 88])
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=10)
        
        self.assertGreater(len(result), 0)
        # The yaw should be around the median of the input yaw values
        self.assertTrue(80 < result[0]['yaw'] < 100)

    def test_compute_flight_lines_sorted_output(self):
        """Test that flight lines are returned in sorted order"""
        captures_yaw = np.array([180, 185, 175, 0, 5, 10])
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=10)
        
        if len(result) > 1:
            for i in range(len(result) - 1):
                self.assertLessEqual(result[i]['start'], result[i+1]['start'])


if __name__ == '__main__':
    unittest.main()