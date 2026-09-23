# Module 4: Weather Data Integration

## 1. Purpose

The purpose of **Module 4** is to integrate meteorological data from **Open-Meteo** to provide **independent physical corroboration and hazard forecasting** for satellite-detected environmental disruptions.

While Sentinel-1 SAR (Module 3B) identifies surface backscatter attenuation (smooth water candidates), satellite imagery is an isolated historical snapshot that cannot reveal whether rainfall is ongoing, intensifying, or subsiding. Module 4 ingests high-resolution precipitation and weather metrics from Open-Meteo to:
1. **Corroborate SAR Flood Candidates**: Verify whether observed backscatter drops were accompanied by significant antecedent rainfall.
2. **Forecast Inundation Trends**: Project whether road-adjacent waterlogging is likely to escalate or clear over the next 24–48 hours.
3. **Enhance Logistics Decision-Making**: Supply actionable meteorological context for downstream road-risk scoring (Module 6) and dynamic dispatch routing (Module 7).

---

## 2. Input

Module 4 receives geographic coordinates or bounding boxes along with optional temporal reference parameters:

* **Coordinates Query**:
  * `lat`: Target latitude ($-90.0 \le \text{lat} \le 90.0$, WGS84 float).
  * `lon`: Target longitude ($-180.0 \le \text{lon} \le 180.0$, WGS84 float).
* **Bounding Box Query (Optional alternative)**:
  * `min_lon`, `min_lat`, `max_lon`, `max_lat`: Regional corridor bounding coordinates.
* **Corroboration Reference (Optional)**:
  * `timestamp`: ISO-8601 string (e.g. `2024-07-15T06:00:00Z`) matching a specific Sentinel-1 satellite pass.
  * `past_days`: Lookback window (default: 2 days / 48 hours).
  * `forecast_days`: Projection window (default: 2 days / 48 hours).

---

## 3. Output

Module 4 produces a standardized JSON meteorological evidence payload:

```json
{
  "location": {
    "latitude": 26.1159,
    "longitude": 91.6757,
    "elevation_m": 51.0,
    "timezone": "GMT"
  },
  "reference_timestamp": "2026-09-20T12:00:00+00:00",
  "precipitation_summary": {
    "past_24h_mm": 6.8,
    "past_48h_mm": 7.5,
    "past_72h_mm": 15.6,
    "forecast_24h_mm": 0.6,
    "forecast_48h_mm": 0.6,
    "current_weather_code": 3,
    "current_weather_description": "Overcast",
    "is_severe_weather": false
  },
  "corroboration": {
    "support_level": "LOW_SUPPORT",
    "rainfall_category": "LOW_OR_NO_RAINFALL",
    "forecast_trend": "SUBSIDING",
    "explanation": "Low antecedent rainfall (7.5 mm in past 48h); detected SAR change may be due to upstream river surge, agricultural irrigation, or specular terrain."
  },
  "status": "success",
  "source": "Open-Meteo"
}
```

---

## 4. Processing Pipeline

```text
Incoming Coordinate / BBox / Satellite Timestamp
                     │
                     ▼
1. Input Validation & BBox Centroid Calculation
                     │
                     ▼
2. HTTP Query to Open-Meteo Forecast Endpoint
   (past_days=2, forecast_days=2, hourly=precipitation,weather_code)
                     │
                     ▼
3. Temporal Alignment & Precipitation Aggregation
   - Past 24h: [T_ref - 24h, T_ref]
   - Past 48h: [T_ref - 48h, T_ref]
   - Past 72h: [T_ref - 72h, T_ref]
   - Forecast 24h: [T_ref, T_ref + 24h]
   - Forecast 48h: [T_ref, T_ref + 48h]
                     │
                     ▼
4. WMO Weather Code Interpretation & Severe Weather Detection
                     │
                     ▼
5. Corroboration & Forecast Trend Classification
   (High / Moderate / Low Support & Escalating / Stable / Subsiding)
                     │
                     ▼
6. Return Standardized Weather Evidence Payload
```

---

## 5. Corroboration Classification Logic

To ensure full scientific transparency without black-box formulas, Module 4 classifies meteorological support using **explainable physical decision tiers**:

### Antecedent Rainfall Support Tiers
| Past 48h Rainfall | Support Level | Physical Interpretation |
| :--- | :--- | :--- |
| **$\ge 50.0\text{ mm}$** | `HIGH_SUPPORT` | Heavy monsoon precipitation; strongly corroborates ground inundation |
| **$15.0\text{ mm} - 50.0\text{ mm}$** | `MODERATE_SUPPORT` | Moderate rainfall; plausible waterlogging in low-lying terrain |
| **$< 15.0\text{ mm}$** | `LOW_SUPPORT` | Low/no rainfall; change may be upstream river surge or agricultural |

### Forecast Trend Tiers
| Forecast 24h Rainfall | Forecast Trend | Logistics Operational Meaning |
| :--- | :--- | :--- |
| **$\ge 25.0\text{ mm}$** | `ESCALATING` | Inundation expected to worsen; avoid assigning supply routes |
| **$5.0\text{ mm} - 25.0\text{ mm}$** | `STABLE` | Inundation sustained; maintain cautious transit |
| **$< 5.0\text{ mm}$** | `SUBSIDING` | Dry forecast; water expected to recede |

---

## 6. Error and Fallback Handling

If Open-Meteo is temporarily unreachable or times out:
1. `requests.exceptions.RequestException` is caught gracefully.
2. The service returns a fallback response with `status: "degraded"` and `support_level: "UNKNOWN"`.
3. Downstream satellite change detection and route evaluation proceed uninterrupted.

---

## 7. Important Files and Functions

* [`backend/app/services/weather.py`](file:///c:/Users/sarif/OneDrive/Desktop/SIH/NER/AI-Logistics-Route-Management/backend/app/services/weather.py):
  * `OpenMeteoWeatherService.get_weather_for_coordinates()`: Main entry point for point queries.
  * `OpenMeteoWeatherService.get_weather_for_bbox()`: Computes BBox center and retrieves regional weather.
  * `OpenMeteoWeatherService.process_weather_metrics()`: Calculates temporal accumulation windows.
  * `OpenMeteoWeatherService.classify_corroboration()`: Evaluates physical support tiers.
  * `OpenMeteoWeatherService.interpret_wmo_code()`: Maps WMO codes to descriptions and severe flags.
* [`backend/app/api/weather.py`](file:///c:/Users/sarif/OneDrive/Desktop/SIH/NER/AI-Logistics-Route-Management/backend/app/api/weather.py):
  * `GET /api/weather/current`: Point/BBox weather metrics.
  * `GET /api/weather/corroborate`: Satellite pass corroboration.
* [`backend/tests/test_weather.py`](file:///c:/Users/sarif/OneDrive/Desktop/SIH/NER/AI-Logistics-Route-Management/backend/tests/test_weather.py):
  * 8 automated unit tests covering accumulation windows, classification tiers, WMO codes, coordinate bounds, and network fallback.

---

## 8. Test Results

* **Unit Tests (`backend/tests/test_weather.py`)**: 8 passed / 8 total ($100\%$).
* **Repository-Wide Unit Tests**: 26 passed / 26 total ($100\%$).
* **Live Integration Test (`GET /api/weather/current` & `/api/weather/corroborate`)**: **PASS** (HTTP 200 OK with live data from Open-Meteo).

---

## 9. How to Explain Module 4 to an SIH Judge

> *"Judges, while Sentinel-1 SAR satellite imaging provides high-resolution maps of standing water, satellites pass only every few days. Module 4 integrates real-time Open-Meteo weather intelligence.*
> 
> *Our engine queries past 24-hour and 48-hour accumulated rainfall alongside next-day precipitation forecasts.*
> 
> *When combined with Sentinel-1 SAR change detection, heavy antecedent rainfall provides ground-truth corroboration that detected backscatter drops are genuine floods rather than agricultural changes. Furthermore, our 24-hour forecast trends inform emergency logistics dispatchers whether an inundated road corridor is escalating towards a complete block or is subsiding and safe for relief vehicles."*
