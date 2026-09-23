"""
Weather API endpoints for Open-Meteo integration.
Provides real-time precipitation metrics, historical rainfall accumulation, and flood candidate corroboration.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from app.services.weather import weather_service

router = APIRouter(
    prefix="/api/weather",
    tags=["Weather Data Integration"]
)


@router.get(
    "/current",
    summary="Get current weather & recent rainfall accumulation",
    response_description="Recent rainfall (24h/48h/72h), 24h forecast, and WMO weather condition"
)
def get_current_weather(
    lat: Optional[float] = Query(None, description="Latitude (-90.0 to 90.0)", ge=-90.0, le=90.0),
    lon: Optional[float] = Query(None, description="Longitude (-180.0 to 180.0)", ge=-180.0, le=180.0),
    min_lon: Optional[float] = Query(None, description="Bounding box min longitude", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Bounding box min latitude", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Bounding box max longitude", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Bounding box max latitude", ge=-90.0, le=90.0),
) -> Dict[str, Any]:
    """
    Retrieves recent precipitation accumulation and short-term forecast.
    Accepts either a single point (lat, lon) or a bounding box (min_lon, min_lat, max_lon, max_lat).
    Defaults to Guwahati, Assam (26.15 N, 91.65 E) if no coordinates are specified.
    """
    bbox_coords = [min_lon, min_lat, max_lon, max_lat]
    bbox_provided = [c is not None for c in bbox_coords]

    if any(bbox_provided):
        if not all(bbox_provided):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="If querying by bounding box, all 4 coordinates (min_lon, min_lat, max_lon, max_lat) must be provided."
            )
        if min_lon >= max_lon or min_lat >= max_lat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bounding box: min coordinates ({min_lon}, {min_lat}) must be less than max coordinates ({max_lon}, {max_lat})."
            )
        return weather_service.get_weather_for_bbox(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
        )

    # Point-based query (default to Guwahati center if omitted)
    target_lat = lat if lat is not None else 26.15
    target_lon = lon if lon is not None else 91.65

    return weather_service.get_weather_for_coordinates(
        lat=target_lat,
        lon=target_lon,
    )


@router.get(
    "/corroborate",
    summary="Corroborate satellite observation with historical rainfall",
    response_description="Antecedent rainfall metrics and explainable corroboration tier for a satellite acquisition"
)
def corroborate_satellite_observation(
    lat: float = Query(..., description="Target latitude (-90.0 to 90.0)", ge=-90.0, le=90.0),
    lon: float = Query(..., description="Target longitude (-180.0 to 180.0)", ge=-180.0, le=180.0),
    timestamp: Optional[str] = Query(None, description="Satellite acquisition timestamp in ISO-8601 format (e.g. 2024-07-15T06:00:00Z)"),
    past_days: int = Query(2, description="Number of past days to query (1-7)", ge=1, le=7),
    forecast_days: int = Query(2, description="Number of forecast days to query (1-7)", ge=1, le=7),
) -> Dict[str, Any]:
    """
    Evaluates meteorological evidence at the given coordinate relative to a satellite acquisition timestamp.
    Calculates whether antecedent rainfall supports the presence of standing water and provides forecast trends.
    """
    target_dt = None
    if timestamp:
        try:
            target_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timestamp format '{timestamp}'. Please use ISO-8601 format (e.g. 2024-07-15T06:00:00Z)."
            )

    return weather_service.get_weather_for_coordinates(
        lat=lat,
        lon=lon,
        target_timestamp=target_dt,
        past_days=past_days,
        forecast_days=forecast_days,
    )
