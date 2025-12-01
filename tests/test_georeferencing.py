import unittest
import tempfile
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).parent.resolve()                    # tests/
TEST_SET_DIR = THIS_DIR / "test_set"
METADATA_FILE = TEST_SET_DIR / "metadata.csv"

# Temporary output directory inside test_set (will be cleaned up)
OUTPUT_DIR = TEST_SET_DIR / "georeference_temp"
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(exist_ok=True)

from dronewq.utils import settings as drone_settings

_original_settings = drone_settings.settings

class TestSettings:
    main_dir = str(TEST_SET_DIR)
    # Not strictly needed for georeference, but keeps everything consistent
    metadata_dir = str(TEST_SET_DIR)
    rrs_dir = str(TEST_SET_DIR / "rrs_imgs")  # just in case

drone_settings.settings = TestSettings()

from dronewq.core.georeference import georeference, compute_flight_lines


class TestComputeFlightLines(unittest.TestCase):
    """Test suite for compute_flight_lines function"""
    def test_compute_flight_lines_simple(self):
        captures_yaw = np.array([0, 5, 10, 5, 0, 180, 175, 185, 180, 175])
        result = compute_flight_lines(captures_yaw, 50.0, 0, 0, threshold=10)
        self.assertEqual(len(result), 2)

    def test_compute_flight_lines_single_line(self):
        captures_yaw = np.array([90, 92, 88, 91, 89])
        result = compute_flight_lines(captures_yaw, 30.0, 0, 0, threshold=10)
        self.assertEqual(result[0]['start'], 0)
        self.assertEqual(result[0]['end'], 5)

    def test_compute_flight_lines_output_structure(self):
        captures_yaw = np.array([0, 10, 20])
        result = compute_flight_lines(captures_yaw, 100, -5, 2, threshold=15)
        for line in result:
            self.assertIn('start', line)
            self.assertIn('end', line)
            self.assertIn('yaw', line)
            self.assertIn('pitch', line)
            self.assertIn('roll', line)
            self.assertIn('alt', line)
            self.assertGreater(line['end'], line['start'])


@unittest.skipUnless(METADATA_FILE.exists(), "test_set/metadata.csv not found")
class TestGeoreferenceWithRealData(unittest.TestCase):
    """Test suite for georeference function using real test_set data"""

    @classmethod
    def setUpClass(cls):
        cls.metadata = pd.read_csv(METADATA_FILE)

        # Find any folder that contains the first filename
        first_file = cls.metadata.iloc[0]['filename']
        cls.input_dir = None
        image_folders = [
            'align_img', 'lt_imgs', 'raw_sky_imgs', 'raw_water_imgs',
            'rrs_imgs', 'sky_lt_imgs', 'panel'
        ]
        for folder in image_folders:
            path = TEST_SET_DIR / folder / first_file
            if path.exists():
                cls.input_dir = str(TEST_SET_DIR / folder)
                break
        if cls.input_dir is None:
            raise FileNotFoundError("No folder contains the test images")

    def setUp(self):
        # Fresh temp folder for each test
        self.temp_dir = tempfile.mkdtemp(dir=TEST_SET_DIR)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_georeference_fixed_parameters(self):
        subset = self.metadata.head(2)
        georeference(
            metadata=subset,
            input_dir=self.input_dir,
            output_dir=self.temp_dir,
            altitude=100.0,
            yaw=90.0,
            pitch=0,
            roll=0
        )
        outputs = list(Path(self.temp_dir).glob("*.tif"))
        self.assertEqual(len(outputs), len(subset))

    def test_georeference_use_metadata_values(self):
        subset = self.metadata.head(1)
        georeference(
            metadata=subset,
            input_dir=self.input_dir,
            output_dir=self.temp_dir,
            altitude=None,
            yaw=None,
            pitch=0,
            roll=0
        )
        outputs = list(Path(self.temp_dir).glob("*.tif"))
        self.assertGreater(len(outputs), 0)

    def test_georeference_with_simple_lines(self):
        subset = self.metadata.head(3)
        lines = [{
            'start': 0,
            'end': len(subset),
            'yaw': 90.0,
            'pitch': 0.0,
            'roll': 0.0,
            'alt': 100.0
        }]
        georeference(
            metadata=subset,
            input_dir=self.input_dir,
            output_dir=self.temp_dir,
            lines=lines
        )
        outputs = list(Path(self.temp_dir).glob("*.tif"))
        self.assertEqual(len(outputs), len(subset))

    def test_georeference_axis_flip(self):
        subset = self.metadata.head(1)
        georeference(
            metadata=subset,
            input_dir=self.input_dir,
            output_dir=self.temp_dir,
            altitude=100.0,
            axis_to_flip=2
        )
        self.assertGreater(len(list(Path(self.temp_dir).glob("*.tif"))), 0)

    def test_georeference_creates_nested_dir(self):
        subset = self.metadata.head(1)
        nested = str(Path(self.temp_dir) / "nested" / "output")
        georeference(
            metadata=subset,
            input_dir=self.input_dir,
            output_dir=nested,
            altitude=100.0
        )
        self.assertTrue(Path(nested).exists())
        self.assertGreater(len(list(Path(nested).glob("*.tif"))), 0)

@unittest.skipUnless(METADATA_FILE.exists(), "test_set/metadata.csv not found")
class TestComputeFlightLinesWithRealData(unittest.TestCase):

    def setUp(self):
        metadata = pd.read_csv(METADATA_FILE)
        self.yaw = metadata['Yaw'].head(20).values
        self.altitude = metadata['Altitude'].head(20).mean() if 'Altitude' in metadata.columns else 100.0

    def test_compute_flight_lines_real_data(self):
        result = compute_flight_lines(self.yaw, self.altitude, 0, 0, threshold=30)
        self.assertIsInstance(result, list)
        for line in result:
            self.assertGreaterEqual(line['end'], line['start'])

    def test_different_thresholds(self):
        for threshold in [10, 20, 30, 50]:
            result = compute_flight_lines(self.yaw, self.altitude, 0, 0, threshold=threshold)
            self.assertIsInstance(result, list)

def tearDownModule():
    shutil.rmtree(OUTPUT_DIR)
    drone_settings.settings = _original_settings  # restore original settings
