# Module 2: Satellite Data Acquisition

## 1. Purpose
This module connects the **NER Logistics Intelligence** backend to the **Copernicus Data Space Ecosystem (CDSE)** to search, discover, and acquire metadata for recent satellite observations over target areas in North Eastern India.

By obtaining observation metadata for both radar (Sentinel-1) and optical (Sentinel-2) satellites, the system establishes which satellite scenes are available for an area before downloading or processing heavy imagery in subsequent modules.

---

## 2. Technologies Used

* **Copernicus Data Space Ecosystem (CDSE)**: The official European Space Agency (ESA) Earth observation data portal. It provides access to Sentinel-1, Sentinel-2, and other satellite missions through standard REST OData and STAC APIs.
* **Sentinel-1 (SAR)**: Synthetic Aperture Radar constellation operated by ESA.
  * *Why we use it*: Primary sensor for environmental hazard monitoring (e.g., flood extent, water accumulation, terrain changes) because radar microwaves penetrate through cloud cover, rain, smoke, and operate day or night.
* **Sentinel-2 (MSI)**: Multi-Spectral Instrument (Optical) constellation operated by ESA.
  * *Why we use it*: Secondary visual confirmation sensor providing 13 spectral bands for land cover classification, vegetation analysis, and visual confirmation of ground conditions when skies are clear.
* **CDSE OData Protocol (REST)**: An open web standard for querying tabular and catalog data using standard HTTP GET parameters (`$filter`, `$orderby`, `$top`, `$expand`). We use direct HTTP queries via Python's `requests` library without needing bulky external SDKs.
* **FastAPI**: Exposes structured, asynchronous REST endpoints to allow the frontend and future analysis modules to query satellite availability on demand.

---

## 3. Why Sentinel-1? (SAR Concept)

### Why didn't we just use normal satellite images (like Google Maps or standard cameras)?
Standard optical satellites rely on visible sunlight reflecting off the Earth's surface. However, the North Eastern Region of India experiences extensive monsoon rainfall, dense cloud cover, and fog for months at a time. During active floods or severe storms, optical cameras capture only a white blanket of clouds, rendering them useless for immediate disaster monitoring.

**Sentinel-1 uses Synthetic Aperture Radar (SAR)**:
* **Active Microwave Sensing**: Sentinel-1 emits its own radar pulses (C-band microwaves, ~5.5 cm wavelength) and measures the backscattered signal reflected back from the ground.
* **Cloud & Night Penetration**: Microwave frequencies pass directly through clouds, rain, haze, and darkness unaffected.
* **Specular Reflection (Water Detection)**: Smooth water surfaces act like mirrors, reflecting radar waves away from the sensor (yielding a dark, low-backscatter signal). Rough land surfaces scatter radar waves back toward the sensor (yielding a bright signal). This sharp contrast makes SAR uniquely suited for flood detection.

---

## 4. Why Sentinel-2?

**Sentinel-2** serves as our complementary optical source:
* While Sentinel-1 detects water regardless of clouds, optical imagery from Sentinel-2 provides high-resolution color and multi-spectral bands (Red, Green, Blue, Near-Infrared).
* When cloud cover is low, Sentinel-2 allows visual verification of land-use changes, vegetation state (NDVI), and road visibility.
* Sentinel-2 includes metadata on cloud cover percentage (`cloud_cover_percentage`), allowing the system to determine whether optical data is usable or if the pipeline must rely solely on radar.

---

## 5. Input

1. **Geographic Bounding Box (`bbox`)**:
   * Coordinates: `(min_lon, min_lat, max_lon, max_lat)` in WGS84 decimal degrees (SRID 4326).
   * Default test area: Assam / Brahmaputra basin near Guwahati (`[91.50, 26.00, 92.00, 26.50]`).
2. **Date Range (Optional)**:
   * ISO 8601 timestamps (e.g., `2026-09-01T00:00:00Z`) to filter acquisitions within a specific historical window.
3. **Product Type / Filters (Optional)**:
   * Sentinel-1: `GRD` (Ground Range Detected), `SLC` (Single Look Complex), `RAW`.
   * Sentinel-2: `S2MSI2A` (Level-2A Bottom-Of-Atmosphere reflectance), `S2MSI1C` (Level-1C Top-Of-Atmosphere).
4. **Configuration & Credentials (`.env`)**:
   * `COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD` (optional for public metadata search, required for downloading full product scenes).
   * `DEFAULT_BBOX_*` coordinates.

---

## 6. Processing Flow

```text
Client Request (GET /api/satellite/sentinel-1/latest?min_lon=...&...)
        ↓
FastAPI Router (_parse_bbox_params in api/satellite.py)
        ↓
Satellite Service (backend/app/services/satellite.py)
        ↓
Validate Coordinates (-180..180, -90..90, min < max)
        ↓
Construct WKT Polygon string: POLYGON((lon lat, ...))
        ↓
Build OData query with $filter (Collection/Name, OData.CSC.Intersects)
        ↓
Send HTTPS GET to CDSE OData API (catalogue.dataspace.copernicus.eu)
        ↓
Parse raw OData JSON into clean domain model (_parse_product)
        ↓
FastAPI returns structured JSON to client
```

---

## 7. Output

The endpoint returns a structured JSON object containing verified observation metadata:

```json
{
  "status": "success",
  "data": {
    "satellite": "Sentinel-1",
    "product_id": "c90fa7a8-a8f7-41e1-88a1-2de5dff15659",
    "product_name": "S1D_IW_RAW__0SDV_20260918T115640_20260918T115713_004632_008A3D_8E85.SAFE",
    "acquisition_start": "2026-09-18T11:56:40.851066Z",
    "acquisition_end": "2026-09-18T11:57:13.250771Z",
    "publication_date": "2026-09-18T17:34:02.003402Z",
    "platform": "SENTINEL-1",
    "instrument": "SAR",
    "product_type": "IW_RAW__0S",
    "processing_level": "LEVEL0",
    "polarization": "VV&VH",
    "cloud_cover_percentage": null,
    "online": true,
    "content_length_bytes": 1024000,
    "footprint": {
      "type": "Polygon",
      "coordinates": [...]
    }
  }
}
```

For Sentinel-2, `cloud_cover_percentage` is populated (e.g., `98.72`).

---

## 8. Important Files

* `backend/app/services/satellite.py`: Houses the `CopernicusSatelliteService` class. Responsible for bounding box validation, WKT polygon generation, OData query construction, token authentication, and raw JSON parsing.
* `backend/app/api/satellite.py`: Houses FastAPI route controllers exposing `/api/satellite/sentinel-1/latest`, `/api/satellite/sentinel-2/latest`, and `/api/satellite/latest`. Validates query parameters and maps exceptions to HTTP status codes.
* `backend/app/main.py`: Registers the satellite router into the root FastAPI application.
* `backend/.env.example`: Provides a template for Copernicus configuration and default bounding boxes.
* `backend/tests/test_satellite.py`: Unit tests covering bounding box validation, WKT formatting, and JSON response parsing.

---

## 9. Important Functions

### `validate_bbox(min_lon, min_lat, max_lon, max_lat)` (`backend/app/services/satellite.py`)
* **Purpose**: Validates geographic bounding box coordinates against WGS84 standards.
* **Input**: 4 float coordinates.
* **Output**: Tuple of validated floats, or raises `ValueError`.
* **Why it matters**: Prevents malformed spatial queries from being sent to Copernicus.

### `search_products(collection, bbox, start_date, end_date, product_type, limit)` (`backend/app/services/satellite.py`)
* **Purpose**: Core querying method that communicates with the CDSE OData catalog endpoint.
* **Input**: Collection name (`SENTINEL-1` or `SENTINEL-2`), bounding box, optional filters, and record limit.
* **Output**: List of parsed, normalized product metadata dictionaries.
* **Why it matters**: Encapsulates external API communication away from HTTP route handlers.

### `_parse_product(raw_item, satellite)` (`backend/app/services/satellite.py`)
* **Purpose**: Flattens nested CDSE OData attributes into a clean, developer-friendly schema.
* **Input**: Raw dictionary from Copernicus API.
* **Output**: Normalized dictionary with standardized keys (`product_id`, `acquisition_start`, `instrument`, etc.).
* **Why it matters**: Isolates the rest of the application from external API schema changes.

### `get_latest_sentinel_1()` / `get_latest_sentinel_2()` (`backend/app/api/satellite.py`)
* **Purpose**: FastAPI route handlers exposing the latest observations over HTTP.
* **Input**: Query parameters (`min_lon`, `min_lat`, `max_lon`, `max_lat`, `product_type`).
* **Output**: Standardized JSON envelope `{"status": "success", "data": {...}}`.
* **Why it matters**: Provides the public interface for the frontend dashboard and downstream analysis services.

---

## 10. API Flow

```text
React Frontend / Client
           │
           │ HTTP GET /api/satellite/sentinel-1/latest?min_lon=91.5&min_lat=26.0...
           ▼
FastAPI Route (api/satellite.py)
           │
           │ Calls satellite_service.get_latest_sentinel1()
           ▼
Satellite Service (services/satellite.py)
           │
           │ Builds OData Intersects query
           ▼
Copernicus Data Space OData API (catalogue.dataspace.copernicus.eu)
           │
           │ Returns Product JSON
           ▼
Satellite Service parses attributes -> FastAPI -> HTTP 200 JSON Response
```

---

## 11. Limitations and Assumptions

* **Not a Real-Time Live Feed**: Satellites operate on orbital revisit schedules (typically 6 to 12 days per satellite constellation for a given point on Earth). Data represents observations from recent satellite passes, not instantaneous live video.
* **Observation Latency**: After satellite acquisition, raw data takes roughly 1 to 3 hours to be processed by ground stations and published to the CDSE catalog.
* **Metadata Only in Module 2**: This module discovers available satellite scenes and their parameters. Pixel-level raster processing (e.g. SAR backscatter analysis, water index calculation) will be handled in Module 3.
* **External Network Dependency**: Catalog availability depends on the uptime and responsiveness of the Copernicus Data Space servers.

---

## 12. How I Should Explain This to a Judge

> "In this module, we built the satellite data acquisition pipeline connecting our backend to the European Space Agency's Copernicus Data Space Ecosystem. 
> 
> We specifically integrate two satellite constellations: **Sentinel-1 SAR** and **Sentinel-2 Optical**. Sentinel-1 is our primary sensor because its Synthetic Aperture Radar penetrates heavy monsoon clouds and works at night, which is critical for disaster monitoring in the North East. Sentinel-2 acts as a complementary optical sensor for multi-spectral validation when skies are clear.
> 
> Our backend queries the Copernicus OData catalogue over a configurable geographic bounding box, validates the spatial bounds, and extracts structured metadata including acquisition timestamps, sensor mode, and cloud cover percentage. This enables our system to dynamically identify the latest available imagery before triggering downstream change-detection algorithms."

---

## 13. Realistic Judge Questions & Answers

**Q1: Why Sentinel-1 SAR instead of standard optical imagery from Google or Sentinel-2?**
> *Answer*: The North Eastern Region experiences persistent monsoon cloud cover and heavy rainfall during the very disaster events (floods, landslides) we need to monitor. Optical sensors cannot see through clouds. Sentinel-1 uses active C-band radar microwaves that penetrate clouds, rain, and darkness, providing uninterrupted surface monitoring regardless of weather.

**Q2: What role does Sentinel-2 play if Sentinel-1 already works through clouds?**
> *Answer*: Sentinel-2 provides high-resolution 13-band optical and infrared imagery. When cloud cover is low, it provides visual ground confirmation, vegetation index (NDVI) calculations, and cross-validation against the SAR water masks.

**Q3: Where does the satellite data come from and how do you access it?**
> *Answer*: Data is acquired directly from the official **Copernicus Data Space Ecosystem (CDSE)** using their standard REST OData catalogue API. We query products by intersecting a geographic bounding box polygon with the satellite track.

**Q4: Is this a continuous, real-time live satellite video stream?**
> *Answer*: No. Earth observation satellites in Sun-synchronous orbits pass over specific geographic coordinates on fixed revisit intervals (typically every few days). Our system queries the most recent observation metadata available for the region and processes each new scene as soon as it is published by ESA.

**Q5: What happens after you obtain this satellite metadata?**
> *Answer*: In the subsequent modules, the product ID and geometry identified in this module are used to fetch the relevant SAR image bands, compute backscatter change detection for flood extent, and spatially intersect those flood polygons with the OpenStreetMap road network to assess road closure risk.
