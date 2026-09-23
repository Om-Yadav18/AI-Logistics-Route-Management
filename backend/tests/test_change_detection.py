import os
import sys
import shutil
import tempfile
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_bounds

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.change_detection import SARChangeDetector


class TestChangeDetection(unittest.TestCase):
    """Unit tests for SARChangeDetector service and flood candidate detection."""

    def setUp(self):
        self.detector = SARChangeDetector(
            default_water_threshold_db=-16.0,
            default_change_threshold_db=-4.0,
            default_min_region_pixels=5,
        )
        self.test_dir = tempfile.mkdtemp()
        self.bbox = (91.50, 26.00, 92.00, 26.50)
        self.width = 64
        self.height = 64

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_test_raster(self, filepath: str, data: np.ndarray, width: int = 64, height: int = 64, crs: str = "EPSG:4326") -> str:
        """Helper to create a synthetic Float32 GeoTIFF."""
        transform = from_bounds(self.bbox[0], self.bbox[1], self.bbox[2], self.bbox[3], width, height)
        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(data.astype(np.float32), 1)
        return filepath

    def test_01_db_conversion(self):
        """Test 1: Verify mathematical accuracy of linear to dB conversion."""
        linear_vals = np.array([[0.01, 0.1], [1.0, 0.001]], dtype=np.float32)
        db_vals = self.detector.linear_to_db(linear_vals)
        
        self.assertAlmostEqual(db_vals[0, 0], -20.0, places=3)
        self.assertAlmostEqual(db_vals[0, 1], -10.0, places=3)
        self.assertAlmostEqual(db_vals[1, 0], 0.0, places=3)
        self.assertAlmostEqual(db_vals[1, 1], -30.0, places=3)

    def test_02_zero_and_invalid_values(self):
        """Test 2: Verify zero, negative, and NaN values are safely handled without errors."""
        invalid_vals = np.array([[0.0, -1.0], [np.nan, np.inf]], dtype=np.float32)
        db_vals = self.detector.linear_to_db(invalid_vals)
        
        # Non-positive/non-finite should result in NaN or clipped values
        self.assertTrue(np.isnan(db_vals[0, 0]))
        self.assertTrue(np.isnan(db_vals[0, 1]))
        self.assertTrue(np.isnan(db_vals[1, 0]))
        self.assertTrue(np.isnan(db_vals[1, 1]))

    def test_03_significant_new_water_detection(self):
        """Test 3: Verify region changing from dry (-10 dB) to flood (-18 dB) is detected."""
        # Linear equivalent: -10 dB = 0.1, -18 dB ≈ 0.0158
        b_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        e_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        
        # Create a 10x10 flooded patch in event image
        e_data[20:30, 20:30] = 0.0158
        
        b_path = os.path.join(self.test_dir, "b3.tif")
        e_path = os.path.join(self.test_dir, "e3.tif")
        self._create_test_raster(b_path, b_data)
        self._create_test_raster(e_path, e_data)

        result = self.detector.detect_changes(b_path, e_path, water_threshold_db=-16.0, change_threshold_db=-4.0)
        
        self.assertGreater(len(result["features"]), 0)
        self.assertGreater(result["metadata"]["summary"]["candidate_pixels"], 50)
        self.assertEqual(result["features"][0]["properties"]["hazard_type"], "flood_candidate")

    def test_04_permanent_water_rejection(self):
        """Test 4: Verify permanent water (-20 dB in both scenes) is NOT detected as new flood."""
        # Both images have a permanent water channel (0.01 ≈ -20 dB)
        b_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        e_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        b_data[10:25, :] = 0.01
        e_data[10:25, :] = 0.01

        b_path = os.path.join(self.test_dir, "b4.tif")
        e_path = os.path.join(self.test_dir, "e4.tif")
        self._create_test_raster(b_path, b_data)
        self._create_test_raster(e_path, e_data)

        result = self.detector.detect_changes(b_path, e_path, water_threshold_db=-16.0, change_threshold_db=-4.0)
        
        # Permanent river should produce 0 flood candidate features
        self.assertEqual(len(result["features"]), 0)
        self.assertEqual(result["metadata"]["summary"]["candidate_pixels"], 0)

    def test_05_insufficient_change_rejection(self):
        """Test 5: Verify slight change (-10 dB to -12 dB, drop -2 dB) does not trigger detection."""
        b_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)       # -10 dB
        e_data = np.full((self.height, self.width), fill_value=0.063, dtype=np.float32)     # -12 dB (not water and drop only -2 dB)

        b_path = os.path.join(self.test_dir, "b5.tif")
        e_path = os.path.join(self.test_dir, "e5.tif")
        self._create_test_raster(b_path, b_data)
        self._create_test_raster(e_path, e_data)

        result = self.detector.detect_changes(b_path, e_path, water_threshold_db=-16.0, change_threshold_db=-4.0)
        self.assertEqual(len(result["features"]), 0)

    def test_06_isolated_noise_removal(self):
        """Test 6: Verify small clusters (< min_region_pixels) are removed by region filtering."""
        # Direct unit test of filter_small_regions
        raw_mask = np.zeros((20, 20), dtype=bool)
        raw_mask[2:5, 2:5] = True  # 9 pixels cluster
        filtered_mask, removed_count = self.detector.filter_small_regions(raw_mask, min_pixels=15)
        self.assertEqual(np.sum(filtered_mask), 0)
        self.assertEqual(removed_count, 9)

        # Pipeline test
        b_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        e_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        
        # Create a small 3x3 patch that survives 3x3 median filter but is < min_region_pixels (e.g. 15)
        e_data[15:18, 15:18] = 0.01

        b_path = os.path.join(self.test_dir, "b6.tif")
        e_path = os.path.join(self.test_dir, "e6.tif")
        self._create_test_raster(b_path, b_data)
        self._create_test_raster(e_path, e_data)

        result = self.detector.detect_changes(b_path, e_path, min_region_pixels=15)
        self.assertEqual(len(result["features"]), 0)
        self.assertGreater(result["metadata"]["summary"]["removed_noise_pixels"], 0)

    def test_07_raster_mismatch_error(self):
        """Test 7: Verify mismatched dimensions raise a clear ValueError."""
        b_data = np.full((64, 64), fill_value=0.1, dtype=np.float32)
        e_data = np.full((32, 32), fill_value=0.1, dtype=np.float32)

        b_path = os.path.join(self.test_dir, "b7.tif")
        e_path = os.path.join(self.test_dir, "e7.tif")
        self._create_test_raster(b_path, b_data, width=64, height=64)
        self._create_test_raster(e_path, e_data, width=32, height=32)

        with self.assertRaises(ValueError):
            self.detector.detect_changes(b_path, e_path)

    def test_08_geojson_structure(self):
        """Test 8: Verify GeoJSON FeatureCollection structure and properties."""
        b_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        e_data = np.full((self.height, self.width), fill_value=0.1, dtype=np.float32)
        e_data[10:20, 10:20] = 0.01

        b_path = os.path.join(self.test_dir, "b8.tif")
        e_path = os.path.join(self.test_dir, "e8.tif")
        self._create_test_raster(b_path, b_data)
        self._create_test_raster(e_path, e_data)

        result = self.detector.detect_changes(b_path, e_path)
        self.assertEqual(result["type"], "FeatureCollection")
        self.assertIn("features", result)
        self.assertIn("metadata", result)
        
        feature = result["features"][0]
        self.assertEqual(feature["type"], "Feature")
        self.assertEqual(feature["geometry"]["type"], "Polygon")
        self.assertEqual(feature["properties"]["hazard_type"], "flood_candidate")
        self.assertIn("mean_drop_db", feature["properties"])
        self.assertIn("pixel_count", feature["properties"])
        self.assertIn("area_km2", feature["properties"])
        self.assertGreater(feature["properties"]["area_km2"], 0.0)


if __name__ == "__main__":
    unittest.main()
