# NER Logistics Intelligence — System Architecture

## Overview
The **NER Logistics Intelligence** platform is an AI-powered system designed to ensure resilient supply chain and transportation access for essential goods (medicines, food, relief materials) across the North Eastern Region (NER) of India. The region frequently suffers from sudden logistical bottlenecks caused by heavy rainfall, landslides, floods, and remote connectivity blackouts.

---

## Target End-to-End Pipeline

```text
Satellite Data (Sentinel-1 SAR / Sentinel-2)
                 +
Weather Data (Precipitation / Forecasts)
                 ↓
Environmental Change & Hazard Detection
                 ↓
Road Risk Assessment Engine
                 ↓
Affected Road Segments Mapping (OSM)
                 ↓
Alternate Route Calculation (Graph Engine)
                 ↓
User Alerts & Logistics Dispatch
                 ↓
Offline Local Cache
                 ↓
Bluetooth / P2P Mesh Synchronization
                 ↓
Nearby Offline Devices in Blackout Zones
```

---

## Current Implementation Status

| Module | Name | Status | Key Components |
|---|---|---|---|
| **Module 1** | **Project Foundation** | **Completed** | FastAPI backend skeleton, CORS middleware, `/api/health` endpoint, React + Vite frontend foundation |
| **Module 2** | **Satellite Data Ingestion** | **Completed** | Copernicus Data Space OData integration, Sentinel-1 SAR & Sentinel-2 Optical metadata querying, spatial bounding box validation, `/api/satellite/*` endpoints |
| **Module 3A**| **Sentinel-1 Image Acquisition & Raster POC** | **Completed** | CDSE Sentinel Hub Processing API integration, targeted GeoTIFF streaming, Rasterio metadata extraction & NumPy backscatter statistics, `/api/satellite/sentinel-1/acquire` endpoint |
| **Module 3B**| **Environmental Change Detection / Flood Candidate Detection** | **Completed** | Bitemporal SAR differential analysis, linear $\sigma^0 \to \text{dB}$ conversion, $3\times3$ median speckle filtering, 3-condition classification, morphological component filtering, geodesic-corrected polygonization, `/api/satellite/sentinel-1/change-detection` endpoint |
| **Module 4** | **Weather Integration** | **Completed** | Open-Meteo precipitation & weather ingestion, antecedent rainfall accumulation (24h/48h/72h), short-term forecast trends (24h/48h), explainable corroboration tiers, `/api/weather/*` endpoints |
| **Module 5** | Road Network | **Implemented** | OpenStreetMap road ingestion, `MultiDiGraph` topology, GraphML caching, summary API |
| **Module 6** | Road Risk Assessment | Planned | Spatial intersection & hazard scoring |
| **Module 7** | Dynamic Routing | Planned | NetworkX/OSMnx re-routing around blocked segments |
| **Module 8** | Alert Generation | Planned | Logistics notification & dispatch payloads |
| **Module 9** | Offline Cache | Planned | Client-side structured storage with versioning |
| **Module 10** | Bluetooth / P2P Mesh | Planned | Device-to-device synchronization in offline zones |

---

## Architecture of Implemented Modules

### Implemented Architecture (Modules 1, 2, 3A, 3B, & 4)

```text
┌─────────────────────────────────────────────────────────────┐
│                     React + Vite Client                     │
│                    (http://localhost:5173)                  │
│  - App.jsx (Health monitor & connection status)             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ HTTP / JSON REST
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI ASGI Backend                     │
│                    (http://localhost:8000)                  │
│                                                             │
│  API Layer (app.api):                                       │
│  ├── /api/health (Health check)                             │
│  ├── /api/satellite/sentinel-1/latest (Latest SAR scene)    │
│  ├── /api/satellite/sentinel-1/acquire (GeoTIFF inspection) │
│  ├── /api/satellite/sentinel-1/change-detection (GeoJSON)   │
│  ├── /api/satellite/sentinel-2/latest (Latest Optical)      │
│  ├── /api/satellite/latest (Combined summary)               │
│  ├── /api/weather/current (Precipitation & current weather) │
│  └── /api/weather/corroborate (Satellite pass corroboration)│
│                                                             │
│  Service Layer (app.services):                              │
│  ├── CopernicusSatelliteService (Catalogue discovery)       │
│  ├── Sentinel1AcquisitionService (Processing API & Rasterio)│
│  ├── SARChangeDetector (Bitemporal SAR change & polygonizer)│
│  └── OpenMeteoWeatherService (Precipitation & corroboration)│
│                                                             │
│  Storage & Cache:                                           │
│  └── backend/data/cache/ (Calibrated GeoTIFF rasters)       │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                │ HTTPS OData / Processing API │ HTTPS REST
                ▼                              ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│    CDSE Copernicus APIs      │ │       Open-Meteo API       │
│  - Sentinel-1 SAR Metadata   │ │  - Hourly Precipitation    │
│  - Calibrated GeoTIFF Stream │ │  - Forecast Trends & WMO   │
└──────────────────────────────┘ └────────────────────────────┘
```
