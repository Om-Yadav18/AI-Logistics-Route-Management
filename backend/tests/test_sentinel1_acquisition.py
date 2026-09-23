import os
import sys
import shutil
import tempfile
import unittest
import numpy as np
import rasterio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.sentinel1_acquisition import Sentinel1AcquisitionService


class TestSentinel1Acquisition(unittest.TestCase):
    """Unit tests for Sentinel-1 acquisition service and Rasterio inspection."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.service = Sentinel1AcquisitionService(cache_dir=self.test_dir)
        self.test_bbox = (91.50, 26.00, 92.00, 26.50)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_build_process_payload(self):
        """Verify Sentinel Hub Processing API payload structure."""
        payload = self.service.build_process_payload(
            bbox=self.test_bbox,
            time_from="2026-09-01T00:00:00Z",
            time_to="2026-09-15T23:59:59Z",
            width=256,
            height=256,
        )
        self.assertIn("input", payload)
        self.assertEqual(payload["input"]["bounds"]["bbox"], [91.50, 26.00, 92.00, 26.50])
        self.assertEqual(payload["input"]["data"][0]["type"], "sentinel-1-grd")
        self.assertTrue(payload["input"]["data"][0]["processing"]["orthorectify"])
        self.assertEqual(payload["output"]["width"], 256)
        self.assertEqual(payload["output"]["height"], 256)
        self.assertIn("evalscript", payload)

    def test_generate_and_inspect_raster(self):
        """Verify generating a synthetic SAR GeoTIFF and reading it with Rasterio."""
        filepath = os.path.join(self.test_dir, "test_s1.tif")
        self.service.generate_synthetic_raster(self.test_bbox, filepath, width=128, height=128)

        self.assertTrue(os.path.exists(filepath))

        inspection = self.service.inspect_raster(filepath)
        self.assertEqual(inspection["file_name"], "test_s1.tif")
        self.assertEqual(inspection["width"], 128)
        self.assertEqual(inspection["height"], 128)
        self.assertEqual(inspection["bands"], 1)
        self.assertEqual(inspection["crs"], "EPSG:4326")
        self.assertEqual(inspection["dtype"], "float32")
        self.assertIn("transform", inspection)
        self.assertEqual(len(inspection["transform"]), 6)

        # Check bounds
        bounds = inspection["bounds"]
        self.assertAlmostEqual(bounds["left"], 91.50, places=2)
        self.assertAlmostEqual(bounds["bottom"], 26.00, places=2)
        self.assertAlmostEqual(bounds["right"], 92.00, places=2)
        self.assertAlmostEqual(bounds["top"], 26.50, places=2)

        # Check statistics
        stats = inspection["statistics"]
        self.assertIsNotNone(stats["min"])
        self.assertIsNotNone(stats["max"])
        self.assertIsNotNone(stats["mean"])
        self.assertIsNotNone(stats["std"])
        self.assertGreater(stats["max"], stats["min"])
        self.assertEqual(stats["valid_pixel_count"], 128 * 128)

    def test_acquire_and_inspect_fallback(self):
        """Verify acquire_and_inspect end-to-end with local fallback mode."""
        res = self.service.acquire_and_inspect(bbox=self.test_bbox, width=64, height=64)
        self.assertEqual(res["width"], 64)
        self.assertEqual(res["height"], 64)
        self.assertEqual(res["bands"], 1)
        self.assertEqual(res["crs"], "EPSG:4326")
        self.assertIn(res["source_mode"], ["cdse_live", "cache", "synthetic_fallback"])

    def test_missing_credentials_handling(self):
        """Verify clear error when no credentials exist and fallback is disabled."""
        empty_service = Sentinel1AcquisitionService(cache_dir=self.test_dir)
        empty_service.client_id = ""
        empty_service.client_secret = ""
        empty_service.username = ""
        empty_service.password = ""

        with self.assertRaises(ValueError):
            empty_service.get_auth_token()


if __name__ == "__main__":
    unittest.main()
