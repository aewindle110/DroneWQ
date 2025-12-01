import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import os


class TestHedleySimple(unittest.TestCase):
    
    def setUp(self):
        """Setup common test data."""
        self.test_shape = (5, 50, 50)
        self.test_data = np.random.rand(*self.test_shape).astype(np.float32)
    
   
    def test_nir_calculation(self):
        """Test: NIR percentile calculation."""
        nir_band = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        percentile_val = np.percentile(nir_band, 0.1)
        self.assertLess(percentile_val, 0.2)
    
    def test_polynomial_slope(self):
        """Test: Polynomial returns correct slope."""
        from numpy.polynomial import Polynomial
        
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([2.0, 4.0, 6.0])  # slope = 2
        
        p = Polynomial.fit(x, y, 1)
        slope = p.convert().coef[1]
        
        self.assertAlmostEqual(slope, 2.0, places=2)
    
    def test_array_operations(self):
        """Test: Basic array operations work."""
        arr = np.random.rand(5, 10, 10)
        reshaped = arr.reshape(*arr.shape[:-2], -1)
        
        self.assertEqual(reshaped.shape, (5, 100))
        self.assertEqual(arr.shape[0], reshaped.shape[0])
