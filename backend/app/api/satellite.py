from typing import Optional, Dict, Any
import os
from fastapi import APIRouter, HTTPException, Query, status
from app.services.satellite import satellite_service
from app.services.sentinel1_acquisition import sentinel1_acquisition_service
from app.services.change_detection import change_detection_service

router = APIRouter(
    prefix="/api/satellite",
    tags=["Satellite Data Ingestion"]
)


def _parse_bbox_params(
    min_lon: Optional[float],
    min_lat: Optional[float],
    max_lon: Optional[float],
    max_lat: Optional[float],
) -> Optional[tuple]:
    """Helper to validate that if one bbox coordinate is provided, all four must be provided."""
    coords = [min_lon, min_lat, max_lon, max_lat]
    provided = [c is not None for c in coords]

    if any(provided) and not all(provided):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="If specifying bounding box coordinates, all four (min_lon, min_lat, max_lon, max_lat) must be provided."
        )

    if all(provided):
        try:
            return satellite_service.validate_bbox(min_lon, min_lat, max_lon, max_lat)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    return None


@router.get(
    "/sentinel-1/latest",
    summary="Get latest Sentinel-1 (SAR) observation metadata",
    response_description="Metadata for the latest Sentinel-1 observation over the target region"
)
def get_latest_sentinel_1(
    min_lon: Optional[float] = Query(None, description="Minimum longitude (WGS84)", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Minimum latitude (WGS84)", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Maximum longitude (WGS84)", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Maximum latitude (WGS84)", ge=-90.0, le=90.0),
    product_type: Optional[str] = Query(None, description="Optional product filter e.g. GRD, SLC, RAW")
) -> Dict[str, Any]:
    """Retrieves metadata for the single most recent Sentinel-1 Synthetic Aperture Radar (SAR) scene."""
    bbox = _parse_bbox_params(min_lon, min_lat, max_lon, max_lat)
    try:
        observation = satellite_service.get_latest_sentinel1(bbox=bbox, product_type=product_type)
        if not observation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Sentinel-1 observations found for the specified geographic area."
            )
        return {
            "status": "success",
            "data": observation
        }
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Copernicus Data Space API request timed out."
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to connect to Copernicus satellite service: {str(e)}"
        )


@router.get(
    "/sentinel-1/acquire",
    summary="Acquire Sentinel-1 GeoTIFF and inspect raster metadata",
    response_description="Raster spatial metadata, dimensions, coordinate system, and pixel statistics"
)
def acquire_sentinel_1_raster(
    min_lon: Optional[float] = Query(None, description="Minimum longitude (WGS84)", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Minimum latitude (WGS84)", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Maximum longitude (WGS84)", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Maximum latitude (WGS84)", ge=-90.0, le=90.0),
    width: int = Query(512, description="Raster width in pixels", ge=64, le=2048),
    height: int = Query(512, description="Raster height in pixels", ge=64, le=2048),
) -> Dict[str, Any]:
    """Acquires a calibrated Sentinel-1 SAR GeoTIFF for the bounding box and inspects its raster properties via Rasterio."""
    bbox = _parse_bbox_params(min_lon, min_lat, max_lon, max_lat)
    try:
        inspection = sentinel1_acquisition_service.acquire_and_inspect(
            bbox=bbox,
            width=width,
            height=height
        )
        return {
            "success": True,
            "data": inspection
        }
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Sentinel-1 acquisition request timed out."
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Raster acquisition/inspection error: {str(e)}"
        )


@router.get(
    "/sentinel-1/change-detection",
    summary="Detect environmental/flood candidates using bitemporal Sentinel-1 SAR imagery",
    response_description="GeoJSON FeatureCollection containing flood candidate polygon geometries and metadata"
)
def detect_flood_candidates(
    baseline_file: Optional[str] = Query(None, description="Optional filename of cached baseline GeoTIFF"),
    event_file: Optional[str] = Query(None, description="Optional filename of cached event GeoTIFF"),
    baseline_time_from: Optional[str] = Query(None, description="Baseline start date (ISO 8601 UTC) e.g. 2026-08-15T00:00:00Z"),
    baseline_time_to: Optional[str] = Query(None, description="Baseline end date (ISO 8601 UTC) e.g. 2026-08-25T23:59:59Z"),
    event_time_from: Optional[str] = Query(None, description="Event start date (ISO 8601 UTC) e.g. 2026-09-05T00:00:00Z"),
    event_time_to: Optional[str] = Query(None, description="Event end date (ISO 8601 UTC) e.g. 2026-09-15T23:59:59Z"),
    min_lon: Optional[float] = Query(None, description="Minimum longitude (WGS84)", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Minimum latitude (WGS84)", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Maximum longitude (WGS84)", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Maximum latitude (WGS84)", ge=-90.0, le=90.0),
    water_threshold_db: float = Query(-16.0, description="Backscatter threshold (dB) for water identification"),
    change_threshold_db: float = Query(-4.0, description="Minimum backscatter drop (dB) to indicate new flood candidate"),
    min_region_pixels: int = Query(5, description="Minimum connected pixel count to filter out speckle noise", ge=1, le=1000),
    width: int = Query(512, description="Raster width in pixels", ge=64, le=2048),
    height: int = Query(512, description="Raster height in pixels", ge=64, le=2048),
) -> Dict[str, Any]:
    """Executes bitemporal SAR change detection between baseline and event scenes, returning flood candidate GeoJSON polygons."""
    bbox = _parse_bbox_params(min_lon, min_lat, max_lon, max_lat)
    active_bbox = bbox or satellite_service.default_bbox

    # Resolve baseline path
    if baseline_file:
        b_path = os.path.join(sentinel1_acquisition_service.cache_dir, os.path.basename(baseline_file))
    else:
        b_time_from = baseline_time_from or "2026-08-15T00:00:00Z"
        b_time_to = baseline_time_to or "2026-08-25T23:59:59Z"
        b_path, _ = sentinel1_acquisition_service.acquire_imagery(
            bbox=active_bbox, time_from=b_time_from, time_to=b_time_to, width=width, height=height
        )

    # Resolve event path
    if event_file:
        e_path = os.path.join(sentinel1_acquisition_service.cache_dir, os.path.basename(event_file))
    else:
        e_time_from = event_time_from or "2026-09-05T00:00:00Z"
        e_time_to = event_time_to or "2026-09-15T23:59:59Z"
        e_path, _ = sentinel1_acquisition_service.acquire_imagery(
            bbox=active_bbox, time_from=e_time_from, time_to=e_time_to, width=width, height=height
        )

    try:
        geojson_result = change_detection_service.detect_changes(
            baseline_path=b_path,
            event_path=e_path,
            water_threshold_db=water_threshold_db,
            change_threshold_db=change_threshold_db,
            min_region_pixels=min_region_pixels,
        )
        return geojson_result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Change detection processing error: {str(e)}"
        )


@router.get(
    "/sentinel-2/latest",
    summary="Get latest Sentinel-2 (Optical) observation metadata",
    response_description="Metadata for the latest Sentinel-2 observation over the target region"
)
def get_latest_sentinel_2(
    min_lon: Optional[float] = Query(None, description="Minimum longitude (WGS84)", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Minimum latitude (WGS84)", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Maximum longitude (WGS84)", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Maximum latitude (WGS84)", ge=-90.0, le=90.0),
    product_type: Optional[str] = Query(None, description="Optional product filter e.g. S2MSI2A, S2MSI1C")
) -> Dict[str, Any]:
    """Retrieves metadata for the single most recent Sentinel-2 Optical (MSI) scene."""
    bbox = _parse_bbox_params(min_lon, min_lat, max_lon, max_lat)
    try:
        observation = satellite_service.get_latest_sentinel2(bbox=bbox, product_type=product_type)
        if not observation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Sentinel-2 observations found for the specified geographic area."
            )
        return {
            "status": "success",
            "data": observation
        }
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Copernicus Data Space API request timed out."
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to connect to Copernicus satellite service: {str(e)}"
        )


@router.get(
    "/latest",
    summary="Get combined latest Sentinel-1 and Sentinel-2 observation metadata",
    response_description="Combined metadata overview for both satellite sensors"
)
def get_latest_satellite_summary(
    min_lon: Optional[float] = Query(None, description="Minimum longitude (WGS84)", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Minimum latitude (WGS84)", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Maximum longitude (WGS84)", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Maximum latitude (WGS84)", ge=-90.0, le=90.0),
) -> Dict[str, Any]:
    """Retrieves latest metadata summary for both Sentinel-1 and Sentinel-2."""
    bbox = _parse_bbox_params(min_lon, min_lat, max_lon, max_lat)
    try:
        summary = satellite_service.get_latest_summary(bbox=bbox)
        return {
            "status": "success",
            "data": summary
        }
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Copernicus Data Space API request timed out."
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to connect to Copernicus satellite service: {str(e)}"
        )


