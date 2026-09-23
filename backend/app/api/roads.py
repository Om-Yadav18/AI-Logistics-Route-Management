"""
Road Network API endpoints.
Provides OpenStreetMap-derived road network graphs, GeoJSON vector layers, and topological statistics.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from app.services.roads import road_network_service

router = APIRouter(
    prefix="/api/roads",
    tags=["Road Network Ingestion"]
)


def _validate_road_bbox(
    min_lon: Optional[float],
    min_lat: Optional[float],
    max_lon: Optional[float],
    max_lat: Optional[float],
) -> tuple:
    """Validates coordinates for road network queries with Assam / Guwahati defaults."""
    w = min_lon if min_lon is not None else 91.50
    s = min_lat if min_lat is not None else 26.00
    e = max_lon if max_lon is not None else 92.00
    n = max_lat if max_lat is not None else 26.50

    if not (-180.0 <= w <= 180.0 and -180.0 <= e <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Longitude coordinates must be between -180.0 and 180.0"
        )
    if not (-90.0 <= s <= 90.0 and -90.0 <= n <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude coordinates must be between -90.0 and 90.0"
        )
    if w >= e or s >= n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bounding box: min coordinates ({w}, {s}) must be less than max coordinates ({e}, {n})"
        )

    return w, s, e, n


@router.get(
    "/network",
    summary="Get a road-network summary for the requested bounding box",
    response_description="Summary of nodes, edges, cache state, and CRS for the road graph"
)
def get_road_network(
    min_lon: Optional[float] = Query(None, description="Bounding box min longitude (default: 91.50)", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Bounding box min latitude (default: 26.00)", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Bounding box max longitude (default: 92.00)", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Bounding box max latitude (default: 26.50)", ge=-90.0, le=90.0),
    force_refresh: bool = Query(False, description="Force re-download from Overpass API bypassing local GraphML cache")
) -> Dict[str, Any]:
    """Return a compact summary of the drivable road graph for the requested AOI."""
    w, s, e, n = _validate_road_bbox(min_lon, min_lat, max_lon, max_lat)
    try:
        G, source_mode = road_network_service.get_road_network_for_bbox(
            min_lon=w,
            min_lat=s,
            max_lon=e,
            max_lat=n,
            force_refresh=force_refresh,
            allow_fallback=False,
        )
        summary = road_network_service.get_summary(G, source_mode)
        summary["bbox"] = {"min_lon": w, "min_lat": s, "max_lon": e, "max_lat": n}
        return summary
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest road network: {str(err)}"
        )


@router.get(
    "/stats",
    summary="Get topological summary statistics for road network",
    response_description="Summary of nodes, edges, total road kilometers, and highway classification breakdown"
)
def get_road_network_stats(
    min_lon: Optional[float] = Query(None, description="Bounding box min longitude", ge=-180.0, le=180.0),
    min_lat: Optional[float] = Query(None, description="Bounding box min latitude", ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, description="Bounding box max longitude", ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, description="Bounding box max latitude", ge=-90.0, le=90.0),
) -> Dict[str, Any]:
    """Calculates network summary statistics including road count, total network length (km), and highway breakdown."""
    w, s, e, n = _validate_road_bbox(min_lon, min_lat, max_lon, max_lat)
    try:
        G, source_mode = road_network_service.get_road_network_for_bbox(
            min_lon=w,
            min_lat=s,
            max_lon=e,
            max_lat=n,
        )
        stats = road_network_service.get_network_statistics(G)
        stats["source_mode"] = source_mode
        stats["bbox"] = {"min_lon": w, "min_lat": s, "max_lon": e, "max_lat": n}
        return stats
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute road statistics: {str(err)}"
        )
