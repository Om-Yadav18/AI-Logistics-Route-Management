# Module 3B Planning: Environmental Change Detection (Flood Candidate Detection)

> [!NOTE]
> **Status: PLANNING DOCUMENT ONLY (Module 3B is NOT yet implemented)**  
> This document details the technical investigation, algorithmic design, mathematical formulation, and implementation blueprint for Sentinel-1 SAR change detection and flood candidate identification for SIH 2026.

---

## 1. Module Purpose
The objective of Module 3B is to take two co-registered Sentinel-1 SAR rasters acquired in Module 3A:
1. **Observation A (Baseline / Pre-Disaster Scene)**
2. **Observation B (Event / Crisis Scene)**

and perform pixel-wise comparative radar backscatter analysis to identify **newly inundated / flooded candidate areas** while ignoring permanent water bodies (rivers, lakes) and radar noise. The output will be georeferenced GeoJSON polygons and raster masks ready to intersect with OpenStreetMap road networks in Module 6.

---

## 2. Current Module 3A Input Baseline

From the Module 3A audit, our backend already produces:
* **Product**: `sentinel-1-grd` (Ground Range Detected), Interferometric Wide (`IW`) mode.
* **Polarization**: Single-channel **`VV`** (Vertical transmit, Vertical receive).
* **Radiometric Calibration**: Linear $\sigma^0$ (Sigma Nought) on ellipsoid (`SIGMA0_ELLIPSOID`).
* **Orthorectification**: Enabled (`orthorectify: true`).
* **Coordinate System**: `EPSG:4326` (WGS84).
* **Grid Consistency**: When queried with the same bounding box and width/height, Observation A and Observation B share the **exact same affine transform matrix, bounding box, and pixel grid**, enabling direct 1-to-1 matrix operations in NumPy without resampling.

---

## 3. Investigation of Change-Detection Algorithms

### A. Single-Image Absolute dB Thresholding
* **Concept**: Convert a single post-event scene to decibels ($\text{dB}$) and classify any pixel where $\text{dB} < \text{threshold}$ as "Water".
* **Major Flaw for Road Risk**: This flags the permanent Brahmaputra River, lakes, ponds, and even smooth airport runways or dry flat asphalt as "floods". It cannot distinguish existing water from disaster-induced flooding.

---

### B. Pre/Post dB Difference ($\Delta\text{dB}$)
* **Concept**:
  $$\text{dB}_{\text{event}} = 10 \cdot \log_{10}(\sigma^0_{\text{event}})$$
  $$\text{dB}_{\text{baseline}} = 10 \cdot \log_{10}(\sigma^0_{\text{baseline}})$$
  $$\Delta\text{dB} = \text{dB}_{\text{event}} - \text{dB}_{\text{baseline}}$$
* **Physical Principle**: When dry soil or vegetation (rough, high backscatter: $-12\text{ dB}$ to $-8\text{ dB}$) becomes inundated with water (smooth specular reflector: $-22\text{ dB}$ to $-18\text{ dB}$), the backscatter experiences a sharp negative drop ($\Delta\text{dB} \le -4\text{ dB}$ to $-8\text{ dB}$).
* **Limitation if used alone**: Areas that drop from $+5\text{ dB}$ (bright buildings) to $0\text{ dB}$ (vegetation) have $\Delta\text{dB} = -5\text{ dB}$, but they are still not water.

---

### C. Linear-Domain Ratio ($\sigma^0_{\text{event}} / \sigma^0_{\text{baseline}}$)
* **Mathematical Relation**:
  $$10 \cdot \log_{10}\left(\frac{\sigma^0_{\text{event}}}{\sigma^0_{\text{baseline}}}\right) = 10 \cdot \log_{10}(\sigma^0_{\text{event}}) - 10 \cdot \log_{10}(\sigma^0_{\text{baseline}}) = \Delta\text{dB}$$
* **Insight**: Ratio in the linear domain is mathematically identical to subtraction in the logarithmic (dB) domain. Working in decibels ($\text{dB}$) is preferred because radar backscatter follows a log-normal distribution, making thresholds symmetric and intuitive to explain.

---

### D. Dual-Condition Bitemporal Thresholding (Recommended Approach)
* **Concept**: Combines **relative change** ($\Delta\text{dB}$) with **absolute post-event water likelihood** ($\text{dB}_{\text{event}}$) and **permanent water masking** ($\text{dB}_{\text{baseline}}$).

---

## 4. Recommended MVP Approach & Workflow

### The 4-Step Dual-Condition Pipeline

```text
[Observation A: Baseline Linear GeoTIFF]   [Observation B: Event Linear GeoTIFF]
                 │                                           │
                 ▼                                           ▼
      Convert to dB (Clip ε)                      Convert to dB (Clip ε)
                 │                                           │
                 ▼                                           ▼
     3x3 Median Filter (Denoise)                 3x3 Median Filter (Denoise)
                 │                                           │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                       Compute Backscatter Difference
                        ΔdB = Event_dB - Baseline_dB
                                       │
                                       ▼
                      Apply 3-Way Logical Classification:
    1. Event is Water-Like:      Event_dB <= T_water (e.g. -16.0 dB)
    2. Baseline was NOT Water:   Baseline_dB > T_water (e.g. > -16.0 dB)
    3. Significant Drop Occurred: ΔdB <= T_drop (e.g. <= -4.0 dB)
                                       │
                                       ▼
                     Binary Flood Mask: (1 AND 2 AND 3)
                                       │
                                       ▼
                 Morphological Area Filter (Min Cluster >= 5 px)
                                       │
                                       ▼
               Polygonize Mask to GeoJSON FeatureCollection
```

### Why This Approach Fits Our MVP
1. **Explainable to Judges**: Relies on fundamental radar physics (specular reflection of microwaves on water) rather than an uninterpretable black-box ML model.
2. **Zero Training Data Required**: Operates directly on physics-based thresholding without needing labeled historical flood polygons.
3. **No False Positives from Permanent Rivers**: Permanent water bodies are filtered out because they were already dark in the baseline image (`Baseline_dB <= T_water`).
4. **Lightweight & Fast**: Executes in under 150 ms in Python using `numpy` and `scipy.ndimage` / `rasterio.features`.

---

## 5. Mathematical Formulation & Decibel Conversion

### Decibel Conversion Formula
$$\text{dB} = 10 \cdot \log_{10}\left(\max(\sigma^0, \epsilon)\right)$$
* **Why $\epsilon$ is essential**: In radar processing, $\sigma^0$ can occasionally be $0.0$ (outside scene bounds or corrupted pixels). Since $\log_{10}(0) = -\infty$, we set $\epsilon = 10^{-6}$ (corresponding to $-60\text{ dB}$) to prevent numerical `NaN` or `-inf` errors.
* **NoData Handling**: Pixels with value $\le 0$ or non-finite values are assigned a `NaN` mask and ignored during difference computation.

---

## 6. Speckle & Noise Filtering

* **The Problem**: SAR imagery is inherently corrupted by **granular speckle noise** caused by random constructive and destructive interference of coherent microwave echoes. Without filtering, isolated noisy pixels trigger false positive flood detections.
* **MVP Solution**: Apply a **$3 \times 3$ median filter** on the dB array prior to difference calculation.
  * *Why Median*: The median filter effectively smooths salt-and-pepper radar speckle while preserving sharp water boundaries and linear road edges, without blurring them as a Gaussian filter would.

---

## 7. Permanent Water Distinguishing Strategy

| Land Type | Baseline dB | Event dB | $\Delta\text{dB}$ | Classification |
|---|---|---|---|---|
| **Permanent River / Lake** | Low ($-22\text{ dB}$) | Low ($-22\text{ dB}$) | $\approx 0\text{ dB}$ | **Permanent Water (Ignored)** |
| **Normal Dry Ground** | High ($-10\text{ dB}$) | High ($-10\text{ dB}$) | $\approx 0\text{ dB}$ | **Dry Land (Ignored)** |
| **Newly Flooded Ground** | High ($-10\text{ dB}$) | Low ($-19\text{ dB}$) | **$-9\text{ dB}$ (Sharp Drop)** | **NEW FLOOD CANDIDATE ✅** |
| **Receded Flood / Drying**| Low ($-20\text{ dB}$) | High ($-11\text{ dB}$) | $+9\text{ dB}$ (Increase) | **Drying / Recovery (Ignored)** |

---

## 8. Threshold Calibration Strategy

Rather than hardcoding arbitrary fixed values, the service will expose configurable parameters with established SAR defaults:

1. **`water_threshold_db`** (Default: **$-16.0\text{ dB}$**):
   * Typical C-band VV backscatter over open standing water is $-24\text{ dB}$ to $-17\text{ dB}$. Pixels below $-16.0\text{ dB}$ are considered water-like.
2. **`change_drop_db`** (Default: **$-4.0\text{ dB}$**):
   * A drop of at least $4.0\text{ dB}$ represents a greater than $60\%$ reduction in reflected linear radar power, indicating significant surface smoothing/inundation.
3. **Adaptive Histogram Split (Optional Calibration Mode)**:
   * Uses Otsu's bimodal thresholding on the post-event histogram to automatically find the valley between land and water modes.

---

## 9. Spatial Resolution & Region Filtering

### Spatial Resolution Analysis
* Our Module 3A audit verified that a $0.5^\circ \times 0.5^\circ$ BBox ($\approx 50\text{ km} \times 50\text{ km}$) at $256 \times 256$ pixels yields $\approx 195\text{ m/pixel}$.
* **For Road-Level Analysis**: A resolution of $195\text{ m/pixel}$ can detect regional plain flooding, but may span across narrow rural roads.
* **Resolution Strategy**:
  1. **Regional Overview**: $512 \times 512$ over $50\text{ km}$ gives $\approx 98\text{ m/pixel}$.
  2. **Corridor High-Res Analysis**: When assessing specific road segments in Module 6, we will query targeted $5\text{ km} \times 5\text{ km}$ corridor bounding boxes at $512 \times 512$, achieving the full **$\approx 9.7\text{ m/pixel}$ native resolution** of Sentinel-1.

### Minimum Cluster Size Filtering
* Single isolated pixels (e.g. 1 pixel of change) are filtered out using morphological labeling (connected components). Only contiguous flood clusters of $\ge 5\text{ pixels}$ are retained.

---

## 10. Expected Output Format for Module 3B

Module 3B will generate a structured response containing both:

### 1. Summary Statistics
```json
{
  "total_area_analyzed_km2": 2765.5,
  "flooded_area_km2": 42.8,
  "flooded_percentage": 1.55,
  "permanent_water_area_km2": 112.4
}
```

### 2. GeoJSON FeatureCollection (for Road Intersection & Frontend Rendering)
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[91.62, 26.15], [91.68, 26.15], [91.68, 26.22], [91.62, 26.22], [91.62, 26.15]]]
      },
      "properties": {
        "hazard_type": "flood_candidate",
        "confidence": 0.88,
        "mean_event_db": -19.4,
        "mean_drop_db": -8.2,
        "area_km2": 4.12
      }
    }
  ]
}
```

---

## 11. Integration with Future Road-Risk Module (Module 6)

```text
[Module 3B: Flood GeoJSON Polygons]       [Module 5: OSM Road Graph Network]
                  │                                        │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                        [Module 6: Risk Assessment]
                       Spatial Intersection (Shapely)
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   Road Intersects Flood Polygon                  Road Outside Flood Zone
   -> Status: BLOCKED                             -> Status: CLEAR
   -> Risk Weight: 1.0 (Closed)                   -> Risk Weight: Normal
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      ▼
                      [Module 7: Dynamic Re-Routing]
                  Calculates Alternate Path Avoiding Blockage
```

---

## 12. Suggested Implementation Steps for Module 3B

1. **Step 1 (`services/flood_detection.py`)**: Implement `SARChangeDetector` service:
   * Method `linear_to_db(array, eps=1e-6)`
   * Method `apply_median_filter(array, size=3)`
   * Method `compute_difference(baseline_db, event_db)`
   * Method `classify_flood(baseline_db, event_db, water_th, drop_th)`
   * Method `polygonize_mask(mask, transform, crs)` using `rasterio.features.shapes`
2. **Step 2 (`api/satellite.py`)**: Expose `GET /api/satellite/sentinel-1/detect-flood` accepting bounding box, baseline date, and event date.
3. **Step 3 (`tests/test_flood_detection.py`)**: Unit tests verifying dB conversion, synthetic flood patch detection, permanent water rejection, and GeoJSON validity.

---

## 13. How to Explain Module 3B to an SIH Judge

> *"In Module 3B, we implement our physics-based environmental change detection engine. Because optical satellites fail during monsoon clouds, we use dual-temporal Sentinel-1 Synthetic Aperture Radar (SAR) observations. 
> 
> Water acts as a specular reflector, scattering microwave pulses away from the radar antenna and resulting in a steep drop in radar backscatter ($\sigma^0$). 
> 
> Our algorithm compares a pre-disaster baseline raster against a post-event crisis raster in the decibel domain. By requiring both a significant drop in backscatter ($\le -4\text{ dB}$) and a post-event water threshold ($\le -16\text{ dB}$), our system identifies newly flooded candidate zones while automatically ignoring permanent rivers and lakes. 
> 
> The detected flood mask is polygonized directly into georeferenced GeoJSON features, which will be spatially overlaid onto OpenStreetMap road vectors in Module 6 to identify inundated road segments and trigger dynamic rerouting."*

---

## 14. Realistic Judge Questions & Answers

**Q1: Why can't you just threshold a single satellite image instead of comparing two dates?**
> *Answer*: A single SAR image cannot differentiate new floodwaters from permanent rivers, lakes, reservoirs, or smooth flat asphalt (like airport runways) because all smooth surfaces appear dark in SAR. By comparing a pre-disaster baseline against a post-event scene, we detect the transition from dry ground to standing water.

**Q2: Why do you convert the linear backscatter values to decibels (dB)?**
> *Answer*: Radar backscatter spans several orders of magnitude and follows a log-normal distribution. In the linear domain, changes over dark surfaces produce tiny numerical differences compared to bright terrain. Converting to decibels ($\text{dB} = 10 \cdot \log_{10}(\sigma^0)$) linearizes relative power ratios, making thresholding uniform and physically meaningful.

**Q3: How do you prevent small radar noise (speckle) from triggering false flood alarms?**
> *Answer*: We apply a $3 \times 3$ median spatial filter to suppress coherent radar speckle while preserving sharp water boundaries, followed by a minimum connected component cluster threshold ($\ge 5\text{ pixels}$) to eliminate isolated single-pixel noise.

**Q4: Is single-polarization VV enough, or do you need VH as well?**
> *Answer*: VV is the primary channel for open water detection because vertical microwave pulses reflect strongly away from smooth water surfaces. VH is helpful for detecting flooded vegetation in dense canopies. For our SIH MVP, VV provides clean, robust surface inundation detection with minimal computational overhead.

**Q5: What is the output of this module and how will the routing algorithm use it?**
> *Answer*: Module 3B outputs georeferenced GeoJSON polygons representing detected flood boundaries. In Module 6, these polygons are spatially intersected with road geometry lines from OpenStreetMap. Any road segment intersecting a flood polygon is flagged as blocked, causing the graph routing engine (Module 7) to calculate an alternative logistics path.
