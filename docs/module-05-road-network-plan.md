# Module 5: Road Network Ingestion & Graph Modeling — Implementation Plan

> [!NOTE]
> **Status: PLANNING DOCUMENT ONLY (Module 5 is NOT yet implemented)**  
> This document details the technical investigation, topological graph design, geospatial data structures, caching strategy, and implementation blueprint for OpenStreetMap (OSM) road network modeling for SIH 2026.

---

## 1. Purpose

The purpose of **Module 5** is to ingest, parse, and topologically model the physical road network of the target Area of Interest (AOI) in North Eastern India (NER) using **OpenStreetMap (OSM)** data.

While Modules 3B and 4 provide spatial hazard polygons (flood candidates) and weather corroboration, routing and logistics accessibility cannot function on raw raster pixels alone. Module 5 constructs a mathematically rigorous, geospatially referenced **Directed Graph ($G = (V, E)$)** where:
* **Nodes ($V$)** represent physical intersections, dead-ends, and structural transitions.
* **Edges ($E$)** represent navigable road segments with true physical geometry (`LineString`), directional constraints (`oneway`), hierarchy (`highway`), and base travel weights (`length` / `travel_time`).

This topological graph forms the physical structural backbone for downstream **Road Risk Assessment (Module 6)** and **Dynamic Rerouting (Module 7)**.

---

## 2. Problem Solved

1. **Bridging Vector Hazards and Supply Chains**: Flood polygons from satellite SAR (Module 3B) are 2D spatial areas. To determine if supply trucks can reach remote communities in Assam or Meghalaya, those polygons must be intersected with discrete, navigable road vectors.
2. **Topological Routing Feasibility**: A collection of isolated road lines is insufficient for navigation. A vehicle cannot traverse disconnected line segments without a topologically validated graph containing explicit connectivity, turn restrictions, and one-way constraints.
3. **Terrain-Aware Geometry Preservation**: In the mountainous and riverine terrain of North Eastern India, roads are winding and follow contour lines. Treating roads as straight Euclidean chords between intersections would cause severe errors when intersecting with floodwaters. Module 5 preserves true physical `LineString` curves.

---

## 3. Data Source: OpenStreetMap & Overpass API

### OpenStreetMap (OSM)
OpenStreetMap is the premier global open geospatial database. In OSM:
* **Nodes**: Point features with latitude and longitude (intersections or geometry vertices).
* **Ways**: Ordered sequences of nodes representing linear road segments with key-value tags (`highway=primary`, `oneway=yes`, `name=NH 27`).
* **Relations**: Groupings of elements defining complex turn restrictions or administrative boundaries.

### Overpass API
The Overpass API is a read-only API that executes Overpass QL queries to extract targeted subsets of OSM data (e.g. all drivable roads within a bounding box) without downloading multi-gigabyte country files.

---

## 4. Technologies Investigated

### OSMnx (`osmnx`)
* **Capabilities**: A specialized Python library built on top of NetworkX, GeoPandas, and Shapely.
* **Functionality**:
  * Directly queries the Overpass API using bounding boxes (`graph_from_bbox`), point buffers, or polygon geometries.
  * Filters road types automatically (e.g. `network_type='drive'` to isolate drivable vehicular roads).
  * Automatically resolves complex intersections and simplifies topological chains into clean graph edges while preserving intermediate curve geometries as Shapely `LineString` attributes.
  * Calculates true geodesic/projected edge lengths in meters.
  * Converts effortlessly between `networkx.MultiDiGraph` and GeoDataFrames (`graph_to_gdfs`, `graph_from_gdfs`).

### NetworkX (`networkx`)
* **Capabilities**: Python's standard library for graph theory and network analysis.
* **Functionality**:
  * Represents directed graphs (`MultiDiGraph` / `DiGraph`) with arbitrary node and edge attributes.
  * Out-of-the-box support for shortest path algorithms (Dijkstra, A*, Bellman-Ford).
  * Enables dynamic edge weight modification (e.g. applying risk penalty multipliers in Module 6 & 7).

### Shapely (`shapely`)
* Provides standard 2D computational geometry (intersections, buffers, distances, centroids) directly compatible with GeoJSON and rasterio.

---

## 5. Approach Comparison

We evaluated three architectural approaches for road network ingestion in our SIH MVP:

| Evaluation Criterion | Approach A: Direct Overpass API + Custom Parser | Approach B: OSMnx (GeoDataFrames Only) | Approach C: OSMnx + NetworkX Unified Graph (Recommended) |
| :--- | :--- | :--- | :--- |
| **Development Complexity** | Very High (must write custom topology stitcher) | Medium (handles geometries, neglects graph) | **Low to Moderate (Unified library architecture)** |
| **Development Time** | 3–4 weeks | 1–2 weeks | **1–2 days (Fast & robust)** |
| **Data Quality & Topology** | Error-prone (dangling ways, manual one-ways) | High geospatial, low graph connectivity | **High (automatic topological simplification)** |
| **True Road Geometry** | Manual node-chain reconstruction required | Preserved as Shapely `LineString` | **Preserved natively on every edge** |
| **One-Way Handling** | Manual directed adjacency list creation | Table column only | **Native directed edge generation (`u -> v`)** |
| **Routing Support (Mod 7)**| Must write custom Dijkstra from scratch | Requires external routing engine | **Native NetworkX Dijkstra / A\* algorithms** |
| **Flood Polygon Overlap** | High complexity | Direct GeoPandas/Shapely spatial join | **Direct Shapely intersection per edge** |
| **Local File Caching** | Custom JSON serialization | Shapefile / GeoJSON only | **Native GraphML / GeoJSON / Pickle support** |
| **FastAPI Compatibility** | Requires custom serializers | High | **High (clean JSON & GeoJSON serialization)** |
| **SIH MVP Suitability** | Poor (reinventing standard wheels) | Incomplete (cannot route natively) | **Best (Industry-standard, reliable, explainable)** |

---

## 6. Recommended Architecture (Approach C)

We recommend **Approach C: OSMnx + NetworkX Unified Graph Representation**.

```text
┌─────────────────────────────────────────────────────────────┐
│                 OPENSTREETMAP (OVERPASS API)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS Query (network_type='drive')
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  OSMNX INGESTION ENGINE                     │
│  - BBox spatial filtering                                   │
│  - Topological simplification                               │
│  - Geodesic length calculation (meters)                     │
│  - Shapely LineString geometry preservation                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               NETWORKX MULTIDIGRAPH (G = V, E)              │
│                                                             │
│  Nodes (V): Intersections (lat, lon, osmid)                 │
│  Edges (E): Road Segments:                                  │
│    - Unique ID: f"{u}_{v}_{key}"                            │
│    - Length: meters                                         │
│    - Highway: motorway, trunk, primary, secondary, tertiary │
│    - Geometry: Shapely LineString (WGS84)                   │
│    - Base Weight: distance / travel_time                    │
│    - Dynamic Hazard Status: [NORMAL] (ready for Mod 6)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│      LOCAL GRAPH CACHE       │ │       FASTAPI ROUTE        │
│ backend/data/cache/roads/    │ │ GET /api/roads/network     │
│ - graphml / geojson extract  │ │ (Returns GeoJSON edges)    │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## 7. Road Data Model & Filtering

To maintain high performance and avoid cluttering the graph with non-drivable footpaths, Module 5 strictly filters road types:

### Included Road Classes (`network_type='drive'`)
* `motorway` & `motorway_link`: High-speed multi-lane expressways.
* `trunk` & `trunk_link`: National Highways (e.g. NH 27, NH 37 across Assam).
* `primary` & `primary_link`: Major state arteries linking major regional district hubs.
* `secondary` & `secondary_link`: Regional corridors connecting sub-divisions.
* `tertiary` & `tertiary_link`: Rural and feeder roads connecting logistical supply points.
* `residential` / `unclassified`: Local access roads connecting final delivery destinations.

### Excluded Classes
* `footway`, `cycleway`, `path`, `steps`, `pedestrian`, `bridleway`, `service` (non-essential tracks).

---

## 8. Graph Model ($G = (V, E)$)

* **Graph Class**: `networkx.MultiDiGraph` (Directed graph supporting parallel edges, e.g. divided highways).
* **Nodes ($V$)**:
  * Index: `osmid` (int) or internal sequential integer.
  * Attributes: `x` (longitude), `y` (latitude), `street_count` (number of connected ways).
* **Edges ($E$)**:
  * Keyed by: `(u, v, key)` where `u` is start node, `v` is end node, and `key` differentiates parallel links.
  * Directionality:
    * `oneway = True`: Generates a single directed edge $u \to v$.
    * `oneway = False`: Generates bidirectional directed edges $u \to v$ and $v \to u$.

---

## 9. Road Attributes to Retain

To keep memory footprint minimal while serving all downstream requirements:

| Attribute | Data Type | Purpose in Logistics Pipeline |
| :--- | :--- | :--- |
| `road_id` | `str` | Unique composite identifier `f"{u}_{v}_{key}"` for discrete tracking |
| `name` | `str` | Human-readable name (e.g. "Guwahati-Shillong Road", "NH 27") |
| `highway` | `str` | Road hierarchy class (dictates baseline capacity and clearance priority) |
| `length` | `float` | Physical edge distance in **meters** (baseline Dijkstra routing weight) |
| `oneway` | `bool` | Directional navigation constraint |
| `maxspeed` | `str` / `float`| Legal/estimated speed limit for baseline travel-time estimation |
| `geometry` | `LineString` | Exact physical coordinates for spatial intersection with flood polygons |
| `lanes` | `str` / `int` | Road width indicator (optional supporting attribute) |

---

## 10. Geometry Handling

Roads in North Eastern India curve through valleys and mountain passes. Straight line segments between intersections fail to capture the true terrain path.
* **Storage**: Every edge retains its `geometry` attribute as a `shapely.geometry.LineString`.
* **Export**: When exported to the frontend or API, geometries are serialized into GeoJSON `LineString` coordinate arrays `[[lon1, lat1], [lon2, lat2], ...]`.
* **Intersection Readiness**: In Module 6, computing flood impact is as simple as calling:
  $$\text{intersects} = \text{road\_geometry.intersects(flood\_polygon)}$$

---

## 11. Coordinate Reference Systems (CRS)

* **Storage & API Representation**: `EPSG:4326` (WGS84 latitude/longitude degrees). Standard for all web APIs, GeoJSON, and Leaflet/Mapbox renderers.
* **Distance Calculations**: OSMnx automatically computes geodesic lengths or projects internally to Universal Transverse Mercator (UTM Zone 46N / `EPSG:32646` for Assam/NER) to assign precise lengths in **meters** to every edge attribute.

---

## 12. Road Identification Strategy (`road_id`)

To ensure seamless coordination between Module 5 (Roads), Module 6 (Risk), and Module 7 (Routing), each road segment is assigned a deterministic, stable string identifier:
$$\text{road\_id} = f"{u}\_{v}\_{key}"$$

* Example: `"184729102_184729105_0"`
* **Advantage**: Allows the Risk Engine in Module 6 to emit a dictionary of impacted segments:
  ```json
  {
    "184729102_184729105_0": { "risk_status": "BLOCKED", "penalty_multiplier": 1000.0 }
  }
  ```
  which Module 7 directly injects into the NetworkX graph edge weights before running Dijkstra.

---

## 13. Area of Interest (AOI) Strategy

For the SIH 2026 MVP, road network ingestion will align directly with our satellite bounding boxes:
* **Default AOI**: Guwahati / Brahmaputra Valley corridor (`min_lon=91.50, min_lat=26.00, max_lon=92.00, max_lat=26.50`).
* **Dynamic BBox**: The service accepts arbitrary `(min_lon, min_lat, max_lon, max_lat)` bounding boxes.
* **Network Size**: A $20\text{ km} \times 20\text{ km}$ to $50\text{ km} \times 50\text{ km}$ urban/rural corridor in Assam yields approximately 2,000–6,000 nodes and 4,000–12,000 edges—lightweight enough to download in $< 5\text{ seconds}$ and hold in memory in $< 15\text{ MB}$.

---

## 14. Caching Strategy

Road networks do not change every minute. Downloading from Overpass API on every user request introduces unnecessary latency and rate-limit vulnerability.

* **Cache Directory**: `backend/data/cache/roads/`
* **Cache Key**: MD5 hash of the BBox coordinates (e.g. `road_graph_91.50_26.00_92.00_26.50.graphml`).
* **Cache Formats**:
  * **GraphML (`.graphml`)**: Native, lossless NetworkX graph format preserving all edge attributes and node topology.
  * **GeoJSON (`.geojson`)**: Cached vector features for rapid web streaming to the frontend.
* **Cache Lifecycle**: If a cached graph file exists for the requested BBox, it is loaded instantaneously ($< 50\text{ ms}$) without hitting external Overpass servers.

---

## 15. Reliability & Fallback Handling

* **Overpass API Outage / Rate Limit**:
  * If Overpass API times out (HTTP 429 / 504), the service checks for the cached regional graph.
  * If no cache exists, the service loads a pre-bundled fallback graph of the Guwahati logistics corridor (`bundled_guwahati_network.graphml`) packaged with the repository.
* **API Isolation**: All OSMnx and Overpass queries run strictly within the FastAPI backend; no external map credentials or Overpass calls are made from the frontend.

---

## 16. Future Integration with Module 6 (Risk) & Module 7 (Routing)

```text
[Module 3B] Flood Candidate Polygons (GeoJSON)
                      │
                      ▼
[Module 5] Road Network Graph (NetworkX MultiDiGraph)
                      │
                      ▼
[Module 6] Spatial Intersection Engine:
           For each edge (u, v, k) with geometry L:
             If L.intersects(Flood_Polygon):
               edge.risk = "CRITICAL / INUNDATED"
               edge.weight = edge.length * 1000.0  (High impedance)
                      │
                      ▼
[Module 7] Alternate Routing Engine:
           nx.shortest_path(G, source, target, weight='weight')
           --> Automatically routes logistics trucks around flooded links!
```

---

## 17. Limitations and Assumptions

1. **OSM Attribute Completeness**: In rural parts of North Eastern India, attributes like `lanes` or `maxspeed` may occasionally be missing in OSM. The service applies sensible regional defaults (`speed_kph = 40.0` for secondary, `60.0` for primary/NH).
2. **Dynamic Road Closures**: OpenStreetMap represents static physical infrastructure; active landslide roadblocks or temporary police barriers are not in OSM. These dynamic conditions will be modeled dynamically in Module 6 via satellite and weather intersections.

---

## 18. How to Explain Module 5 to an SIH Judge

> *"Judges, while satellite SAR detects where water is, relief trucks cannot drive on raw satellite pixels—they navigate physical roads.*
> 
> *Module 5 builds our topological road graph using OpenStreetMap. Using OSMnx and NetworkX, we ingest drivable road networks, maintain full directional and one-way constraints, and preserve true curved road geometries.*
> 
> *Every road segment is given a unique identifier and physical length in meters. This creates the mathematical graph foundation that allows our Risk Engine in Module 6 to pinpoint exactly which road segments are submerged and allows our Routing Engine in Module 7 to calculate real-time bypasses."*

---

## 19. Likely Judge Questions and Concise Answers

### Q1: "Why use OSMnx instead of just querying Overpass API directly?"
**Answer:** *"Overpass returns raw disconnected XML/JSON nodes and ways. OSMnx automatically stitches nodes into continuous ways, simplifies complex multi-point intersections into clean topological graph edges, computes physical geodesic distances in meters, and outputs a ready-to-route NetworkX graph in a single robust call."*

### Q2: "Why is retaining the full road geometry important instead of just straight lines between intersections?"
**Answer:** *"In the hilly and riverine terrain of North Eastern India, roads are winding. If we represented a road as a straight line between two distant towns, a flood polygon in a river bend might appear to miss the road when in reality the physical curved highway passes directly through the water. Preserving Shapely `LineString` geometries ensures 100% spatial intersection accuracy in Module 6."*

### Q3: "How does this road graph support dynamic rerouting later?"
**Answer:** *"Every edge in our NetworkX graph has an initial impedance weight equal to its physical length in meters. When Module 6 detects that a road segment intersects a flood polygon, it applies a massive penalty multiplier to that edge's weight. When Dijkstra's algorithm runs in Module 7, it naturally routes around the penalized segment."*

### Q4: "What happens if the Overpass API is down or rate-limited during a disaster?"
**Answer:** *"Our system caches road graphs locally in GraphML format. For critical logistics corridors like Guwahati-Shillong (NH 27), the graph is pre-cached and loads offline in under 50 milliseconds without any internet dependency."*
