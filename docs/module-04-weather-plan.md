# Module 4: Weather Data Integration — Implementation Plan

## 1. Module Purpose

The purpose of **Module 4** is to integrate real-time, historical, and forecast meteorological data to provide **independent physical corroboration and hazard forecasting** for satellite-detected environmental disruptions.

While Sentinel-1 SAR (Module 3B) identifies surface backscatter attenuation (smooth water candidates), satellite imagery alone is a static snapshot that cannot reveal whether rainfall is ongoing, intensifying, or subsiding. Module 4 ingests high-resolution precipitation and weather metrics from **Open-Meteo** to:
1. **Corroborate SAR Flood Candidates**: Verify whether observed backscatter drops were accompanied by significant antecedent rainfall.
2. **Forecast Inundation Trends**: Project whether road-adjacent waterlogging is likely to escalate or clear over the next 24–48 hours.
3. **Enhance Logistics Decision-Making**: Supply actionable meteorological context for downstream road-risk scoring (Module 6) and dynamic dispatch routing (Module 7).

---

## 2. Why Weather Is Needed (Beyond Satellite Alone)

1. **Physical Corroboration**: SAR backscatter drops occur primarily over water, but can also occur over flat smooth sand, recently harvested paddies, or specular airport tarmacs. Heavy antecedent rainfall ($> 50\text{ mm}$) provides ground-truth corroboration that a detected change is genuinely flood-induced.
2. **Temporal Gap Bridging**: Sentinel-1 has a revisit cycle of 5–12 days over North Eastern India. Weather data updates hourly, allowing the system to track precipitation accumulation during the multi-day gaps between satellite passes.
3. **Predictive Risk Assessment**: Satellite imagery is retrospective (detects what already happened). Weather forecasts ($+24\text{h}/+48\text{h}$) enable proactive rerouting before a road is completely submerged.

---

## 3. Open-Meteo API Capabilities Investigated

Open-Meteo was investigated for its suitability, endpoints, and data offerings:

### Endpoints Investigated
* **Forecast API (`https://api.open-meteo.com/v1/forecast`)**:
  * Provides hourly and daily forecasts up to 16 days.
  * **Key Feature**: Supports the `past_days` parameter ($1$ to $92$ days). This allows retrieving **both historical rainfall (past 1–3 days) and forecast rainfall (next 1–3 days) in a single unified API request**, eliminating the need for separate archive requests for recent events.
* **Historical Weather Archive API (`https://archive-api.open-meteo.com/v1/archive`)**:
  * Provides reanalysis data (ERA5) for deep historical studies older than 3 months. Not needed for near-real-time operations.

### Parameter Support
* Coordinates: `latitude`, `longitude` (WGS84 float).
* Timezone: `timezone=Asia/Kolkata` or `auto`.
* Hourly variables: `precipitation`, `rain`, `showers`, `precipitation_probability`, `weather_code`, `temperature_2m`, `wind_speed_10m`.
* Daily variables: `precipitation_sum`, `precipitation_hours`, `precipitation_probability_max`, `weather_code`.

---

## 4. Recommended Weather Variables (Smallest Useful Dataset)

To keep the system lightweight, deterministic, and explainable, we select only variables with direct causal relationships to road inundation:

| Variable | Time Resolution | Purpose in Logistics Pipeline | Included in MVP? |
| :--- | :--- | :--- | :--- |
| **`precipitation`** (mm) | Hourly & Aggregated | Calculates cumulative rainfall ($\text{last\_24h}$, $\text{last\_48h}$, $\text{forecast\_24h}$) | **YES (Core)** |
| **`precipitation_sum`** (mm) | Daily | Quick multi-day total calculation | **YES (Core)** |
| **`weather_code`** (WMO) | Hourly / Current | Identifies severe weather (thunderstorms, heavy downpours) | **YES (Core)** |
| **`precipitation_probability_max`** (%) | Daily | Probability of sustained rain in upcoming forecast window | **YES (Supporting)** |
| `temperature_2m` | Hourly | Ambient temperature (minimal direct impact on riverine floods) | **NO (Excluded)** |
| `wind_speed_10m` | Hourly | Wind speed (relevant for coastal cyclones, secondary for NER valleys) | **NO (Excluded)** |
| `soil_moisture` / `river_discharge` | Daily | Global hydrological model (GloFAS); high latency, complex calibration | **NO (Post-MVP)** |

---

## 5. Historical vs. Forecast Weather Usage

The platform divides meteorological intelligence into two distinct operational roles:

```text
┌─────────────────────────────────────────────────────────────┐
│                 WEATHER USAGE ARCHITECTURE                  │
├──────────────────────────────┬──────────────────────────────┤
│     HISTORICAL RAINFALL      │      FORECAST RAINFALL       │
│      (Past 24h / 48h)        │       (Next 24h / 48h)       │
├──────────────────────────────┼──────────────────────────────┤
│ • Corroborates SAR changes   │ • Predicts hazard evolution  │
│ • Validates flood candidates │ • Proactive dispatch warning │
│ • Answers: "Did it rain?"    │ • Answers: "Will it worsen?" │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 6. Temporal Alignment with Sentinel-1 Observations

When evaluating a Sentinel-1 SAR acquisition at timestamp $T_{\text{sat}}$:

1. **Past 24-Hour Window ($T_{\text{sat}} - 24\text{h} \to T_{\text{sat}}$)**:
   * Captures acute flash downpours causing immediate surface waterlogging.
2. **Past 48-Hour Window ($T_{\text{sat}} - 48\text{h} \to T_{\text{sat}}$)**:
   * Captures antecedent ground saturation. In Assam's Brahmaputra alluvial plain, heavy 48h rainfall fills the soil water table, preventing drainage and causing runoff accumulation.
3. **Next 24-Hour Forecast ($T_{\text{sat}} \to T_{\text{sat}} + 24\text{h}$)**:
   * Determines whether the hazard is **ESCALATING** (continued heavy rain), **STABLE**, or **SUBSIDING** (dry forecast permitting route recovery).

---

## 7. Spatial Handling

### Evaluated Options
* **Option A: Bounding Box Center Point**: Computes $(\text{lat}_{\text{center}}, \text{lon}_{\text{center}})$ of the satellite AOI.
* **Option B: Multi-Point Spatial Grid**: Samples an $N \times N$ grid of weather points.
* **Option C: Polygon Centroid / Road Corridor Point**: Queries weather at the exact centroid of detected candidate polygons or along specific road corridors.

### Recommendation for MVP
**Hybrid Point/BBox-Center Design**:
* The core weather service accepts `(latitude, longitude)` coordinates or a bounding box `(min_lon, min_lat, max_lon, max_lat)`.
* For bounding boxes (e.g. Guwahati $50\text{ km} \times 50\text{ km}$ AOI), the service calculates the spatial centroid for a fast, single-call weather profile.
* When Module 6 evaluates specific road segments, it can query weather for the road segment centroid on demand.

---

## 8. API / Service Request Design

### Open-Meteo Request Strategy
We query the Open-Meteo Forecast endpoint using standard query parameters:
```http
GET https://api.open-meteo.com/v1/forecast?latitude=26.15&longitude=91.65&hourly=precipitation,weather_code&daily=precipitation_sum,precipitation_probability_max&past_days=2&forecast_days=2&timezone=Asia%2FKolkata
```

* **Single Request Efficiency**: In one HTTP GET request, we obtain:
  * 48 hours of past hourly precipitation ($-48\text{h} \to 0\text{h}$).
  * 48 hours of forecast hourly precipitation ($0\text{h} \to +48\text{h}$).
  * Daily summary metrics and WMO weather codes.

---

## 9. Expected Output Structure

Module 4 will expose a clean, structured JSON schema:

```json
{
  "location": {
    "latitude": 26.15,
    "longitude": 91.65,
    "timezone": "Asia/Kolkata"
  },
  "query_timestamp": "2026-09-20T17:30:00Z",
  "rainfall_metrics": {
    "past_24h_mm": 54.2,
    "past_48h_mm": 112.6,
    "forecast_24h_mm": 38.0,
    "forecast_48h_mm": 55.4,
    "current_weather_code": 65,
    "current_weather_description": "Heavy Rain",
    "is_severe_weather": true
  },
  "corroboration": {
    "support_level": "HIGH_SUPPORT",
    "rainfall_category": "HEAVY_RAINFALL",
    "forecast_trend": "ESCALATING",
    "explanation": "Past 48h rainfall of 112.6 mm strongly corroborates environmental inundation detected by Sentinel-1 SAR."
  },
  "status": "success",
  "source": "Open-Meteo"
}
```

### Corroboration Decision Matrix (Explainable Tiers)

| Past 48h Rainfall | Support Level | Physical Meaning |
| :--- | :--- | :--- |
| **$\ge 50\text{ mm}$** | `HIGH_SUPPORT` | Heavy monsoon downpour; strong physical corroboration of standing water |
| **$15\text{ mm} - 50\text{ mm}$** | `MODERATE_SUPPORT` | Moderate rainfall; plausible waterlogging in low-lying depressions |
| **$< 15\text{ mm}$** | `LOW_SUPPORT` | Low/no rainfall; candidate may be irrigation, wetland, or terrain shadow |

| Forecast 24h Rainfall | Forecast Trend | Operational Meaning |
| :--- | :--- | :--- |
| **$\ge 25\text{ mm}$** | `ESCALATING` | Inundation expected to worsen; avoid assigning non-critical supply routes |
| **$5\text{ mm} - 25\text{ mm}$** | `STABLE` | Inundation levels likely sustained; maintain caution |
| **$< 5\text{ mm}$** | `SUBSIDING` | Dry conditions; water expected to recede |

---

## 10. Error and Fallback Strategy

The logistics pipeline must be resilient to external API failures:

```text
Open-Meteo Available
        ↓
Return verified weather metrics + corroboration tier

Open-Meteo Timeout / Unreachable (HTTP 5xx / Network Error)
        ↓
1. Catch requests.exceptions.RequestException
2. Return graceful fallback object:
   {
     "status": "unavailable",
     "source": "fallback",
     "support_level": "UNKNOWN",
     "explanation": "Weather service temporarily offline; proceeding with satellite evidence only."
   }
3. Pipeline does NOT crash; Module 6 consumes fallback without disruption.
```

---

## 11. Configuration & Environment Variables

Open-Meteo free tier requires **no API keys or credentials**. The configuration footprint is minimal:

```env
# Weather Service Configuration (Optional overrides)
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/forecast
WEATHER_REQUEST_TIMEOUT_SECONDS=10
WEATHER_CACHE_TTL_SECONDS=1800
```

---

## 12. Security Considerations

* **No Secret Leakage**: Since no private keys are used, there are no credentials to leak.
* **Server-Side Proxy**: All external weather requests originate from the FastAPI backend. The frontend never makes direct third-party HTTP requests, preventing client-side network exposure.
* **Input Validation**: All coordinates are validated ($-90 \le \text{lat} \le 90$, $-180 \le \text{lon} \le 180$) prior to outgoing API queries.

---

## 13. Integration with Module 3B (Change Detection)

```text
Module 3B GeoJSON Output
(Candidate Polygons + BBox)
            │
            ▼
Module 4 Weather Service
(Query weather at BBox centroid / polygon centroid)
            │
            ▼
Enriched Hazard Assessment
- SAR mean backscatter drop: -10.97 dB
- Candidate Area: 12.16 km²
- Corroborating Past 48h Rain: 112.6 mm (HIGH_SUPPORT)
- Forecast 24h Rain: 38.0 mm (ESCALATING)
```

---

## 14. Integration with Future Road-Risk Assessment (Module 6)

In Module 6:
$$\text{Risk Score} = f(\text{SAR Inundation Extent}, \text{Antecedent Rainfall Tier}, \text{Forecast Trend}, \text{Road Hierarchy})$$

Weather acts as an explicit multiplier/modifier:
* A road flooded during `ESCALATING` heavy rain gets an immediate `CRITICAL / BLOCKED` status.
* A road with minor waterlogging under `SUBSIDING` weather gets a `CAUTION / PASSABLE_HIGH_CLEARANCE` status.

---

## 15. Limitations and Assumptions

1. **Resolution**: Open-Meteo global weather models (GFS / ECMWF) operate on a $\sim 11\text{ km} - 25\text{ km}$ spatial grid. Highly localized microclimate valley downpours are approximated.
2. **Upstream River Inundation**: Flooding in Assam can occasionally originate from heavy rainfall in upstream Arunachal Pradesh mountains even if local rainfall in Guwahati is modest. The system accounts for this by treating weather as **corroboration** rather than an absolute filter.

---

## 16. Suggested Implementation Steps (When Approved)

1. **Service Creation**: `backend/app/services/weather.py` with `OpenMeteoWeatherService` class.
2. **REST Endpoints**: `backend/app/api/weather.py`:
   * `GET /api/weather/current` (Point-based weather query)
   * `GET /api/weather/corroborate` (Bitemporal satellite corroboration query)
3. **Router Registration**: Attach router in `backend/app/main.py`.
4. **Unit Tests**: `backend/tests/test_weather.py` with mock network responses (deterministic tests).
5. **Live Integration Test**: Verify live Open-Meteo connection over Guwahati coordinates.
6. **Documentation Update**: `docs/module-04-weather.md` and `docs/architecture.md`.

---

## 17. How to Explain Module 4 to an SIH Judge

> *"Judges, satellite imagery gives us a spatial snapshot of where water is, but it cannot tell us whether the storm is passing or worsening. Module 4 integrates Open-Meteo weather intelligence.*
> 
> *Our service queries past 24-hour and 48-hour accumulated rainfall alongside next-day forecasts. When combined with Sentinel-1 SAR change detection, heavy antecedent rainfall provides ground-truth corroboration that detected backscatter drops are genuine floods rather than agricultural changes.*
> 
> *Furthermore, forecast rainfall informs our logistics dispatchers whether a compromised road segment is about to be completely submerged or will clear up shortly."*

---

## 18. Likely Judge Questions and Answers

### Q1: "Why use Open-Meteo instead of IMD (India Meteorological Department)?"
**Answer:** *"Open-Meteo provides an open, highly reliable JSON API without API key friction or restrictive rate limits, powered by ECMWF and global weather models. IMD radar data can be integrated as an additional secondary feed in future enterprise deployments."*

### Q2: "If there was no local rain, does your system automatically dismiss the flood candidate?"
**Answer:** *"No. In the Brahmaputra valley, downstream flooding can be caused by heavy rain in upstream mountain catchments. Zero local rain lowers the meteorological corroboration tier to `LOW_SUPPORT`, but the SAR physical detection remains active for human dispatcher review rather than being silently deleted."*

### Q3: "Do you combine satellite and rainfall using an arbitrary formula like 70% + 30%?"
**Answer:** *"No. Arbitrary percentage formulas lack scientific justification. Instead, we use transparent, explainable decision tiers: rainfall is categorized into physical thresholds ($\ge 50\text{ mm}$ for High Support) and trend classifications (`ESCALATING`, `STABLE`, `SUBSIDING`) that directly dictate logistics passability."*
