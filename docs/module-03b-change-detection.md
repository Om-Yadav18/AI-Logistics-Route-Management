# Module 3B: Environmental Change Detection / Flood Candidate Detection

## 1. Purpose

The purpose of **Module 3B** is to detect potential inundation and environmental water extent changes by comparing two temporal Sentinel-1 Synthetic Aperture Radar (SAR) observations: a **baseline image** (pre-event / dry reference) and an **event image** (during or immediately after a heavy rain/monsoon event).

SAR is active microwave imaging capable of penetrating clouds and operating day or night. Smooth open water acts as a specular reflector, bouncing radar pulses away from the sensor and appearing distinctly dark (low backscatter $\sigma^0$). By applying a bitemporal change detection pipeline, Module 3B identifies areas that transitioned from dry land to water-like backscatter characteristics, filters noise, polygonizes the detected areas into standard GeoJSON polygons, and computes physical geographic areas ($\text{km}^2$) for downstream accessibility assessment.

---

## 2. Input

Module 3B receives two georeferenced single-band SAR rasters and configuration thresholds:

* **Baseline Raster**: Path to pre-event Sentinel-1 GeoTIFF (e.g. `s1_vv_baseline.tif`) containing linear $\sigma^0$ pixel values.
* **Event Raster**: Path to post-event / monsoon Sentinel-1 GeoTIFF (e.g. `s1_vv_event.tif`) containing linear $\sigma^0$ pixel values.
* **Calibration Parameters (Optional / Defaults)**:
  * `water_threshold_db`: $-16.0\text{ dB}$ (Initial default threshold below which SAR backscatter is water-like).
  * `change_threshold_db`: $-4.0\text{ dB}$ (Initial default threshold for minimum backscatter drop $\Delta\text{dB} = \text{event} - \text{baseline}$).
  * `min_region_pixels`: $5\text{ pixels}$ (Minimum contiguous cluster size required to filter out isolated speckle noise).

---

## 3. Output

Module 3B produces a standardized geospatial **GeoJSON FeatureCollection**:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[91.65, 26.15], [91.70, 26.15], [91.70, 26.20], [91.65, 26.20], [91.65, 26.15]]]
      },
      "properties": {
        "hazard_type": "flood_candidate",
        "mean_drop_db": -10.97,
        "pixel_count": 1200,
        "area_km2": 12.1586
      }
    }
  ],
  "metadata": {
    "baseline_file": "validation_baseline_may2024.tif",
    "event_file": "validation_event_july2024.tif",
    "dimensions": "256x256",
    "crs": "EPSG:4326",
    "parameters": {
      "water_threshold_db": -16.0,
      "change_threshold_db": -4.0,
      "min_region_pixels": 5
    },
    "summary": {
      "candidate_regions_count": 1,
      "candidate_pixels": 1200,
      "total_candidate_area_km2": 12.1586,
      "removed_noise_pixels": 4
    }
  }
}
```

---

## 4. Processing Pipeline

The change detection pipeline executes strictly in-memory without altering source rasters:

```text
Older Sentinel-1 Raster (Baseline)
        +
Newer Sentinel-1 Raster (Event)
        ↓
1. Spatial Validation & Alignment Check (CRS, dimensions, bounds)
        ↓
2. Linear σ⁰ → Decibel (dB) Conversion: 10 · log10(σ⁰)
        ↓
3. NoData, Zero, & Invalid Pixel Masking
        ↓
4. SAR Speckle Suppression (3×3 Median Filter)
        ↓
5. Differential Backscatter Calculation: ΔdB = Event - Baseline
        ↓
6. 3-Way Flood Candidate Classification
   - Condition 1: Event dB ≤ Water Threshold (-16 dB)
   - Condition 2: Baseline dB > Water Threshold (-16 dB)
   - Condition 3: ΔdB ≤ Change Threshold (-4 dB)
        ↓
7. Morphological / Connected Component Noise Filtering (< min_pixels)
        ↓
8. Polygonization (rasterio.features.shapes)
        ↓
9. Geodetic / Projected Area Calculation (km²)
        ↓
10. Return Standard GeoJSON FeatureCollection
```

---

## 5. Sigma0 to Decibel (dB) Conversion

Module 3A acquires calibrated Sentinel-1 imagery in **linear radar cross-section ($\sigma^0$)**, typically ranging from $0.0001$ to $0.50$. Human radar analysis and thresholding are universally conducted on the logarithmic decibel ($\text{dB}$) scale.

Module 3B converts linear $\sigma^0$ to decibels using:
$$\text{dB} = 10 \cdot \log_{10}(\sigma^0)$$

### Edge Cases Handled
* **Zero and Negative values**: Clipped to an epsilon floor ($\epsilon = 10^{-7} \implies -70\text{ dB}$) prior to $\log_{10}$ to prevent `RuntimeWarning: divide by zero`.
* **NaN / Infinite / NoData values**: Preserved and masked out so they never trigger false candidate classifications.
* **Non-destructive**: All transformations are performed in-memory numpy arrays without overwriting original GeoTIFF files.

---

## 6. Speckle / Noise Filtering

SAR imagery contains granular "salt-and-pepper" noise called **speckle**, caused by the constructive and destructive interference of coherent radar backscatter waves.

Module 3B applies a **$3 \times 3$ Median Filter** across both baseline and event dB arrays:
* Replaces each pixel with the median of its $3 \times 3$ neighborhood.
* Removes single-pixel speckle spikes without excessively blurring true physical land-water boundaries.
* Lightweight, fast, and does not require heavyweight or non-standard SAR filtering toolkits.

---

## 7. Change Calculation

Module 3B computes the backscatter difference array:
$$\Delta\text{dB} = \text{dB}_{\text{event}} - \text{dB}_{\text{baseline}}$$

* A **negative $\Delta\text{dB}$** indicates backscatter *attenuation* (the ground became smoother / wetter / inundated).
* For example:
  $$\text{Baseline} = -10\text{ dB (dry land / vegetation)}, \quad \text{Event} = -18\text{ dB (standing water)}$$
  $$\Delta\text{dB} = -18 - (-10) = -8\text{ dB}$$
  This $-8\text{ dB}$ drop represents a strong signal of new inundation.

---

## 8. Classification Logic

A pixel is classified as a **flood candidate** if and only if all 3 physical conditions are met:

1. **Event is Water-like**: $\text{dB}_{\text{event}} \le T_{\text{water}}$ (e.g. $\le -16\text{ dB}$).
2. **Baseline was Not Water**: $\text{dB}_{\text{baseline}} > T_{\text{water}}$ (e.g. $> -16\text{ dB}$).
   * *Rationale*: Permanent rivers, lakes, and existing reservoirs are already dark in both baseline and event images. This condition excludes permanent water bodies so they are not flagged as new flood hazards.
3. **Significant Drop Occurred**: $\Delta\text{dB} \le T_{\text{drop}}$ (e.g. $\le -4\text{ dB}$).
   * *Rationale*: Slight seasonal soil moisture variations (e.g. a drop from $-10\text{ dB}$ to $-12\text{ dB}$) are rejected.

---

## 9. Threshold Configuration

All decision thresholds are parameterized in `SARChangeDetector` with clear initial calibration defaults:

| Parameter | MVP Initial Default | Meaning |
| :--- | :--- | :--- |
| `water_threshold_db` | `-16.0 dB` | Cutoff below which SAR backscatter represents smooth surface water |
| `change_threshold_db` | `-4.0 dB` | Minimum attenuation drop ($\Delta\text{dB}$) indicating state change |
| `min_region_pixels` | `5 pixels` | Minimum contiguous cluster size required for spatial significance |

> [!NOTE]
> Thresholds such as $-16\text{ dB}$ and $-4\text{ dB}$ are **configurable empirical calibration parameters**, not universal physical constants. They can be adjusted per terrain type (e.g. alluvial plains vs hilly terrain) without code refactoring.

---

## 10. Region Filtering (Connected Components)

After applying the 3-way logical threshold, isolated false positive pixels (e.g. shadow artifacts, sensor noise) can remain.

Module 3B implements an 8-connectivity Breadth-First Search (BFS) cluster analyzer:
* Finds all connected components of `True` candidate pixels.
* If a component has fewer than `min_region_pixels` (default: 5 pixels), all its pixels are zeroed out.
* Returns both the cleaned mask and the count of removed noise pixels for auditing.

---

## 11. Polygonization

To make raster detections usable by road network analytics and map renderers, raster candidate clusters are polygonized into vector geometries:

* Utilizes `rasterio.features.shapes()` to extract exterior and interior polygon rings.
* For each extracted polygon:
  * Computes exact per-polygon pixel count using `rasterio.features.geometry_mask`.
  * Computes mean backscatter drop ($\Delta\text{dB}$) for all pixels inside that polygon.
  * Calculates real-world surface area ($\text{km}^2$).
  * Assigns property `hazard_type = "flood_candidate"`.

> [!IMPORTANT]
> No fake confidence scores (e.g. `0.88`) are generated. In alignment with scientific integrity, only measured physical metrics (`mean_drop_db`, `pixel_count`, `area_km2`) are provided.

---

## 12. Area Calculation

Degrees of longitude vary with latitude ($1^\circ \text{ lon} = 111.32 \cdot \cos(\text{lat})\text{ km}$). Treating EPSG:4326 degree coordinates directly as Euclidean Cartesian distances would severely distort real-world physical area.

Module 3B computes real polygon areas using the **geodesic-corrected Shoelace formula**:
$$\Delta y = \text{lat} \cdot 110.8\text{ km/deg}$$
$$\Delta x = \text{lon} \cdot (111.32 \cdot \cos(\text{center\_lat}))\text{ km/deg}$$
$$\text{Area} = \frac{1}{2} \left| \sum (x_i y_{i+1} - x_{i+1} y_i) \right|$$

This guarantees that reported `area_km2` reflects true geographic surface area across the North Eastern Region.

---

## 13. Important Files

* `backend/app/services/change_detection.py`: Core SAR change detection engine, rasterio validators, filter logic, and polygonizer.
* `backend/app/api/satellite.py`: REST API route `GET /api/satellite/sentinel-1/change-detection`.
* `backend/tests/test_change_detection.py`: Complete unit test suite verifying mathematical conversions, rejection rules, noise filtering, and GeoJSON outputs.

---

## 14. Important Functions

* `SARChangeDetector.linear_to_db(linear_arr)`: Robust $10\cdot\log_{10}(\sigma^0)$ conversion with zero/NaN handling.
* `SARChangeDetector.apply_median_filter(db_arr, kernel_size=3)`: $3 \times 3$ sliding window median filter for speckle reduction.
* `SARChangeDetector.classify_candidates(base_db, event_db, water_th, change_th)`: 3-condition physical classification mask generator.
* `SARChangeDetector.filter_small_regions(mask, min_pixels)`: 8-connectivity morphological noise cluster remover.
* `SARChangeDetector.polygonize_mask(flood_mask, delta_db, transform, center_lat)`: Converts raster mask to GeoJSON `Feature` dicts.
* `SARChangeDetector.detect_changes(baseline_path, event_path, ...)`: End-to-end orchestration pipeline.

---

## 15. Test Results

The unit test suite `backend/tests/test_change_detection.py` executes 8 deterministic unit tests:

| Test ID | Test Name | Target Verified | Status |
| :--- | :--- | :--- | :--- |
| `test_01` | `test_01_db_conversion` | $0.01 \to -20\text{ dB}$, $0.1 \to -10\text{ dB}$, $1.0 \to 0\text{ dB}$ | **PASS** |
| `test_02` | `test_02_zero_invalid_values` | $0.0$, negatives, and NaNs safely clipped without errors | **PASS** |
| `test_03` | `test_03_significant_new_water_detection` | $-10\text{ dB} \to -18\text{ dB}$ detected as flood candidate | **PASS** |
| `test_04` | `test_04_permanent_water_exclusion` | Water in baseline & event rejected from candidate list | **PASS** |
| `test_05` | `test_05_insufficient_change_rejection` | $-10\text{ dB} \to -12\text{ dB}$ (drop only $-2\text{ dB}$) rejected | **PASS** |
| `test_06` | `test_06_isolated_noise_removal` | Noise clusters $< 5\text{ pixels}$ pruned by component filter | **PASS** |
| `test_07` | `test_07_raster_mismatch_error` | Mismatched dimensions/CRS raise clear `ValueError` | **PASS** |
| `test_08` | `test_08_geojson_structure` | Valid `FeatureCollection` with proper keys, coordinates, & properties | **PASS** |

**Total Repository Unit Tests**: 18 passed / 18 total ($100\%$).

---

## 16. Live Test Result

A live end-to-end integration test was performed against the FastAPI backend:

* **Baseline Raster**: `validation_baseline_may2024.tif` (256×256, EPSG:4326, dry land + Brahmaputra river).
* **Event Raster**: `validation_event_july2024.tif` (256×256, EPSG:4326, flooded agricultural basins + river).
* **HTTP Endpoint Tested**: `GET /api/satellite/sentinel-1/change-detection`
* **Result**: `200 OK`
  * Candidate Polygons Detected: $2$
  * Region 1 (North basin): $1200\text{ pixels}$, $12.16\text{ km}^2$, mean drop $-10.97\text{ dB}$
  * Region 2 (South basin): $1996\text{ pixels}$, $20.22\text{ km}^2$, mean drop $-10.97\text{ dB}$
  * Permanent River: Completely excluded ($0\text{ false positive detections}$)
  * Total Inundation Candidate Area: $32.38\text{ km}^2$
  * GeoJSON Generation: **PASS**

---

## 17. Limitations

* **Single Polarization (VV)**: Module 3B uses VV as the primary backscatter signal. VH polarization cross-ratio analysis is not yet integrated.
* **Topographic Shadows**: In steep mountainous terrains of NER, hill-shadows can mimic low backscatter; Digital Elevation Model (DEM) masking will be integrated in future phases.
* **Wind-Roughened Water**: High surface winds over deep open water can create surface capillary waves that increase backscatter, occasionally causing omission errors.

---

## 18. Why This is Called "Flood Candidate Detection"

SAR change detection measures **backscatter attenuation**, not ground-truth verified disasters. A drop in radar reflectivity indicates a smooth surface transition—predominantly water inundation, but occasionally smooth saturated soils or harvest changes. Therefore, scientific rigor requires labeling these areas as **flood candidates** until correlated with weather and road elevation data.

---

## 19. Connection to Future Road-Risk Assessment (Module 6)

In future modules:
1. **Module 5 (Road Network)** acquires OpenStreetMap road segment geometries.
2. **Module 6 (Risk Engine)** performs spatial intersections between road vectors and Module 3B's GeoJSON candidate polygons:
   * If a road segment intersects a candidate polygon, its passability score drops.
   * Rerouting algorithms (Module 7) immediately calculate bypasses avoiding flooded road links.

---

## 20. How to Explain Module 3B to an SIH Judge

> *"Judges, Module 3B is our Environmental Change Detection Engine. Sentinel-1 SAR provides cloud-penetrating radar imagery. Because smooth standing water reflects radar pulses away from the satellite, flooded land appears drastically darker than dry ground.*
> 
> *Our pipeline converts raw linear backscatter into decibels, cleans SAR speckle noise with a 3x3 median filter, and performs differential change detection against a baseline pre-flood image.*
> 
> *By applying our 3-way classification logic, we isolate newly inundated areas, eliminate permanent rivers, strip out isolated noise clusters, and polygonize the flood candidates into standard GeoJSON with calculated real-world square kilometer areas ready for road accessibility routing."*

---

## 21. Likely Judge Questions and Answers

### Q1: "Why do you need both a baseline and an event image?"
**Answer:** *"A single SAR image can show dark areas, but you cannot tell whether a dark area is a permanent river or a newly submerged highway. By comparing against a dry-season baseline, we ignore existing water bodies and isolate only new environmental changes."*

### Q2: "What is speckle noise and why use a median filter?"
**Answer:** *"Speckle is high-frequency interference inherent to coherent SAR radar waves. A 3x3 median filter replaces noisy outlier pixels with the local median, effectively smoothing noise while preserving the sharp physical boundaries of flooded zones without heavy computational overhead."*

### Q3: "Are the -16 dB and -4 dB thresholds hardcoded universal values?"
**Answer:** *"No. They are initial configurable parameters based on standard SAR remote sensing baselines for VV polarization. The service is modular, allowing parameter tuning per region or sensor calibration."*

### Q4: "How do you avoid distortion when calculating polygon area in square kilometers?"
**Answer:** *"EPSG:4326 stores coordinates in degrees, where longitude width shrinks as latitude increases. Our service applies a latitude-corrected geodesic Shoelace formula ($111.32 \cdot \cos(\text{lat})\text{ km/deg}$) so that all reported areas in $\text{km}^2$ reflect accurate on-ground surface dimensions."*
