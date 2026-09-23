import os
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import rasterio
import rasterio.features


class SARChangeDetector:
    """Service to perform bitemporal Sentinel-1 SAR change detection for flood candidate identification."""

    def __init__(
        self,
        default_water_threshold_db: float = -16.0,
        default_change_threshold_db: float = -4.0,
        default_min_region_pixels: int = 5,
    ):
        self.water_threshold_db = default_water_threshold_db
        self.change_threshold_db = default_change_threshold_db
        self.min_region_pixels = default_min_region_pixels

    def linear_to_db(self, linear_array: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Converts linear sigma0 backscatter intensity to decibels (dB).
        
        Formula: dB = 10 * log10(max(sigma0, eps))
        """
        arr = np.asarray(linear_array, dtype=np.float32)
        # Create mask of valid positive finite numbers
        valid_mask = np.isfinite(arr) & (arr > 0)
        
        # Initialize output with NaN
        db_arr = np.full_like(arr, fill_value=np.nan, dtype=np.float32)
        
        # Apply conversion where valid with clipping at eps
        clipped = np.clip(arr[valid_mask], a_min=eps, a_max=None)
        db_arr[valid_mask] = 10.0 * np.log10(clipped)
        return db_arr

    def apply_median_filter_3x3(self, arr: np.ndarray) -> np.ndarray:
        """Applies a 3x3 median filter to reduce SAR speckle noise while preserving edges."""
        if arr.ndim != 2:
            raise ValueError("Median filter requires a 2D array.")
        
        h, w = arr.shape
        if h < 3 or w < 3:
            return arr.copy()

        # Handle NaNs by replacing temporarily with edge values
        nan_mask = np.isnan(arr)
        clean_arr = arr.copy()
        if np.any(nan_mask):
            mean_val = np.nanmean(arr) if np.any(~nan_mask) else 0.0
            clean_arr[nan_mask] = mean_val

        # Pad with edge replication
        padded = np.pad(clean_arr, pad_width=1, mode='edge')
        
        # Vectorized 3x3 neighborhood stacking
        stacked = np.stack([
            padded[0:h,     0:w], padded[0:h,     1:w+1], padded[0:h,     2:w+2],
            padded[1:h+1,   0:w], padded[1:h+1,   1:w+1], padded[1:h+1,   2:w+2],
            padded[2:h+2,   0:w], padded[2:h+2,   1:w+1], padded[2:h+2,   2:w+2],
        ], axis=0)
        
        filtered = np.median(stacked, axis=0).astype(np.float32)
        filtered[nan_mask] = np.nan
        return filtered

    def validate_and_read_rasters(
        self, baseline_path: str, event_path: str
    ) -> Tuple[np.ndarray, np.ndarray, rasterio.Affine, Any, Dict[str, Any]]:
        """Verifies raster existence, compatibility (CRS, dimensions, bounds), and reads band 1."""
        if not os.path.exists(baseline_path):
            raise FileNotFoundError(f"Baseline raster not found: {baseline_path}")
        if not os.path.exists(event_path):
            raise FileNotFoundError(f"Event raster not found: {event_path}")

        with rasterio.open(baseline_path) as src_b, rasterio.open(event_path) as src_e:
            # Check CRS compatibility
            if src_b.crs != src_e.crs:
                raise ValueError(f"CRS mismatch: Baseline ({src_b.crs}) vs Event ({src_e.crs})")

            # Check Dimensions
            if src_b.width != src_e.width or src_b.height != src_e.height:
                raise ValueError(
                    f"Dimension mismatch: Baseline ({src_b.width}x{src_b.height}) vs Event ({src_e.width}x{src_e.height})"
                )

            # Check Bounds tolerance
            b_bounds = src_b.bounds
            e_bounds = src_e.bounds
            tol = 1e-4
            if (
                abs(b_bounds.left - e_bounds.left) > tol
                or abs(b_bounds.right - e_bounds.right) > tol
                or abs(b_bounds.bottom - e_bounds.bottom) > tol
                or abs(b_bounds.top - e_bounds.top) > tol
            ):
                raise ValueError("Spatial extent / bounding box mismatch between baseline and event rasters.")

            baseline_arr = src_b.read(1)
            event_arr = src_e.read(1)
            transform = src_b.transform
            crs = src_b.crs
            meta = {
                "width": src_b.width,
                "height": src_b.height,
                "bounds": dict(src_b.bounds._asdict()),
                "crs": str(src_b.crs),
            }

        return baseline_arr, event_arr, transform, crs, meta

    def classify_flood_candidates(
        self,
        baseline_db: np.ndarray,
        event_db: np.ndarray,
        water_threshold_db: float,
        change_threshold_db: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Applies 3-way logical classification:
        
        1. Event is water-like: event_db <= water_threshold_db
        2. Baseline was NOT water-like: baseline_db > water_threshold_db
        3. Significant drop: (event_db - baseline_db) <= change_threshold_db
        """
        valid_pixels = np.isfinite(baseline_db) & np.isfinite(event_db)
        
        delta_db = np.full_like(event_db, fill_value=np.nan, dtype=np.float32)
        delta_db[valid_pixels] = event_db[valid_pixels] - baseline_db[valid_pixels]

        # Condition 1: Event pixel is water-like (low backscatter)
        is_event_water = (event_db <= water_threshold_db) & valid_pixels
        
        # Condition 2: Baseline pixel was NOT water-like (filters permanent rivers & lakes)
        was_baseline_dry = (baseline_db > water_threshold_db) & valid_pixels
        
        # Condition 3: Significant drop in backscatter occurred
        has_significant_drop = (delta_db <= change_threshold_db) & valid_pixels

        # Combined Flood Candidate Mask
        flood_mask = is_event_water & was_baseline_dry & has_significant_drop

        return flood_mask, delta_db

    def filter_small_regions(self, mask: np.ndarray, min_pixels: int = 5) -> Tuple[np.ndarray, int]:
        """Removes connected components / clusters with fewer than min_pixels."""
        if not np.any(mask) or min_pixels <= 1:
            return mask.copy(), 0

        h, w = mask.shape
        visited = np.zeros((h, w), dtype=bool)
        cleaned_mask = np.zeros((h, w), dtype=bool)
        removed_count = 0

        # 8-connectivity neighbor offsets
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for r in range(h):
            for c in range(w):
                if mask[r, c] and not visited[r, c]:
                    # BFS component search
                    component = []
                    queue = [(r, c)]
                    visited[r, c] = True

                    while queue:
                        curr_r, curr_c = queue.pop(0)
                        component.append((curr_r, curr_c))

                        for dr, dc in offsets:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < h and 0 <= nc < w:
                                if mask[nr, nc] and not visited[nr, nc]:
                                    visited[nr, nc] = True
                                    queue.append((nr, nc))

                    if len(component) >= min_pixels:
                        for cr, cc in component:
                            cleaned_mask[cr, cc] = True
                    else:
                        removed_count += len(component)

        return cleaned_mask, removed_count

    def calculate_polygon_area_km2(self, coordinates: List[List[List[float]]], center_lat: float = 26.0) -> float:
        """Calculates approximate real ground area in km² using projected spherical latitude/longitude conversion."""
        if not coordinates or not coordinates[0]:
            return 0.0

        ring = coordinates[0]
        if len(ring) < 3:
            return 0.0

        # Ground scaling factors at given latitude
        deg_to_km_lat = 110.8
        deg_to_km_lon = 111.32 * np.cos(np.radians(center_lat))

        # Shoelace formula on scaled km coordinates
        n = len(ring)
        area_sum = 0.0
        for i in range(n - 1):
            x1, y1 = ring[i][0] * deg_to_km_lon, ring[i][1] * deg_to_km_lat
            x2, y2 = ring[i + 1][0] * deg_to_km_lon, ring[i + 1][1] * deg_to_km_lat
            area_sum += (x1 * y2) - (x2 * y1)

        return abs(area_sum) / 2.0

    def polygonize_mask(
        self,
        flood_mask: np.ndarray,
        delta_db: np.ndarray,
        transform: rasterio.Affine,
        center_lat: float = 26.0,
    ) -> List[Dict[str, Any]]:
        """Converts binary flood mask into GeoJSON Features with area and mean drop properties."""
        if not np.any(flood_mask):
            return []

        features = []
        # rasterio.features.shapes extracts geometries as GeoJSON-like dicts
        shapes_gen = rasterio.features.shapes(
            flood_mask.astype(np.uint8),
            mask=flood_mask,
            transform=transform,
        )

        for geom, val in shapes_gen:
            if val == 1:
                coords = geom.get("coordinates", [])
                area_km2 = self.calculate_polygon_area_km2(coords, center_lat=center_lat)

                # Compute exact pixel count and mean drop for this specific polygon
                poly_mask = rasterio.features.geometry_mask(
                    [geom],
                    out_shape=flood_mask.shape,
                    transform=transform,
                    invert=True,
                )
                active_pixels = poly_mask & flood_mask
                pixel_count = int(np.count_nonzero(active_pixels))
                poly_deltas = delta_db[active_pixels]
                mean_drop = float(np.mean(poly_deltas)) if len(poly_deltas) > 0 else 0.0

                feature = {
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "hazard_type": "flood_candidate",
                        "mean_drop_db": round(mean_drop, 2),
                        "pixel_count": pixel_count,
                        "area_km2": round(area_km2, 4),
                    },
                }
                features.append(feature)

        return features

    def detect_changes(
        self,
        baseline_path: str,
        event_path: str,
        water_threshold_db: Optional[float] = None,
        change_threshold_db: Optional[float] = None,
        min_region_pixels: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Full pipeline executing SAR bitemporal change detection and returning a GeoJSON FeatureCollection."""
        water_th = water_threshold_db if water_threshold_db is not None else self.water_threshold_db
        change_th = change_threshold_db if change_threshold_db is not None else self.change_threshold_db
        min_pixels = min_region_pixels if min_region_pixels is not None else self.min_region_pixels

        # 1. Validate and Read Rasters
        b_raw, e_raw, transform, crs, meta = self.validate_and_read_rasters(baseline_path, event_path)

        # 2. Linear to dB
        b_db = self.linear_to_db(b_raw)
        e_db = self.linear_to_db(e_raw)

        # 3. 3x3 Median Filter
        b_filtered = self.apply_median_filter_3x3(b_db)
        e_filtered = self.apply_median_filter_3x3(e_db)

        # 4. Classify Flood Candidates
        raw_flood_mask, delta_db = self.classify_flood_candidates(
            b_filtered, e_filtered, water_threshold_db=water_th, change_threshold_db=change_th
        )

        # 5. Remove Isolated Small Regions
        cleaned_flood_mask, removed_px = self.filter_small_regions(raw_flood_mask, min_pixels=min_pixels)

        # 6. Polygonize to GeoJSON
        center_lat = (meta["bounds"]["bottom"] + meta["bounds"]["top"]) / 2.0
        features = self.polygonize_mask(cleaned_flood_mask, delta_db, transform, center_lat=center_lat)

        total_pixels = cleaned_flood_mask.size
        candidate_pixels = int(np.count_nonzero(cleaned_flood_mask))
        total_candidate_area_km2 = sum(f["properties"]["area_km2"] for f in features)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "baseline_file": os.path.basename(baseline_path),
                "event_file": os.path.basename(event_path),
                "dimensions": f"{meta['width']}x{meta['height']}",
                "crs": meta["crs"],
                "parameters": {
                    "water_threshold_db": water_th,
                    "change_threshold_db": change_th,
                    "min_region_pixels": min_pixels,
                },
                "summary": {
                    "candidate_regions_count": len(features),
                    "candidate_pixels": candidate_pixels,
                    "total_candidate_area_km2": round(total_candidate_area_km2, 4),
                    "removed_noise_pixels": removed_px,
                }
            }
        }


# Singleton instance
change_detection_service = SARChangeDetector()


def get_sar_change_detector() -> SARChangeDetector:
    return change_detection_service

