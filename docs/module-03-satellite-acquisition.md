# Module 3: Sentinel-1 Image Acquisition & Raster Inspection

## 1. Purpose
The purpose of this module is to acquire actual Sentinel-1 Synthetic Aperture Radar (SAR) imagery for a targeted geographic bounding box in North Eastern India and inspect its georeferenced raster properties (dimensions, Coordinate Reference System, affine transform, and pixel backscatter statistics) using **Rasterio** and **NumPy**.

This establishes the foundational raster ingestion pipeline needed before executing pixel-level flood segmentation and environmental hazard classification in subsequent steps.

---

## 2. Why We Use the Processing API Instead of Downloading Full `.SAFE` Archives

| Aspect | OData `.SAFE.zip` Download | CDSE Sentinel Hub Processing API |
|---|---|---|
| **Data Size** | **1,000 MB – 1,600 MB** per scene | **1 MB – 5 MB** for targeted bounding box |
| **Spatial Scope** | Full unclipped 250 km satellite swath | Exact user-specified bounding box |
| **Preprocessing Required** | Complex (Requires SNAP/GDAL for calibration & terrain correction) | **Cloud-side automatic orthorectification & $\sigma^0$ calibration** |
| **Request Latency** | 3 to 10 minutes | **Fast REST response (seconds)** |
| **SIH Demonstration** | Impractical (High risk of network timeouts) | **Responsive, lightweight, and robust** |

---

## 3. Authentication Flow
The service supports two authentication methods with the Copernicus Data Space Ecosystem Keycloak server (`https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`):
1. **OAuth Client Credentials (`grant_type=client_credentials`)**: Using `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` configured in `.env`.
2. **Password Grant (`grant_type=password`)**: Using `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD` with `client_id=cdse-public`.
3. **Offline / Fallback Simulation**: If remote CDSE credentials are missing or the upstream server is unavailable, the service deterministically generates a local calibrated SAR GeoTIFF so testing and demonstration never fail.

---

## 4. How Module 2 Connects to Module 3

```text
Module 2 (Catalogue Discovery)
  - Queries Copernicus OData catalog for target BBox
  - Identifies latest observation date (e.g., 2026-09-18T11:56:40Z)
        ↓
Module 3 (Targeted Acquisition & Inspection)
  - Uses observation timestamp to establish tight date filter window
  - Sends bounding box & VV evalscript to CDSE Processing API
  - Streams GeoTIFF into backend/data/cache/
  - Inspects GeoTIFF with Rasterio & NumPy
```

---

## 5. Processing API Request Flow

```text
Client Request (GET /api/satellite/sentinel-1/acquire?min_lon=91.5&...)
        ↓
FastAPI Router (_parse_bbox_params in api/satellite.py)
        ↓
Sentinel1AcquisitionService.acquire_and_inspect()
        ↓
Query latest acquisition timestamp from satellite_service
        ↓
Build Processing API Payload (IW mode, VV band, SIGMA0_ELLIPSOID, image/tiff)
        ↓
POST to https://sh.dataspace.copernicus.eu/api/v1/process
        ↓
Save GeoTIFF to backend/data/cache/
        ↓
Open with rasterio.open() -> Extract metadata & band 1 array
        ↓
Compute NumPy statistics (min, max, mean, std)
        ↓
Return structured JSON to Client
```

---

## 6. What is a GeoTIFF?
A **GeoTIFF** is an industry-standard raster file format (TIFF) that embeds geographic metadata directly into the image tags:
* **Coordinate Reference System (CRS)**: Tells GIS software which projection is used (e.g., `EPSG:4326` for WGS84 latitude/longitude).
* **Affine Geotransform**: A 6-element matrix mapping pixel coordinates `(col, row)` to real-world geographic coordinates `(longitude, latitude)`.
* **Pixel Resolution**: Defines the real-world distance represented by each individual pixel.
* **Physical Value Encoding**: Unlike 8-bit PNGs or JPEGs (0–255 color values), SAR GeoTIFFs store physical measurement arrays (32-bit floating-point backscatter intensity $\sigma^0$).

---

## 7. What Does Rasterio Do?
**Rasterio** is a Python library for reading, writing, and transforming geospatial raster datasets:
* It reads the GeoTIFF binary header, extracting spatial metadata without decompressing the entire file unnecessarily.
* It reads the radar band data into a standard **NumPy N-dimensional array** (`numpy.ndarray`).
* It enables spatial slicing, reprojection, affine coordinate translation, and fast array operations.

---

## 8. Important Files

* `backend/app/services/sentinel1_acquisition.py`: Core acquisition service. Handles token authentication, payload building, GeoTIFF file caching, synthetic sample fallback generation, and Rasterio metadata inspection.
* `backend/app/api/satellite.py`: Exposes `GET /api/satellite/sentinel-1/acquire` with parameter validation and error mapping.
* `backend/requirements.txt`: Updated to include `rasterio` and `numpy`.
* `backend/.env.example`: Updated with `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`.
* `backend/tests/test_sentinel1_acquisition.py`: Unit tests verifying payload construction, GeoTIFF creation, Rasterio inspection, and error handling.

---

## 9. Important Functions & Classes

### `Sentinel1AcquisitionService` (`backend/app/services/sentinel1_acquisition.py`)
* `get_auth_token()`: Authenticates against Keycloak token endpoint and returns Bearer token.
* `build_process_payload(bbox, time_from, time_to, width, height)`: Constructs the Sentinel Hub Process API request body with `sentinel-1-grd`, `IW` mode, and `SIGMA0_ELLIPSOID`.
* `generate_synthetic_raster(bbox, filepath, width, height)`: Creates a realistic synthetic Float32 GeoTIFF with water channel features for testing/offline scenarios.
* `acquire_imagery(bbox, time_from, time_to, width, height)`: Acquires the GeoTIFF (from cache, live CDSE, or fallback generator) and saves to disk.
* `inspect_raster(filepath)`: Opens the GeoTIFF with `rasterio` and extracts dimensions, CRS, affine transform, bounds, data type, and NumPy pixel statistics.
* `acquire_and_inspect(bbox, width, height)`: End-to-end orchestration returning structured metadata.

### `acquire_sentinel_1_raster()` (`backend/app/api/satellite.py`)
* FastAPI endpoint handler for `GET /api/satellite/sentinel-1/acquire`.

---

## 10. Input
* **Bounding Box**: `min_lon`, `min_lat`, `max_lon`, `max_lat` (WGS84 degrees). Default: Assam test area `[91.50, 26.00, 92.00, 26.50]`.
* **Raster Dimensions**: `width`, `height` (default: 512×512 pixels).

---

## 11. Output
```json
{
  "success": true,
  "data": {
    "file_name": "s1_vv_4b90de05f6d9.tif",
    "width": 256,
    "height": 256,
    "bands": 1,
    "crs": "EPSG:4326",
    "transform": [0.001953125, 0.0, 91.5, 0.0, -0.001953125, 26.5],
    "bounds": {
      "left": 91.5,
      "bottom": 26.0,
      "right": 92.0,
      "top": 26.5
    },
    "dtype": "float32",
    "statistics": {
      "min": 0.000063,
      "max": 0.306062,
      "mean": 0.046608,
      "std": 0.033327,
      "valid_pixel_count": 65536,
      "total_pixel_count": 65536
    },
    "source_mode": "cdse_live"
  }
}
```

---

## 12. Error Handling
* **Missing/Invalid Credentials**: Catches authentication errors cleanly and returns `401 Unauthorized` without leaking secrets.
* **Invalid Bounding Box**: Validates coordinate ranges (e.g. `min_lon >= max_lon`) and returns `400 Bad Request`.
* **Network Timeouts**: Catches upstream timeouts and returns `504 Gateway Timeout`.
* **Corrupt/Unreadable Raster**: Catches `RasterioIOError` and returns `500 Internal Server Error`.

---

## 13. Testing
* **Unit Tests (`backend/tests/test_sentinel1_acquisition.py`)**:
  * Payload construction validation.
  * GeoTIFF generation and Rasterio inspection.
  * Bounding box error handling.
  * Credential validation.
* **Live API Verification**:
  * Tested `GET http://127.0.0.1:8000/api/satellite/sentinel-1/acquire` -> `200 OK` with full raster metadata returned.

---

## 14. Current Limitations
* Imagery acquisition is constrained to the bounding box requested.
* Single-band `VV` polarization is currently acquired for initial backscatter verification; `VH` band can be added when dual-polarization analysis is required.
* Raster caching is file-based on local disk.

---

## 15. What is Intentionally NOT Implemented Yet
* **Pixel-level flood segmentation / thresholding** (Deferred to next module).
* **Vector polygonization / GeoJSON hazard generation** (Deferred to next module).
* **Road network spatial intersection** (Belongs to Module 6).
* **Dynamic routing** (Belongs to Module 7).

---

## 16. How to Explain This Module to an SIH Judge
> "In this module, we established our Sentinel-1 imagery acquisition pipeline. Rather than downloading massive 1.5 GB raw satellite archives that would stall our application, our backend communicates with the Copernicus Sentinel Hub Processing API to request a cloud-calibrated, orthorectified GeoTIFF cropped to our exact disaster evaluation corridor. We then use **Rasterio** to ingest the GeoTIFF, extract its spatial affine geotransforms and Coordinate Reference System, and load the radar backscatter intensity band into **NumPy** arrays for downstream change detection."

---

## 17. Likely Judge Questions & Technically Accurate Answers

**Q1: What is the difference between what you did in Module 2 vs. Module 3?**
> *Answer*: Module 2 used the Copernicus OData Catalogue to search and discover metadata (identifying which satellite scenes exist and when they were captured). Module 3 uses the Copernicus Processing API to retrieve the actual calibrated pixel data as a georeferenced GeoTIFF and inspects its numerical raster properties using Rasterio.

**Q2: What is a Sentinel-1 GRD product?**
> *Answer*: GRD stands for Ground Range Detected. In raw SAR data (SLC), signals contain complex phase and range information. In GRD products, ESA has already converted complex phase amplitudes into multi-looked intensity images projected onto the ground surface, making them ready for spatial analysis.

**Q3: Why is a GeoTIFF better than a PNG or JPEG for satellite analysis?**
> *Answer*: PNG and JPEG only store 8-bit visual color triplets (0–255) with no geographic context. A GeoTIFF stores 32-bit floating-point physical radar backscatter values along with embedded Coordinate Reference System (CRS) data and an affine transform matrix that maps every pixel directly to latitude and longitude.

**Q4: How does Rasterio bridge satellite data to your AI / risk algorithms?**
> *Answer*: Rasterio reads the binary GeoTIFF and converts the raster bands directly into NumPy numerical arrays while maintaining the affine geographic projection matrix. This allows us to perform matrix thresholding and spatial array operations in Python.

**Q5: What are the backscatter values represented in your pixel statistics?**
> *Answer*: The pixel statistics represent linear $\sigma^0$ (Sigma Nought) radar backscatter intensity. Low values (near zero) correspond to smooth water bodies where radar pulses bounce away, while higher values correspond to rough land, vegetation, and built-up structures.
