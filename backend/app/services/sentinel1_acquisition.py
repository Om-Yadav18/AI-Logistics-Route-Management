import os
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from dotenv import load_dotenv

from app.services.satellite import satellite_service

load_dotenv()

CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Evalscript to extract calibrated linear VV backscatter from Sentinel-1 GRD
S1_VV_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["VV"],
      units: "LINEAR"
    }],
    output: {
      bands: 1,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(samples) {
  return [samples.VV];
}
"""


class Sentinel1AcquisitionService:
    """Service to acquire and inspect Sentinel-1 SAR imagery via the CDSE Processing API."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.client_id = os.getenv("CDSE_CLIENT_ID", "")
        self.client_secret = os.getenv("CDSE_CLIENT_SECRET", "")
        self.username = os.getenv("COPERNICUS_USERNAME", "")
        self.password = os.getenv("COPERNICUS_PASSWORD", "")
        self.public_client_id = os.getenv("COPERNICUS_CLIENT_ID", "cdse-public")
        
        # Base cache directory for downloaded/generated GeoTIFFs
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.cache_dir = os.path.join(base_path, "data", "cache")
        
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_auth_token(self) -> str:
        """Obtains an OAuth access token from Copernicus CDSE Keycloak.
        
        Tries client_credentials first if configured, else tries password grant.
        """
        # 1. Try OAuth Client Credentials
        if self.client_id and self.client_secret:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            try:
                res = requests.post(CDSE_TOKEN_URL, data=payload, timeout=15)
                if res.status_code == 200:
                    return res.json().get("access_token")
                else:
                    raise PermissionError(f"CDSE client_credentials authentication failed: HTTP {res.status_code}")
            except requests.RequestException as e:
                raise ConnectionError(f"Failed to connect to CDSE authentication service: {str(e)}")

        # 2. Try Password Grant
        if self.username and self.password:
            payload = {
                "grant_type": "password",
                "client_id": self.public_client_id,
                "username": self.username,
                "password": self.password,
            }
            try:
                res = requests.post(CDSE_TOKEN_URL, data=payload, timeout=15)
                if res.status_code == 200:
                    return res.json().get("access_token")
                else:
                    err_desc = res.json().get("error_description", "Authentication failed")
                    raise PermissionError(f"CDSE password authentication failed: {err_desc}")
            except requests.RequestException as e:
                raise ConnectionError(f"Failed to connect to CDSE authentication service: {str(e)}")

        raise ValueError("No CDSE credentials configured (CDSE_CLIENT_ID/SECRET or COPERNICUS_USERNAME/PASSWORD required).")

    def build_process_payload(
        self,
        bbox: Tuple[float, float, float, float],
        time_from: str,
        time_to: str,
        width: int = 512,
        height: int = 512,
    ) -> Dict[str, Any]:
        """Constructs the JSON request payload for the CDSE Sentinel Hub Processing API."""
        min_lon, min_lat, max_lon, max_lat = bbox
        return {
            "input": {
                "bounds": {
                    "bbox": [min_lon, min_lat, max_lon, max_lat],
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                    }
                },
                "data": [
                    {
                        "type": "sentinel-1-grd",
                        "dataFilter": {
                            "timeRange": {
                                "from": time_from,
                                "to": time_to
                            },
                            "acquisitionMode": "IW",
                            "polarization": "DV"
                        },
                        "processing": {
                            "orthorectify": True,
                            "backCoeff": "SIGMA0_ELLIPSOID"
                        }
                    }
                ]
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {
                            "type": "image/tiff"
                        }
                    }
                ]
            },
            "evalscript": S1_VV_EVALSCRIPT
        }

    def generate_synthetic_raster(
        self,
        bbox: Tuple[float, float, float, float],
        filepath: str,
        width: int = 512,
        height: int = 512,
    ) -> str:
        """Generates a realistic synthetic Sentinel-1 Float32 GeoTIFF for local offline testing.
        
        Simulates radar backscatter in linear scale (0.001 to 0.25, corresponding to -30 dB to -6 dB).
        Includes a simulated water channel (Brahmaputra river feature) with lower backscatter.
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)

        # Base land backscatter (mean ~ 0.05 linear ≈ -13 dB with speckle noise)
        rng = np.random.default_rng(42)
        land_pixels = rng.gamma(shape=3.0, scale=0.018, size=(height, width)).astype(np.float32)

        # Create simulated river / water body channel with specular reflection (mean ~ 0.008 linear ≈ -21 dB)
        y, x = np.ogrid[:height, :width]
        channel_center = height // 2 + (np.sin(x / 40.0) * (height // 6)).astype(int)
        water_mask = np.abs(y - channel_center) < (height // 12)
        land_pixels[water_mask] = rng.gamma(shape=2.0, scale=0.004, size=np.count_nonzero(water_mask)).astype(np.float32)

        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(land_pixels, 1)

        return filepath

    def acquire_imagery(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        use_cache: bool = True,
        allow_fallback: bool = True,
    ) -> Tuple[str, str]:
        """Acquires a Sentinel-1 GeoTIFF for the specified bounding box.
        
        Returns:
            Tuple of (filepath, source_mode) where source_mode is 'cdse_live', 'cache', or 'synthetic_fallback'.
        """
        active_bbox = bbox or satellite_service.default_bbox
        satellite_service.validate_bbox(*active_bbox)

        # Determine time window: use provided, or query latest observation date from Module 2, or default to last 14 days
        if not time_from or not time_to:
            try:
                latest_obs = satellite_service.get_latest_sentinel1(bbox=active_bbox)
                if latest_obs and latest_obs.get("acquisition_start"):
                    dt = datetime.fromisoformat(latest_obs["acquisition_start"].replace("Z", "+00:00"))
                    time_from = (dt - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
                    time_to = (dt + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59Z")
            except Exception:
                pass

        if not time_from or not time_to:
            now = datetime.utcnow()
            time_from = (now - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00Z")
            time_to = now.strftime("%Y-%m-%dT23:59:59Z")

        # Cache file naming based on parameters hash
        cache_str = f"s1_{active_bbox}_{time_from}_{time_to}_{width}_{height}"
        cache_hash = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()[:12]
        filename = f"s1_vv_{cache_hash}.tif"
        filepath = os.path.join(self.cache_dir, filename)

        if use_cache and os.path.exists(filepath):
            return filepath, "cache"

        # Attempt live acquisition from CDSE Processing API
        try:
            token = self.get_auth_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "image/tiff",
                "Content-Type": "application/json",
            }
            payload = self.build_process_payload(active_bbox, time_from, time_to, width, height)
            response = requests.post(CDSE_PROCESS_URL, json=payload, headers=headers, timeout=40)

            if response.status_code == 200 and len(response.content) > 1000:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                return filepath, "cdse_live"
            else:
                error_msg = f"CDSE Process API returned {response.status_code}: {response.text[:200]}"
                if not allow_fallback:
                    raise ConnectionError(error_msg)
        except Exception as e:
            if not allow_fallback:
                raise e

        # Fallback to deterministic synthetic sample for testing/offline demo
        self.generate_synthetic_raster(active_bbox, filepath, width, height)
        return filepath, "synthetic_fallback"

    def inspect_raster(self, filepath: str) -> Dict[str, Any]:
        """Opens a GeoTIFF using Rasterio and extracts metadata and basic array statistics."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Raster file not found: {filepath}")

        with rasterio.open(filepath) as src:
            width = src.width
            height = src.height
            band_count = src.count
            crs_str = str(src.crs) if src.crs else "Unknown"
            transform = list(src.transform)[:6]
            bounds = {
                "left": float(src.bounds.left),
                "bottom": float(src.bounds.bottom),
                "right": float(src.bounds.right),
                "top": float(src.bounds.top),
            }
            dtype_str = src.dtypes[0] if src.dtypes else "unknown"

            # Read first band into NumPy array
            band1 = src.read(1)
            valid_mask = np.isfinite(band1) & (band1 > 0)
            valid_pixels = band1[valid_mask]

            if len(valid_pixels) > 0:
                stats = {
                    "min": round(float(np.min(valid_pixels)), 6),
                    "max": round(float(np.max(valid_pixels)), 6),
                    "mean": round(float(np.mean(valid_pixels)), 6),
                    "std": round(float(np.std(valid_pixels)), 6),
                    "valid_pixel_count": int(np.count_nonzero(valid_mask)),
                    "total_pixel_count": int(band1.size),
                }
            else:
                stats = {
                    "min": None,
                    "max": None,
                    "mean": None,
                    "std": None,
                    "valid_pixel_count": 0,
                    "total_pixel_count": int(band1.size),
                }

        return {
            "file_name": os.path.basename(filepath),
            "width": width,
            "height": height,
            "bands": band_count,
            "crs": crs_str,
            "transform": transform,
            "bounds": bounds,
            "dtype": dtype_str,
            "statistics": stats,
        }

    def acquire_and_inspect(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        width: int = 512,
        height: int = 512,
    ) -> Dict[str, Any]:
        """End-to-end pipeline: Acquires raster, inspects with Rasterio, and returns metadata."""
        filepath, source_mode = self.acquire_imagery(bbox=bbox, width=width, height=height)
        inspection = self.inspect_raster(filepath)
        inspection["source_mode"] = source_mode
        return inspection


# Singleton instance
sentinel1_acquisition_service = Sentinel1AcquisitionService()
