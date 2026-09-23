"""
Weather Service using Open-Meteo API.
Provides historical rainfall accumulation, real-time weather metrics, and short-term precipitation
forecasts to corroborate Sentinel-1 SAR flood candidates and inform logistics road-risk scoring.
"""

from typing import Dict, Any, Optional, Tuple, List
import os
import logging
from datetime import datetime, timezone, timedelta
import requests

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("WEATHER_REQUEST_TIMEOUT_SECONDS", "10"))

# WMO Weather interpretation codes (WW)
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# WMO codes representing severe convective/precipitation hazards
SEVERE_WEATHER_CODES = {65, 67, 75, 82, 86, 95, 96, 99}


class OpenMeteoWeatherService:
    """Service for interacting with Open-Meteo meteorological endpoints."""

    def __init__(self, base_url: str = OPEN_METEO_FORECAST_URL, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url
        self.timeout = timeout

    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> Tuple[float, float]:
        """Validates geographic latitude and longitude bounds."""
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude must be between -90.0 and 90.0, got {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude must be between -180.0 and 180.0, got {lon}")
        return float(lat), float(lon)

    @staticmethod
    def calculate_bbox_center(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Tuple[float, float]:
        """Calculates center (lat, lon) for a bounding box."""
        center_lat = (min_lat + max_lat) / 2.0
        center_lon = (min_lon + max_lon) / 2.0
        return center_lat, center_lon

    @staticmethod
    def interpret_wmo_code(code: Optional[int]) -> Tuple[str, bool]:
        """Returns human-readable description and severe weather boolean for a WMO code."""
        if code is None:
            return "Unknown", False
        description = WMO_WEATHER_CODES.get(code, f"Weather Code {code}")
        is_severe = code in SEVERE_WEATHER_CODES
        return description, is_severe

    @staticmethod
    def classify_corroboration(
        past_48h_mm: float,
        forecast_24h_mm: float,
    ) -> Dict[str, str]:
        """
        Classifies weather support for satellite flood candidates into explainable tiers:
        - HIGH_SUPPORT: >= 50 mm past 48h rainfall (heavy monsoon/inundation conditions).
        - MODERATE_SUPPORT: 15 mm - 50 mm past 48h rainfall (plausible waterlogging).
        - LOW_SUPPORT: < 15 mm past 48h rainfall (low/no rain; potential agricultural or terrain artifact).
        
        Forecast Trend:
        - ESCALATING: >= 25 mm forecast in next 24h.
        - STABLE: 5 mm - 25 mm forecast in next 24h.
        - SUBSIDING: < 5 mm forecast in next 24h.
        """
        if past_48h_mm >= 50.0:
            support_level = "HIGH_SUPPORT"
            rainfall_category = "HEAVY_RAINFALL"
            explanation = (
                f"Heavy antecedent rainfall ({past_48h_mm:.1f} mm in past 48h) strongly corroborates "
                f"environmental inundation detected by satellite SAR."
            )
        elif past_48h_mm >= 15.0:
            support_level = "MODERATE_SUPPORT"
            rainfall_category = "MODERATE_RAINFALL"
            explanation = (
                f"Moderate antecedent rainfall ({past_48h_mm:.1f} mm in past 48h) indicates plausible "
                f"waterlogging in low-lying depressions."
            )
        else:
            support_level = "LOW_SUPPORT"
            rainfall_category = "LOW_OR_NO_RAINFALL"
            explanation = (
                f"Low antecedent rainfall ({past_48h_mm:.1f} mm in past 48h); detected SAR change may be "
                f"due to upstream river surge, agricultural irrigation, or specular terrain."
            )

        if forecast_24h_mm >= 25.0:
            forecast_trend = "ESCALATING"
        elif forecast_24h_mm >= 5.0:
            forecast_trend = "STABLE"
        else:
            forecast_trend = "SUBSIDING"

        return {
            "support_level": support_level,
            "rainfall_category": rainfall_category,
            "forecast_trend": forecast_trend,
            "explanation": explanation,
        }

    def fetch_raw_open_meteo(
        self,
        lat: float,
        lon: float,
        past_days: int = 2,
        forecast_days: int = 2,
    ) -> Dict[str, Any]:
        """Direct HTTP call to Open-Meteo Forecast endpoint."""
        lat, lon = self.validate_coordinates(lat, lon)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,weather_code",
            "daily": "precipitation_sum,precipitation_probability_max,weather_code",
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": "UTC",
        }
        response = requests.get(self.base_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def process_weather_metrics(
        self,
        raw_data: Dict[str, Any],
        target_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Parses Open-Meteo response into past 24h/48h/72h and forecast 24h/48h precipitation totals
        relative to the target_timestamp (defaults to current UTC time).
        """
        ref_time = target_timestamp or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        hourly = raw_data.get("hourly", {})
        times = hourly.get("time", [])
        precip = hourly.get("precipitation", [])
        codes = hourly.get("weather_code", [])

        # Parse timestamps into datetime objects
        parsed_hourly: List[Tuple[datetime, float, int]] = []
        for t_str, p_val, c_val in zip(times, precip, codes):
            try:
                # Open-Meteo ISO format e.g. "2024-07-15T00:00"
                dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                p = float(p_val) if p_val is not None else 0.0
                c = int(c_val) if c_val is not None else 0
                parsed_hourly.append((dt, p, c))
            except (ValueError, TypeError):
                continue

        past_24h_mm = 0.0
        past_48h_mm = 0.0
        past_72h_mm = 0.0
        forecast_24h_mm = 0.0
        forecast_48h_mm = 0.0

        current_code = 0
        min_diff = timedelta(days=999)

        for dt, p, c in parsed_hourly:
            diff = dt - ref_time
            # Past intervals (before or at reference time)
            if -timedelta(hours=24) <= diff <= timedelta(seconds=0):
                past_24h_mm += p
            if -timedelta(hours=48) <= diff <= timedelta(seconds=0):
                past_48h_mm += p
            if -timedelta(hours=72) <= diff <= timedelta(seconds=0):
                past_72h_mm += p

            # Future intervals (after reference time)
            if timedelta(seconds=0) < diff <= timedelta(hours=24):
                forecast_24h_mm += p
            if timedelta(seconds=0) < diff <= timedelta(hours=48):
                forecast_48h_mm += p

            # Identify weather code closest to ref_time
            abs_diff = abs(diff)
            if abs_diff < min_diff:
                min_diff = abs_diff
                current_code = c

        weather_desc, is_severe = self.interpret_wmo_code(current_code)
        corroboration = self.classify_corroboration(past_48h_mm, forecast_24h_mm)

        return {
            "location": {
                "latitude": raw_data.get("latitude"),
                "longitude": raw_data.get("longitude"),
                "elevation_m": raw_data.get("elevation"),
                "timezone": raw_data.get("timezone", "UTC"),
            },
            "reference_timestamp": ref_time.isoformat(),
            "precipitation_summary": {
                "past_24h_mm": round(past_24h_mm, 2),
                "past_48h_mm": round(past_48h_mm, 2),
                "past_72h_mm": round(past_72h_mm, 2),
                "forecast_24h_mm": round(forecast_24h_mm, 2),
                "forecast_48h_mm": round(forecast_48h_mm, 2),
                "current_weather_code": current_code,
                "current_weather_description": weather_desc,
                "is_severe_weather": is_severe,
            },
            "corroboration": corroboration,
            "status": "success",
            "source": "Open-Meteo",
        }

    def get_weather_for_coordinates(
        self,
        lat: float,
        lon: float,
        target_timestamp: Optional[datetime] = None,
        past_days: int = 2,
        forecast_days: int = 2,
    ) -> Dict[str, Any]:
        """Fetches and processes meteorological data for a single coordinate."""
        try:
            raw_data = self.fetch_raw_open_meteo(
                lat=lat,
                lon=lon,
                past_days=past_days,
                forecast_days=forecast_days,
            )
            return self.process_weather_metrics(raw_data, target_timestamp=target_timestamp)
        except Exception as e:
            logger.warning(f"Failed to fetch weather data from Open-Meteo: {e}")
            return self._build_fallback_response(lat=lat, lon=lon, error_msg=str(e))

    def get_weather_for_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        target_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Fetches and processes meteorological data for a bounding box center."""
        center_lat, center_lon = self.calculate_bbox_center(min_lon, min_lat, max_lon, max_lat)
        result = self.get_weather_for_coordinates(
            lat=center_lat,
            lon=center_lon,
            target_timestamp=target_timestamp,
        )
        if "location" in result:
            result["location"]["bbox"] = {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            }
        return result

    @staticmethod
    def _build_fallback_response(lat: float, lon: float, error_msg: str) -> Dict[str, Any]:
        """Graceful fallback response when external Open-Meteo API is unreachable."""
        return {
            "location": {
                "latitude": lat,
                "longitude": lon,
            },
            "reference_timestamp": datetime.now(timezone.utc).isoformat(),
            "precipitation_summary": {
                "past_24h_mm": 0.0,
                "past_48h_mm": 0.0,
                "past_72h_mm": 0.0,
                "forecast_24h_mm": 0.0,
                "forecast_48h_mm": 0.0,
                "current_weather_code": 0,
                "current_weather_description": "Service Unavailable",
                "is_severe_weather": False,
            },
            "corroboration": {
                "support_level": "UNKNOWN",
                "rainfall_category": "UNKNOWN",
                "forecast_trend": "UNKNOWN",
                "explanation": f"Weather API is temporarily unavailable ({error_msg}). Proceeding with satellite evidence only.",
            },
            "status": "degraded",
            "source": "fallback",
        }


# Singleton instance
weather_service = OpenMeteoWeatherService()


def get_weather_service() -> OpenMeteoWeatherService:
    return weather_service
