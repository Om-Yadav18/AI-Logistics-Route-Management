# Module 3 Pre-Check & Planning: Sentinel-1 Image Acquisition

> [!NOTE]
> **Status: PLANNING & FEASIBILITY REPORT (Module 3 is NOT yet implemented)**  
> This document details the technical investigation, comparison of Copernicus Data Space Ecosystem (CDSE) APIs, and the recommended architecture for acquiring Sentinel-1 SAR imagery for our SIH MVP.

---

## 1. Goal

To determine the most practical, robust, and scalable method for our FastAPI backend to acquire actual **Sentinel-1 SAR imagery** for a specific geographic area in North Eastern India (e.g., Guwahati / Brahmaputra basin), preparing for subsequent flood and environmental change detection.

---

## 2. Current Copernicus Data Space Ecosystem (CDSE) Ingestion Options

Under the official ESA Copernicus Data Space Ecosystem, three primary approaches exist for accessing satellite data:

### A. OData Catalogue & Direct Product Download
* **Mechanism**: Use the OData API (`https://catalogue.dataspace.copernicus.eu/odata/v1/Products(<UUID>)/$value`) to download complete product archives.
* **Format**: Full `.SAFE` format zipped archives.
* **Payload Size**: **1.0 GB to 1.6 GB per scene**.
* **Subset Capability**: No server-side spatial clipping. The entire satellite swath (~250 km × 200 km) must be downloaded.
* **Processing Burden**: Heavy client-side / backend processing required (unzipping, reading multi-gigabyte files, applying orbital files, radiometric calibration, terrain correction, and cropping).
* **MVP Feasibility**: **Poor for a live SIH demo**. Downloading 1.5 GB per query causes high network latency (minutes), disk bloat, and server memory bottlenecks.

---

### B. Sentinel Hub Processing API (CDSE Hosted)
* **Mechanism**: Send a `POST` request to `https://sh.dataspace.copernicus.eu/api/v1/process` with a targeted bounding box, time range, and an `evalscript`.
* **Format**: Clean, georeferenced **GeoTIFF** (`image/tiff`) containing calibrated SAR backscatter bands (VV, VH).
* **Payload Size**: **1 MB to 5 MB** (for a 512×512 or 1024×1024 pixel bounding box).
* **Subset Capability**: Native server-side spatial clipping to the exact bounding box requested.
* **Server-Side Preprocessing**: Cloud-side **orthorectification** (`orthorectify: true`), **radiometric calibration** (`SIGMA0_ELLIPSOID` or `GAMMA0_TERRAIN`), and speckle filtering.
* **Response Time**: **1 to 3 seconds**.
* **MVP Feasibility**: **Ideal for SIH MVP**. Ultra-fast, lightweight, standard GeoTIFF format directly readable with Python `rasterio`.

---

### C. STAC / Sentinel Hub Catalog API
* **Mechanism**: SpatioTemporal Asset Catalog (STAC) API (`https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search`).
* **Role**: **Discovery only**. Catalog/STAC is used to query scene metadata, overpass times, and footprints (comparable to what we built in Module 2 with OData), while the **Processing API** is used to retrieve and render the actual pixel arrays.

---

## 3. Comparative Analysis

| Criteria | Option 1: OData Product Download | Option 2: CDSE Processing API (Recommended) | Option 3: STAC + S3 Direct Access |
| :--- | :--- | :--- | :--- |
| **Output Data** | Raw `.SAFE.zip` complete scene | Calibrated GeoTIFF (VV/VH bands) | Raw COG / SAFE files from S3 |
| **Download Size** | 1,000 MB – 1,600 MB | **1 MB – 5 MB** | 500 MB – 1,000 MB |
| **Server-Side Clipping** | ❌ None (Full swath only) | ✅ **Exact bounding box** | ⚠️ Partial (range requests on COG) |
| **SAR Calibration** | ❌ Manual (Requires SNAP / GDAL) | ✅ **Automated cloud calibration** | ❌ Manual |
| **Latency per Request** | 3 – 10 minutes | **1 – 3 seconds** | 30 – 90 seconds |
| **Band Support** | All raw sub-swaths | Selected bands (`VV`, `VH`) | Single band COGs |
| **Complexity** | High (Heavy disk & memory) | **Low & Clean (Standard REST)** | High (AWS/Cloud credentials & S3 config) |
| **MVP Demonstration** | Risky (Too slow for live demo) | **Perfect (Instant responsive demo)** | Moderate |

---

## 4. Recommended Implementation Approach

### Primary Recommendation: **CDSE Sentinel Hub Processing API**

**Why this is the best choice for our project:**
1. **Speed & Demonstrability**: Live SIH judging requires fast response times. Generating a 2 MB calibrated GeoTIFF in 2 seconds enables a real-time dashboard, whereas downloading a 1.5 GB ZIP file would stall the application.
2. **Pre-calibrated Radiometry**: Sentinel-1 SAR raw measurements must be calibrated to backscatter values ($\sigma^0$ or $\gamma^0$) and terrain-corrected (orthorectified). The Processing API performs this on ESA's high-performance cloud servers, eliminating the need to install multi-gigabyte C++ tools (like ESA SNAP) in our Python environment.
3. **Exact Bounding Box Extraction**: Only the North Eastern road corridor / disaster region is queried, saving bandwidth and memory.
4. **Standard GeoTIFF Output**: The resulting TIFF is directly ingested into Python using `rasterio` and `numpy` for immediate flood thresholding in Module 3.

---

## 5. Exact Data Requirements for Flood & Water Detection

To detect surface water and environmental changes from Sentinel-1:

* **Product Type**: **Sentinel-1 GRD (Ground Range Detected)**
  * *Why*: GRD products have already converted raw complex phase signals into intensity images projected onto the ground ellipsoid.
* **Acquisition Mode**: **IW (Interferometric Wide Swath)**
  * *Why*: The default operational mode over land, covering 250 km swaths with 10-meter spatial resolution.
* **Polarizations**:
  * **VV (Vertical transmit, Vertical receive)**: Primary channel for water detection. Smooth open water produces strong specular reflection (away from sensor), resulting in very low backscatter values (dark pixels, typically < -15 dB to -18 dB).
  * **VH (Vertical transmit, Horizontal receive)**: Cross-polarization channel. Useful for distinguishing rough vegetated terrain and urban structures from water.
* **Spatial Resolution**: **10 meters per pixel**.
* **Radiometric Calibration**: **$\sigma^0$ (Sigma Nought)** or **$\gamma^0$ (Gamma Nought)** in decibels (dB) or linear backscatter.
* **Output Format**: **16-bit unsigned or 32-bit float GeoTIFF** with EPSG:4326 (WGS84) or EPSG:3857 coordinate reference system.

---

## 6. Authentication Requirements

To use the CDSE Processing API:
1. **Credentials Needed**:
   * An **OAuth Client** (Client ID & Client Secret) generated freely from the Copernicus Data Space Ecosystem user dashboard under *User Settings -> OAuth Clients*.
2. **Environment Variables**:
   ```ini
   # Copernicus Sentinel Hub Processing API Credentials
   CDSE_CLIENT_ID=your_client_id_here
   CDSE_CLIENT_SECRET=your_client_secret_here
   ```
3. **Token Endpoint**:
   `POST https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`
   with `grant_type=client_credentials`.
4. **Offline / Fallback Support**:
   For automated tests and offline demonstrations where internet or Copernicus quota may be unavailable, our service will include a local sample raster fallback so testing never breaks.

---

## 7. Proposed Module 3 Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│               Frontend / Analysis Trigger                   │
│         (Request Sentinel-1 Scene for Target BBox)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                                                             │
│  [1. Discovery Layer]                                       │
│  CopernicusSatelliteService.get_latest_sentinel1()          │
│  - Finds latest scene date & ID                             │
│                                                             │
│  [2. Acquisition Layer (NEW in Module 3)]                   │
│  Sentinel1AcquisitionService.fetch_raster(bbox, time_range) │
│  - Obtains OAuth token                                      │
│  - Posts evalscript to /api/v1/process                      │
│  - Receives calibrated VV/VH GeoTIFF                        │
│                                                             │
│  [3. Processing Layer (NEW in Module 3)]                    │
│  SARProcessor.analyze_water_extent(geotiff_path)            │
│  - Reads GeoTIFF using rasterio                             │
│  - Extracts VV backscatter array                            │
│  - Applies thresholding (e.g. Otsu or dB < -16 threshold)   │
│  - Produces binary water mask & GeoJSON polygons            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Georeferenced Hazard Output (GeoJSON)             │
│    { "type": "FeatureCollection", "features": [ ... ] }     │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Expected Python Dependencies for Module 3

When we begin implementation of Module 3, the minimal dependencies required will be:

1. **`rasterio`**: Reading, slicing, and saving georeferenced GeoTIFF raster arrays with spatial metadata (CRS, transform, bounds).
2. **`numpy`**: Fast matrix operations, array masking, and threshold computation on radar backscatter pixels.
3. **`requests`**: Already installed; used to execute the HTTP POST to the CDSE Process API.

*(GeoPandas and Shapely will be introduced in Module 6 for road network spatial intersection).*

---

## 9. Planned MVP Proof-of-Concept Test

When Module 3 development begins, the immediate validation milestone will be:
1. Send a request for a 10 km × 10 km test box in Assam.
2. Download and store a 1 MB GeoTIFF in `backend/data/cache/`.
3. Open the file with Python `rasterio`.
4. Verify and print:
   - Raster dimensions (e.g. `512 x 512`)
   - Coordinate Reference System (`EPSG:4326`)
   - Band count (Band 1: VV, Band 2: VH)
   - Value range (Valid backscatter amplitudes)

---

## 10. Risks & Mitigation

| Risk | Mitigation |
| :--- | :--- |
| **CDSE API rate limits or downtime** | Implement a local file-based raster cache so already-fetched scenes are re-used instantly without re-querying CDSE. |
| **Topographic distortions in hilly NER terrain** | Request `orthorectify: true` and `backCoeff: GAMMA0_TERRAIN` in the evalscript to eliminate terrain radar shadows. |
| **High cloud cover during demonstration** | Explain to judges that Sentinel-1 SAR is immune to clouds, proving our design choice. |
