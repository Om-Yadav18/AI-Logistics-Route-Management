import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

CDSE_ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


class CopernicusSatelliteService:
    """Service for interacting with the Copernicus Data Space Ecosystem (CDSE)

    Provides methods to query Sentinel-1 (SAR) and Sentinel-2 (Optical) metadata.
    """

    def __init__(self):
        self.username = os.getenv("COPERNICUS_USERNAME", "")
        self.password = os.getenv("COPERNICUS_PASSWORD", "")
        self.client_id = os.getenv("COPERNICUS_CLIENT_ID", "cdse-public")
        self.default_bbox = (
            float(os.getenv("DEFAULT_BBOX_MIN_LON", "91.50")),
            float(os.getenv("DEFAULT_BBOX_MIN_LAT", "26.00")),
            float(os.getenv("DEFAULT_BBOX_MAX_LON", "92.00")),
            float(os.getenv("DEFAULT_BBOX_MAX_LAT", "26.50")),
        )

    def validate_bbox(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> Tuple[float, float, float, float]:
        """Validates bounding box geographic bounds (WGS84)."""
        if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
            raise ValueError("Longitude must be between -180.0 and 180.0 degrees.")
        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise ValueError("Latitude must be between -90.0 and 90.0 degrees.")
        if min_lon >= max_lon:
            raise ValueError("min_lon must be strictly less than max_lon.")
        if min_lat >= max_lat:
            raise ValueError("min_lat must be strictly less than max_lat.")
        return (min_lon, min_lat, max_lon, max_lat)

    def _build_wkt_polygon(self, bbox: Tuple[float, float, float, float]) -> str:
        """Constructs a WKT Polygon string from a bounding box (min_lon, min_lat, max_lon, max_lat)."""
        min_lon, min_lat, max_lon, max_lat = bbox
        return (
            f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
            f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
        )

    def _extract_attribute_map(self, raw_attributes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Flattens CDSE Attributes array into a dictionary."""
        attr_map = {}
        for attr in raw_attributes or []:
            name = attr.get("Name")
            value = attr.get("Value")
            if name is not None:
                attr_map[name] = value
        return attr_map

    def _parse_product(self, raw_item: Dict[str, Any], satellite: str) -> Dict[str, Any]:
        """Transforms a raw CDSE OData product JSON into a clean, structured dictionary."""
        attrs = self._extract_attribute_map(raw_item.get("Attributes", []))
        content_date = raw_item.get("ContentDate", {}) or {}

        # Extract cloud cover safely for Sentinel-2
        cloud_cover = attrs.get("cloudCover")
        if cloud_cover is not None:
            try:
                cloud_cover = round(float(cloud_cover), 2)
            except (ValueError, TypeError):
                cloud_cover = None

        return {
            "satellite": satellite,
            "product_id": raw_item.get("Id"),
            "product_name": raw_item.get("Name"),
            "acquisition_start": content_date.get("Start"),
            "acquisition_end": content_date.get("End"),
            "publication_date": raw_item.get("PublicationDate"),
            "platform": attrs.get("platformShortName") or satellite,
            "instrument": attrs.get("instrumentShortName") or ("SAR" if "SENTINEL-1" in satellite.upper() else "MSI"),
            "product_type": attrs.get("productType") or raw_item.get("ContentType"),
            "processing_level": attrs.get("processingLevel"),
            "polarization": attrs.get("polarisationChannels"),
            "cloud_cover_percentage": cloud_cover,
            "online": raw_item.get("Online", True),
            "content_length_bytes": raw_item.get("ContentLength"),
            "footprint": raw_item.get("GeoFootprint") or raw_item.get("Footprint"),
        }

    def authenticate(self) -> Optional[str]:
        """Authenticates with Copernicus CDSE Keycloak service if credentials exist."""
        if not self.username or not self.password:
            return None

        data = {
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
        }
        try:
            response = requests.post(CDSE_TOKEN_URL, data=data, timeout=15)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                return None
        except requests.RequestException:
            return None

    def search_products(
        self,
        collection: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product_type: Optional[str] = None,
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """Queries the CDSE OData Catalogue API for satellite products."""
        active_bbox = bbox or self.default_bbox
        self.validate_bbox(*active_bbox)

        polygon_wkt = self._build_wkt_polygon(active_bbox)
        filter_parts = [
            f"Collection/Name eq '{collection.upper()}'",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{polygon_wkt}')",
        ]

        if start_date:
            filter_parts.append(f"ContentDate/Start ge {start_date}")
        if end_date:
            filter_parts.append(f"ContentDate/Start le {end_date}")
        if product_type:
            filter_parts.append(
                f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{product_type}')"
            )

        filter_query = " and ".join(filter_parts)

        params = {
            "$filter": filter_query,
            "$orderby": "ContentDate/Start desc",
            "$top": str(limit),
            "$expand": "Attributes",
        }

        satellite_name = "Sentinel-1" if "SENTINEL-1" in collection.upper() else "Sentinel-2"

        try:
            response = requests.get(CDSE_ODATA_URL, params=params, timeout=25)
        except requests.Timeout:
            raise TimeoutError("Copernicus Data Space API request timed out.")
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to Copernicus API: {str(e)}")

        if response.status_code == 200:
            data = response.json()
            raw_items = data.get("value", [])
            return [self._parse_product(item, satellite_name) for item in raw_items]
        else:
            raise ConnectionError(
                f"Copernicus API error {response.status_code}: {response.text[:200]}"
            )

    def get_latest_sentinel1(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        product_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves metadata for the single most recent Sentinel-1 SAR observation."""
        results = self.search_products(
            collection="SENTINEL-1",
            bbox=bbox,
            product_type=product_type,
            limit=1,
        )
        return results[0] if results else None

    def get_latest_sentinel2(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        product_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves metadata for the single most recent Sentinel-2 Optical observation."""
        results = self.search_products(
            collection="SENTINEL-2",
            bbox=bbox,
            product_type=product_type,
            limit=1,
        )
        return results[0] if results else None

    def get_latest_summary(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Dict[str, Any]:
        """Retrieves latest observation metadata for both Sentinel-1 and Sentinel-2."""
        active_bbox = bbox or self.default_bbox
        s1 = self.get_latest_sentinel1(bbox=active_bbox)
        s2 = self.get_latest_sentinel2(bbox=active_bbox)
        return {
            "bounding_box": {
                "min_lon": active_bbox[0],
                "min_lat": active_bbox[1],
                "max_lon": active_bbox[2],
                "max_lat": active_bbox[3],
            },
            "sentinel_1": s1,
            "sentinel_2": s2,
            "query_timestamp": datetime.utcnow().isoformat() + "Z",
        }


# Singleton instance for application-wide dependency injection
satellite_service = CopernicusSatelliteService()
