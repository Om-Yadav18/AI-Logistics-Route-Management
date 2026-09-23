# Frontend Testing Shell (Modules 1–4) — Documentation

## 1. Purpose

The purpose of this frontend implementation is to provide a **minimal, functional engineering testing dashboard** to manually trigger, inspect, and demonstrate the backend capabilities implemented across **Modules 1 through 4**:
* **Module 1**: FastAPI foundation & system health check.
* **Module 2**: Copernicus Sentinel-1 and Sentinel-2 satellite metadata discovery.
* **Module 3A**: Sentinel-1 SAR calibrated raster streaming & inspection.
* **Module 3B**: Sentinel-1 bitemporal change detection & flood candidate polygonization.
* **Module 4**: Open-Meteo precipitation accumulation, weather conditions, and meteorological corroboration.

> [!NOTE]
> This interface is an **engineering testing prototype**, not the final SIH end-user UI. It prioritizes functionality, clear data inspection, and deterministic manual verification over decorative styling.

---

## 2. Frontend Architecture

The frontend is built on **React 18** and bundled with **Vite 6**:

```text
frontend/
├── src/
│   ├── api.js       # Centralized API client & endpoint helpers
│   ├── app.jsx      # Single-page testing dashboard & formatted results console
│   └── main.jsx     # React root entrypoint
├── index.html       # HTML shell
├── package.json     # Scripts & dependencies (React, React-DOM, Vite)
└── vite.config.js   # Vite development server configuration (port 5173)
```

---

## 3. API Communication Flow

```text
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend Client                    │
│                    (http://127.0.0.1:5173)                  │
│                                                             │
│  [UI Controls: BBox / Params]   [Interactive Action Buttons]│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ fetch() via src/api.js
                               │ Base: import.meta.env.VITE_API_BASE_URL
                               │       || 'http://127.0.0.1:8000'
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Server                   │
│                    (http://127.0.0.1:8000)                  │
│                                                             │
│  ├── /api/health                                            │
│  ├── /api/satellite/sentinel-1/latest                       │
│  ├── /api/satellite/sentinel-2/latest                       │
│  ├── /api/satellite/latest                                  │
│  ├── /api/satellite/sentinel-1/acquire                      │
│  ├── /api/satellite/sentinel-1/change-detection             │
│  ├── /api/weather/current                                   │
│  └── /api/weather/corroborate                               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ JSON Response
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Formatted Results Console                   │
│  - Candidate Polygons Table (Area, Pixel Count, Drop dB)    │
│  - Weather Corroboration Tiers & Forecast Trends            │
│  - Satellite Raster Statistics & Metadata                   │
│  - Optional "Raw JSON" Inspector Toggle                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Components Created & Modified

1. **[`frontend/src/api.js`](file:///c:/Users/sarif/OneDrive/Desktop/SIH/NER/AI-Logistics-Route-Management/frontend/src/api.js)**:
   - Centralized network request handler.
   - Automatically handles parameter serialization and network/HTTP error translation.
2. **[`frontend/src/app.jsx`](file:///c:/Users/sarif/OneDrive/Desktop/SIH/NER/AI-Logistics-Route-Management/frontend/src/app.jsx)**:
   - **System Status Card**: `Check System` button and live status badge.
   - **Satellite Data Card**: Configurable BBox inputs with buttons for Sentinel-1, Sentinel-2, Combined Latest, and SAR raster acquisition.
   - **SAR Change Detection Card**: Configurable baseline/event raster paths, water threshold ($-16\text{ dB}$), drop threshold ($-4\text{ dB}$), and region size ($5\text{ px}$).
   - **Weather Card**: Latitude/Longitude inputs with buttons for Current Weather and Historical Corroboration.
   - **Formatted Results Console**: Renders structured tables, metric summary cards, and raw JSON toggle.

---

## 5. API Endpoints Used

| Section | Button Label | Endpoint Called | Parameters Sent |
| :--- | :--- | :--- | :--- |
| **System** | `Check System` | `GET /api/health` | None |
| **Satellite** | `Get Sentinel-1` | `GET /api/satellite/sentinel-1/latest` | `min_lon`, `min_lat`, `max_lon`, `max_lat` |
| **Satellite** | `Get Sentinel-2` | `GET /api/satellite/sentinel-2/latest` | `min_lon`, `min_lat`, `max_lon`, `max_lat` |
| **Satellite** | `Get Latest Satellite Data`| `GET /api/satellite/latest` | `min_lon`, `min_lat`, `max_lon`, `max_lat` |
| **Satellite** | `Acquire Sentinel-1 Raster`| `GET /api/satellite/sentinel-1/acquire` | `min_lon`, `min_lat`, `max_lon`, `max_lat`, `width`, `height` |
| **Change Detection** | `Run Change Detection` | `GET /api/satellite/sentinel-1/change-detection` | `baseline_file`, `event_file`, `water_threshold_db`, `change_threshold_db`, `min_region_pixels` |
| **Weather** | `Get Current Weather` | `GET /api/weather/current` | `lat`, `lon` |
| **Weather** | `Check Weather Corroboration` | `GET /api/weather/corroborate` | `lat`, `lon` |

---

## 6. State Management Approach

The application uses lightweight standard React state hooks (`useState`, `useEffect`) scoped within `App`:
* `health`, `healthLoading`, `healthError`: Backend connection health state.
* `bbox`: Bounding box query coordinates (default: Assam / Guwahati corridor `91.50, 26.00, 92.00, 26.50`).
* `changeParams`: Baseline raster, event raster, and SAR detection thresholds.
* `coords`: Coordinates for weather queries (default: `26.15 N, 91.65 E`).
* `resultData`, `loading`, `error`: Active execution payload displayed in the results console.
* `showRawJson`: Toggle between formatted cards/tables and raw JSON.

---

## 7. Error Handling

* **Network Unreachable**: If the backend is not running at `http://127.0.0.1:8000`, the API helper catches the network failure and displays an informative banner: `"Unable to connect to backend at http://127.0.0.1:8000. Ensure FastAPI is running."`
* **HTTP 4xx/5xx Errors**: Extracts backend error details (`detail` field) and renders them in an inline error box without crashing.
* **Loading Spinners**: Disables buttons and displays an active progress indicator during in-flight network requests.

---

## 8. How to Run the Frontend

1. Ensure the FastAPI backend is running:
   ```bash
   cd backend
   ..\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Start the Vite development server:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open `http://127.0.0.1:5173/` in your browser.

---

## 9. How to Test Each Feature

1. **System Health**: Click `Check System`. Verify the badge turns green (`Connected`) and shows version `1.0.0`.
2. **Current Weather**: Click `Get Current Weather`. Verify the console displays elevation, live condition, and past 24h/48h/72h rainfall.
3. **Weather Corroboration**: Click `Check Weather Corroboration`. Verify the support tier (`HIGH_SUPPORT`, `MODERATE_SUPPORT`, or `LOW_SUPPORT`) and forecast trend (`ESCALATING`, `STABLE`, or `SUBSIDING`) appear.
4. **Change Detection**: Click `Run Change Detection`. Verify the candidate polygons table lists detected candidate regions with area $\text{km}^2$, pixel count, mean drop dB, and label `Environmental / Flood Candidates`.
5. **Sentinel-1 Raster**: Click `Acquire Sentinel-1 Raster`. Verify raster statistics (min, max, mean, valid pixel count) render.
6. **Raw JSON Toggle**: Click `Raw JSON` to inspect the underlying raw JSON payload.

---

## 10. Current Limitations & What Is Intentionally NOT Implemented Yet

* **No Road Network**: OpenStreetMap road graph ingestion (Module 5) is not yet integrated.
* **No Road Risk Scoring**: Spatial intersection of roads with flood polygons (Module 6) is not yet integrated.
* **No Dynamic Routing**: Dijkstra / A* route calculation (Module 7) is not yet integrated.
* **No Offline Cache / P2P**: IndexedDB storage and Bluetooth mesh synchronization (Modules 9 & 10) are planned for later stages.
* **No Heavy Map Library**: Kept lightweight without Mapbox/Leaflet dependencies for rapid testing.
