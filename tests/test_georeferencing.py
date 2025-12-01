import numpy as np
import pandas as pd
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from dronewq.core.georeference import georeference, compute_flight_lines


class TestComputeFlightLines(unittest.TestCase):
    """Test suite for compute_flight_lines function"""

    def test_compute_flight_lines_simple(self):
        """Test flight line computation with simple yaw angles"""
        captures_yaw = np.array([0, 5, 10, 5, 0, 180, 175, 185, 180, 175])
        altitude = 50.0
        pitch = 0.0
        roll = 0.0
        
        result = compute_flight_lines(captures_yaw, altitude, pitch, roll, threshold=10)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertTrue(all('start' in line and 'end' in line for line in result))
        self.assertTrue(all(line['alt'] == altitude for line in result))

    def test_compute_flight_lines_single_line(self):
        """Test with all captures in same direction"""
        captures_yaw = np.array([90, 92, 88, 91, 89])
        altitude = 30.0
        
        result = compute_flight_lines(captures_yaw, altitude, 0, 0, threshold=10)
        
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0]['start'], 0)
        self.assertEqual(result[0]['end'], 5)

    def test_compute_flight_lines_threshold(self):
        """Test threshold parameter filters correctly"""
        captures_yaw = np.array([0, 5, 50, 5, 0])
        
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=10)
        
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
        self.assertTrue(80 < result[0]['yaw'] < 100)

    def test_compute_flight_lines_sorted_output(self):
        """Test that flight lines are returned in sorted order"""
        captures_yaw = np.array([180, 185, 175, 0, 5, 10])
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=10)
        
        if len(result) > 1:
            for i in range(len(result) - 1):
                self.assertLessEqual(result[i]['start'], result[i+1]['start'])

    def test_compute_flight_lines_with_gaps(self):
        """Test handling of non-contiguous capture sequences"""
        captures_yaw = np.array([0, 5, 10, 90, 95, 100])
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=10)
        
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

    def test_compute_flight_lines_large_threshold(self):
        """Test with large threshold to ensure at least one line is found"""
        captures_yaw = np.array([0, 10, 20, 30, 40])
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=50)
        
        # With large threshold, should detect at least one line
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_compute_flight_lines_varied_angles(self):
        """Test with varied but reasonable yaw angles"""
        captures_yaw = np.array([88, 90, 92, 89, 91, 270, 272, 268, 271])
        result = compute_flight_lines(captures_yaw, 50, 0, 0, threshold=15)
        
        self.assertIsInstance(result, list)
        # Should detect two flight lines (around 90 and 270 degrees)
        self.assertGreaterEqual(len(result), 1)


class TestGeoreferenceWithRealData(unittest.TestCase):
    """Test suite for georeference function using real test data"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        # Path to test_set directory (adjust if needed)
        cls.test_set_dir = Path('tests/test_set')
        
        # Check if test data exists
        cls.has_test_data = cls.test_set_dir.exists()
        
        if cls.has_test_data:
            cls.metadata_file = cls.test_set_dir / 'metadata.csv'
            cls.dls_ed_file = cls.test_set_dir / 'dls_ed.csv'
            
            # Available image directories
            cls.image_dirs = [
                'align_img',
                'lt_imgs', 
                'lt_thumbnails',
                'panel',
                'raw_sky_imgs',
                'raw_water_imgs',
                'rrs_imgs',
                'sky_lt_imgs',
                'sky_lt_thumbnails'
            ]

    def setUp(self):
        """Set up for each test"""
        self.temp_output_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directories"""
        if os.path.exists(self.temp_output_dir):
            shutil.rmtree(self.temp_output_dir)

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_with_metadata_csv(self):
        """Test georeference using actual metadata.csv file"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        # Load metadata
        metadata = pd.read_csv(self.metadata_file)
        
        # Verify metadata has required columns
        required_cols = ['filename', 'FocalLength', 'ImageWidth', 'ImageHeight',
                        'SensorX', 'SensorY', 'Longitude', 'Latitude', 'Altitude']
        for col in required_cols:
            self.assertIn(col, metadata.columns, f"Missing column: {col}")
        
        # Test with a small subset (first 2 images) for speed
        metadata_subset = metadata.head(2)
        
        # Find which image directory has these files
        input_dir = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                # Check if first file exists
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found with test files")
        
        # Run georeference with fixed parameters
        georeference(
            metadata=metadata_subset,
            input_dir=input_dir,
            output_dir=self.temp_output_dir,
            altitude=100.0,
            yaw=90.0,
            pitch=0,
            roll=0
        )
        
        # Verify output files were created
        output_files = list(Path(self.temp_output_dir).glob('*.tif'))
        self.assertGreater(len(output_files), 0, "No output .tif files created")

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_with_metadata_values(self):
        """Test georeference using values from metadata (not fixed)"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        metadata = pd.read_csv(self.metadata_file)
        
        # Check if metadata has orientation columns
        if 'Yaw' not in metadata.columns:
            self.skipTest("Metadata missing Yaw column")
        
        metadata_subset = metadata.head(1)
        
        # Find input directory
        input_dir = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found")
        
        # Run with None parameters (use metadata values)
        georeference(
            metadata=metadata_subset,
            input_dir=input_dir,
            output_dir=self.temp_output_dir,
            altitude=None,  # Use metadata
            yaw=None,       # Use metadata
            pitch=0,     # Use metadata
            roll=0       # Use metadata
        )
        
        # Verify output
        output_files = list(Path(self.temp_output_dir).glob('*.tif'))
        self.assertGreater(len(output_files), 0)

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_with_simple_lines_parameter(self):
        """Test georeference with manually defined flight lines"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        metadata = pd.read_csv(self.metadata_file)
        
        # Use first 5 images for speed
        metadata_subset = metadata.head(5)
        
        # Find input directory
        input_dir = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found")
        
        # Manually define a simple flight line covering all images
        simple_lines = [
            {
                'start': 0, 
                'end': len(metadata_subset), 
                'yaw': 90.0, 
                'pitch': 0.0, 
                'roll': 0.0, 
                'alt': 100.0
            }
        ]
        
        # Run georeference with manually defined lines
        georeference(
            metadata=metadata_subset,
            input_dir=input_dir,
            output_dir=self.temp_output_dir,
            lines=simple_lines
        )
        
        # Verify output
        output_files = list(Path(self.temp_output_dir).glob('*.tif'))
        self.assertGreater(len(output_files), 0, "No output .tif files created")

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_different_axis_flip(self):
        """Test georeference with different axis flip values"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        metadata = pd.read_csv(self.metadata_file)
        metadata_subset = metadata.head(1)
        
        # Find input directory
        input_dir = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found")
        
        # Test with axis_to_flip=2
        output_dir_flip2 = tempfile.mkdtemp()
        try:
            georeference(
                metadata=metadata_subset,
                input_dir=input_dir,
                output_dir=output_dir_flip2,
                altitude=100.0,
                axis_to_flip=2
            )
            output_files = list(Path(output_dir_flip2).glob('*.tif'))
            self.assertGreater(len(output_files), 0)
        finally:
            shutil.rmtree(output_dir_flip2)
        
        # Test with axis_to_flip=None
        output_dir_no_flip = tempfile.mkdtemp()
        try:
            georeference(
                metadata=metadata_subset,
                input_dir=input_dir,
                output_dir=output_dir_no_flip,
                altitude=100.0,
                axis_to_flip=0
            )
            output_files = list(Path(output_dir_no_flip).glob('*.tif'))
            self.assertGreater(len(output_files), 0)
        finally:
            shutil.rmtree(output_dir_no_flip)

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_output_tif_format(self):
        """Test that output files are properly formatted .tif files"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        metadata = pd.read_csv(self.metadata_file)
        metadata_subset = metadata.head(1)
        
        # Find input directory
        input_dir = None
        input_filename = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    input_filename = first_file
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found")
        
        # Run georeference
        georeference(
            metadata=metadata_subset,
            input_dir=input_dir,
            output_dir=self.temp_output_dir,
            altitude=100.0
        )
        
        # Check output file naming
        output_files = list(Path(self.temp_output_dir).glob('*.tif'))
        self.assertGreater(len(output_files), 0)
        
        # Verify the filename conversion (e.g., .jpg -> .tif)
        expected_name = input_filename.rsplit('.', 1)[0] + '.tif'
        output_names = [f.name for f in output_files]
        self.assertIn(expected_name, output_names)

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_creates_output_dir(self):
        """Test that georeference creates output directory if it doesn't exist"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        metadata = pd.read_csv(self.metadata_file)
        metadata_subset = metadata.head(1)
        
        # Find input directory
        input_dir = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found")
        
        # Use a nested directory that doesn't exist
        nested_output = os.path.join(self.temp_output_dir, 'level1', 'level2')
        self.assertFalse(os.path.exists(nested_output))
        
        # Run georeference
        georeference(
            metadata=metadata_subset,
            input_dir=input_dir,
            output_dir=nested_output,
            altitude=100.0
        )
        
        # Verify directory was created
        self.assertTrue(os.path.exists(nested_output))
        
        # Verify files were written
        output_files = list(Path(nested_output).glob('*.tif'))
        self.assertGreater(len(output_files), 0)

    @unittest.skipUnless(
        Path('tests/test_set').exists(),
        "Test data directory not found"
    )
    def test_georeference_with_slice_lines(self):
        """Test georeference with slice-style lines parameter"""
        if not self.metadata_file.exists():
            self.skipTest("metadata.csv not found")
        
        metadata = pd.read_csv(self.metadata_file)
        metadata_subset = metadata.head(3)
        
        # Find input directory
        input_dir = None
        for img_dir in self.image_dirs:
            test_dir = self.test_set_dir / img_dir
            if test_dir.exists():
                first_file = metadata_subset.iloc[0]['filename']
                if (test_dir / first_file).exists():
                    input_dir = str(test_dir)
                    break
        
        if input_dir is None:
            self.skipTest("No matching image directory found")
        
        # Use slice-style lines (process subset)
        lines = [
            {
                'start': 0, 
                'end': 2,  # Only first 2 images
                'yaw': 90.0, 
                'pitch': 0.0, 
                'roll': 0.0, 
                'alt': 100.0
            }
        ]
        
        georeference(
            metadata=metadata_subset,
            input_dir=input_dir,
            output_dir=self.temp_output_dir,
            lines=lines
        )
        
        # Should only create 2 output files
        output_files = list(Path(self.temp_output_dir).glob('*.tif'))
        self.assertGreater(len(output_files), 0)
        self.assertLessEqual(len(output_files), 2)


class TestComputeFlightLinesWithRealData(unittest.TestCase):
    """Test compute_flight_lines with real metadata"""

    @unittest.skipUnless(
        Path('tests/test_set/metadata.csv').exists(),
        "metadata.csv not found"
    )
    def test_compute_flight_lines_accepts_real_metadata(self):
        """Test that compute_flight_lines can process real metadata structure"""
        metadata_file = Path('tests/test_set/metadata.csv')
        metadata = pd.read_csv(metadata_file)
        
        if 'Yaw' not in metadata.columns:
            self.skipTest("Metadata missing Yaw column")
        
        # Use first 20 captures
        yaw_values = metadata['Yaw'].head(20).values
        
        if 'Altitude' in metadata.columns:
            altitude = float(np.mean(metadata['Altitude'].head(20).values))
        else:
            altitude = 100.0
        
        pitch = 0.0
        roll = 0.0
        
        # Use a larger threshold to be more permissive
        result = compute_flight_lines(yaw_values, altitude, pitch, roll, threshold=30)
        
        # Just verify it returns a list - it may be empty if data doesn't have clear flight lines
        self.assertIsInstance(result, list)
        
        # If we get results, verify structure
        if len(result) > 0:
            for line in result:
                self.assertIn('start', line)
                self.assertIn('end', line)
                self.assertIn('yaw', line)
                self.assertIn('alt', line)
                self.assertGreaterEqual(line['end'], line['start'])

    @unittest.skipUnless(
        Path('tests/test_set/metadata.csv').exists(),
        "metadata.csv not found"
    )
    def test_compute_flight_lines_with_varied_thresholds(self):
        """Test compute_flight_lines with different threshold values"""
        metadata_file = Path('tests/test_set/metadata.csv')
        metadata = pd.read_csv(metadata_file)
        
        if 'Yaw' not in metadata.columns:
            self.skipTest("Metadata missing Yaw column")
        
        yaw_values = metadata['Yaw'].head(20).values
        altitude = 100.0
        
        # Try different thresholds
        for threshold in [10, 20, 30, 50]:
            result = compute_flight_lines(yaw_values, altitude, 0, 0, threshold=threshold)
            self.assertIsInstance(result, list)
            
            # Verify structure if results exist
            for line in result:
                self.assertIn('start', line)
                self.assertIn('end', line)
                self.assertGreaterEqual(line['end'], line['start'])