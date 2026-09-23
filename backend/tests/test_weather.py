"""
Unit tests for Module 4: Weather Data Integration (Open-Meteo).
Deterministic unit tests verifying metric parsing, accumulation windows, corroboration tiers,
WMO code mapping, coordinate validation, and graceful fallback handling.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.weather import (
    OpenMeteoWeatherService,
    WMO_WEATHER_CODES,
    SEVERE_WEATHER_CODES,
)


class TestWeatherService(unittest.TestCase):
    """Test suite for OpenMeteoWeatherService."""

    def setUp(self):
        self.service = OpenMeteoWeatherService()
        self.ref_time = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Generate synthetic 5-day hourly dataset (-48h to +48h around ref_time)
        times = []
        precips = []
        codes = []
        start_time = self.ref_time - timedelta(hours=48)
        for i in range(97):  # 97 hourly intervals (-48h to +48h)
            cur = start_time + timedelta(hours=i)
            times.append(cur.strftime("%Y-%m-%dT%H:%M"))
            # 1.0 mm/hr in past 48h (48 mm total), 2.0 mm/hr in past 24h (+24 mm -> 72 mm total in past 48h)
            if cur <= self.ref_time:
                diff_h = (self.ref_time - cur).total_seconds() / 3600
                if diff_h <= 24:
                    precips.append(2.0)
                else:
                    precips.append(1.0)
                codes.append(65)  # Heavy Rain
            else:
                diff_h = (cur - self.ref_time).total_seconds() / 3600
                if diff_h <= 24:
                    precips.append(1.5)  # 1.5 * 24 = 36.0 mm in forecast 24h
                else:
                    precips.append(0.5)
                codes.append(80)  # Rain showers

        self.mock_raw_response = {
            "latitude": 26.15,
            "longitude": 91.65,
            "elevation": 55.0,
            "timezone": "UTC",
            "hourly": {
                "time": times,
                "precipitation": precips,
                "weather_code": codes,
            },
            "daily": {
                "precipitation_sum": [40.0, 60.0, 36.0, 12.0],
                "precipitation_probability_max": [90, 100, 80, 40],
                "weather_code": [65, 65, 80, 80],
            }
        }

    def test_01_precipitation_aggregation_windows(self):
        """Test 1: Verify correct hourly precipitation summation over 24h, 48h, and forecast 24h."""
        result = self.service.process_weather_metrics(
            self.mock_raw_response,
            target_timestamp=self.ref_time,
        )

        precip = result["precipitation_summary"]
        # Past 24h: 24 intervals * 2.0 mm = 48.0 mm (plus 1 boundary interval)
        self.assertAlmostEqual(precip["past_24h_mm"], 50.0, delta=2.0)
        # Past 48h: (24 * 1.0) + (24 * 2.0) = 72.0 mm (+ boundary ~74.0 mm)
        self.assertAlmostEqual(precip["past_48h_mm"], 73.0, delta=3.0)
        # Forecast 24h: 24 intervals * 1.5 mm = 36.0 mm
        self.assertAlmostEqual(precip["forecast_24h_mm"], 36.0, delta=1.0)

    def test_02_corroboration_high_support(self):
        """Test 2: Verify past 48h >= 50 mm yields HIGH_SUPPORT tier."""
        tier = self.service.classify_corroboration(past_48h_mm=65.0, forecast_24h_mm=30.0)
        self.assertEqual(tier["support_level"], "HIGH_SUPPORT")
        self.assertEqual(tier["rainfall_category"], "HEAVY_RAINFALL")
        self.assertEqual(tier["forecast_trend"], "ESCALATING")
        self.assertIn("strongly corroborates", tier["explanation"])

    def test_03_corroboration_moderate_support(self):
        """Test 3: Verify past 48h between 15-50 mm yields MODERATE_SUPPORT tier."""
        tier = self.service.classify_corroboration(past_48h_mm=25.0, forecast_24h_mm=10.0)
        self.assertEqual(tier["support_level"], "MODERATE_SUPPORT")
        self.assertEqual(tier["rainfall_category"], "MODERATE_RAINFALL")
        self.assertEqual(tier["forecast_trend"], "STABLE")
        self.assertIn("plausible waterlogging", tier["explanation"])

    def test_04_corroboration_low_support(self):
        """Test 4: Verify past 48h < 15 mm yields LOW_SUPPORT tier and SUBSIDING trend."""
        tier = self.service.classify_corroboration(past_48h_mm=4.0, forecast_24h_mm=1.0)
        self.assertEqual(tier["support_level"], "LOW_SUPPORT")
        self.assertEqual(tier["rainfall_category"], "LOW_OR_NO_RAINFALL")
        self.assertEqual(tier["forecast_trend"], "SUBSIDING")

    def test_05_wmo_code_interpretation(self):
        """Test 5: Verify WMO weather codes and severe weather flag detection."""
        desc_heavy_rain, is_severe_heavy = self.service.interpret_wmo_code(65)
        self.assertEqual(desc_heavy_rain, "Heavy rain")
        self.assertTrue(is_severe_heavy)

        desc_thunder, is_severe_thunder = self.service.interpret_wmo_code(95)
        self.assertEqual(desc_thunder, "Thunderstorm")
        self.assertTrue(is_severe_thunder)

        desc_clear, is_severe_clear = self.service.interpret_wmo_code(0)
        self.assertEqual(desc_clear, "Clear sky")
        self.assertFalse(is_severe_clear)

    def test_06_bbox_center_and_validation(self):
        """Test 6: Verify BBox center calculation and coordinate bounds validation."""
        # Guwahati BBox
        min_lon, min_lat, max_lon, max_lat = 91.5, 26.0, 92.0, 26.5
        c_lat, c_lon = self.service.calculate_bbox_center(min_lon, min_lat, max_lon, max_lat)
        self.assertAlmostEqual(c_lat, 26.25)
        self.assertAlmostEqual(c_lon, 91.75)

        # Coordinate bounds validation
        lat, lon = self.service.validate_coordinates(26.15, 91.65)
        self.assertEqual(lat, 26.15)
        self.assertEqual(lon, 91.65)

        with self.assertRaises(ValueError):
            self.service.validate_coordinates(95.0, 91.65)  # Invalid lat > 90

        with self.assertRaises(ValueError):
            self.service.validate_coordinates(26.15, 200.0)  # Invalid lon > 180

    @patch("app.services.weather.requests.get")
    def test_07_network_fallback_behavior(self, mock_get):
        """Test 7: Verify graceful fallback response when Open-Meteo raises RequestException."""
        mock_get.side_effect = Exception("Connection timeout / 503 Service Unavailable")

        result = self.service.get_weather_for_coordinates(lat=26.15, lon=91.65)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["corroboration"]["support_level"], "UNKNOWN")
        self.assertIn("temporarily unavailable", result["corroboration"]["explanation"])

    @patch("app.services.weather.requests.get")
    def test_08_end_to_end_service_success(self, mock_get):
        """Test 8: Verify end-to-end service execution with mocked HTTP response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.mock_raw_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.service.get_weather_for_coordinates(
            lat=26.15,
            lon=91.65,
            target_timestamp=self.ref_time,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source"], "Open-Meteo")
        self.assertEqual(result["corroboration"]["support_level"], "HIGH_SUPPORT")
        self.assertEqual(result["precipitation_summary"]["current_weather_description"], "Heavy rain")
        self.assertTrue(result["precipitation_summary"]["is_severe_weather"])


if __name__ == "__main__":
    unittest.main()
