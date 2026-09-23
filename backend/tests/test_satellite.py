import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.satellite import CopernicusSatelliteService, satellite_service
from app.api.satellite import _parse_bbox_params
from fastapi import HTTPException


class TestSatelliteService(unittest.TestCase):
    """Unit tests for CopernicusSatelliteService logic."""

    def setUp(self):
        self.service = CopernicusSatelliteService()

    def test_validate_bbox_valid(self):
        """Test valid bounding box passes validation."""
        bbox = self.service.validate_bbox(91.5, 26.0, 92.0, 26.5)
        self.assertEqual(bbox, (91.5, 26.0, 92.0, 26.5))

    def test_validate_bbox_invalid_lat(self):
        """Test out of range latitude raises ValueError."""
        with self.assertRaises(ValueError):
            self.service.validate_bbox(91.5, -95.0, 92.0, 26.5)

    def test_validate_bbox_min_greater_than_max(self):
        """Test min_lon >= max_lon raises ValueError."""
        with self.assertRaises(ValueError):
            self.service.validate_bbox(93.0, 26.0, 92.0, 26.5)

    def test_build_wkt_polygon(self):
        """Test WKT Polygon string formatting."""
        wkt = self.service._build_wkt_polygon((91.5, 26.0, 92.0, 26.5))
        self.assertEqual(wkt, "POLYGON((91.5 26.0, 92.0 26.0, 92.0 26.5, 91.5 26.5, 91.5 26.0))")

    def test_parse_product(self):
        """Test parsing of raw CDSE OData JSON product."""
        mock_raw = {
            "Id": "test-uuid-1234",
            "Name": "S1A_IW_GRDH_1SDV_20260901_TEST.SAFE",
            "PublicationDate": "2026-09-01T12:00:00Z",
            "Online": True,
            "ContentLength": 1024000,
            "ContentDate": {
                "Start": "2026-09-01T10:00:00Z",
                "End": "2026-09-01T10:00:30Z"
            },
            "Attributes": [
                {"Name": "platformShortName", "Value": "SENTINEL-1"},
                {"Name": "instrumentShortName", "Value": "SAR"},
                {"Name": "productType", "Value": "GRD"},
                {"Name": "polarisationChannels", "Value": "VV&VH"},
                {"Name": "processingLevel", "Value": "LEVEL1"}
            ],
            "GeoFootprint": {"type": "Polygon", "coordinates": [[[91.5, 26.0], [92.0, 26.0], [92.0, 26.5], [91.5, 26.5], [91.5, 26.0]]]}
        }
        parsed = self.service._parse_product(mock_raw, "Sentinel-1")
        self.assertEqual(parsed["satellite"], "Sentinel-1")
        self.assertEqual(parsed["product_id"], "test-uuid-1234")
        self.assertEqual(parsed["instrument"], "SAR")
        self.assertEqual(parsed["product_type"], "GRD")
        self.assertEqual(parsed["polarization"], "VV&VH")
        self.assertEqual(parsed["acquisition_start"], "2026-09-01T10:00:00Z")

    def test_parse_bbox_params_partial(self):
        """Test partial bounding box params raise HTTPException 400."""
        with self.assertRaises(HTTPException) as ctx:
            _parse_bbox_params(91.5, 26.0, None, 26.5)
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
