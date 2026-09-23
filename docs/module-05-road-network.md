# Module 5: Road Network Ingestion & Graph Modeling

## 1. Purpose

**Implemented**

This module ingests a drivable road network for a target geographic area, preserves the road geometry needed for later spatial analysis, and stores a NetworkX graph in a local GraphML cache. The goal is to create the road backbone required before Module 6 road-risk assessment and later route calculations.

**Planned**

This module does not yet perform flood-road intersection, route optimization, or alternate-path search. Those are later modules.

---

## 2. Technologies

**Implemented**

- OpenStreetMap via OSMnx
- NetworkX `MultiDiGraph`
- Shapely `LineString` geometries
- Local GraphML cache in `backend/data/cache/roads`
- FastAPI endpoint under `/api/roads`

**Planned**

- Projected CRS conversion for metric analysis beyond the MVP geographic graph
- Advanced route scoring or hazard-aware routing

---

## 3. Input

**Implemented**

The service accepts a bounding box:

```text
min_lon, min_lat, max_lon, max_lat
```

Default Assam/Guwahati test window:

```text
west  = 91.50
south = 26.00
east  = 92.00
north = 26.50
```

The API validates the BBox and rejects invalid coordinate ranges.

---

## 4. Bounding Box Validation

**Implemented**

- longitude must be within `[-180, 180]`
- latitude must be within `[-90, 90]`
- minimum values must be strictly less than maximum values

This keeps the service usable across different AOIs without permanently hard-coding Assam.

---

## 5. OpenStreetMap

**Implemented**

The service queries OpenStreetMap through OSMnx using the drivable network type.

This is a network-level ingestion step, not a claim that OSM is complete or perfect. It provides a practical road graph for the requested area.

**Planned**

- exact road completeness validation for every local corridor
- road-quality audits against local government datasets

---

## 6. OSMnx

**Implemented**

The service leverages OSMnx for:

- bounding-box downloads
- drivable network extraction
- GraphML cache save/load
- graph creation and fallback behavior

The code uses OSMnx `graph_from_bbox` with `network_type="drive"`.

**Planned**

- more advanced filtering for modal or vehicle-specific road classes beyond the MVP drive network

---

## 7. NetworkX

**Implemented**

The graph is a `networkx.MultiDiGraph`.

This supports:

- directed road connectivity
- parallel edges
- later routing and risk augmentation in downstream modules

**Important**

The current module does not calculate safe routes or alternate paths; it only builds and summarizes the graph.

---

## 8. Node Model

**Implemented**

Each node carries OSM-style attributes such as:

- `osmid`
- `x` (longitude)
- `y` (latitude)
- `street_count`

This is compatible with a geospatial network model and future module integration.

---

## 9. Edge Model

**Implemented**

Each edge retains attributes such as:

- `source` and `destination`
- `key`
- `name`
- `highway`
- `length`
- `geometry`
- `oneway`
- `maxspeed`

Some attributes may legitimately be absent in raw OSM data. The implementation only stores values that exist and does not fabricate placeholders where none exist.

---

## 10. Geometry

**Implemented**

Road segments keep a Shapely `LineString` geometry where available. This preserves the actual road shape, which is important for future hazard overlap work.

**Planned**

- exact intersection tests with satellite-derived polygons
- road segment impact scoring

---

## 11. Attributes

**Implemented**

The model stores the expected OSM attributes when present and preserves the raw graph structure. When OSM attributes are missing, they are either omitted or kept as default values only when needed for the current service logic.

**Important**

No universal claim is made that every road has every attribute.

---

## 12. CRS

**Implemented**

The graph is represented in geographic coordinates with:

```text
EPSG:4326
```

This matches the standard OSM / GeoJSON / web-API convention and keeps the MVP simple.

**Planned**

- projected CRS selection for metric-heavy road analysis in later modules

---

## 13. Caching

**Implemented**

The service uses a local GraphML cache keyed by the BBox hash.

Flow:

```text
First request
  -> OSM / OSMnx fetch
  -> build graph
  -> save GraphML

Later request
  -> load GraphML
```

The cache is intended to avoid repeated network pulls for the same AOI. No benchmarked latency claim is made.

### Test isolation

Production retrieval uses OSMnx and the OSM/Overpass network. Module 5 tests isolate that external call with a deterministic mocked graph, so they verify graph normalization, caching, API responses, and error handling without depending on live Overpass availability. This test stub does not enable or represent a synthetic-road fallback in production.

---

## 14. API

**Implemented**

Endpoint:

```text
GET /api/roads/network
```

Response shape:

```json
{
  "success": true,
  "nodes": 1234,
  "edges": 2345,
  "crs": "EPSG:4326",
  "cache_used": true,
  "source_mode": "cache",
  "bbox": {
    "min_lon": 91.5,
    "min_lat": 26.0,
    "max_lon": 92.0,
    "max_lat": 26.5
  }
}
```

This is a compact summary and does not return the whole graph structure in one payload.

---

## 15. Tests

**Implemented**

The repository now includes `backend/tests/test_roads.py`, covering:

- valid bounding box
- invalid bounding box
- synthetic graph creation
- `MultiDiGraph` verification
- basic node/edge attributes
- missing attribute handling
- cache save/load round trip
- API summary response

**Planned**

- a separate live integration test that depends on network access and OSM availability

---

## 16. Live Verification

**Implemented**

The service is designed so a live test can verify:

- graph download from OSMnx
- non-zero node count
- non-zero edge count
- directed graph behavior
- geometry availability where present
- GraphML save/load behavior

**Important**

A synthetic graph is intentionally kept only for isolated unit testing. The production API/service does not silently return synthetic roads when a live OSM fetch fails; it raises a clear error unless a valid cached graph is available.

---

## 17. Limitations

**Implemented / known**

- OSM is not guaranteed to include every road in a given area
- not every edge has every metadata field
- caching reduces repeated requests but is not a guaranteed sub-50ms solution
- this module does not calculate a safe route or detect flood impact by itself
- `EPSG:4326` is intentionally kept simple for the MVP; not every metric operation uses a projected CRS yet

---

## 18. Connection to Module 6

**Implemented**

The graph created here is the base dataset used in the next module for road-risk assessment. The planned next step is to intersect roads with hazard polygons and rank impacted segments.

**Planned**

- polygon/edge impact analysis
- risk classification on the road graph
- road-level disruption scoring

---

## 19. How to Explain to an SIH Judge

**Implemented**

“This module builds the road backbone for the logistics platform using OpenStreetMap and OSMnx. It stores the road network as a directed graph with geometry and metadata, keeping a local cache for reuse. This allows us to connect satellite hazard information to actual roads in later modules without inventing a custom road map from scratch.”

---

## 20. Likely Judge Questions and Concise Answers

1. Why not use a raw GeoJSON file instead of a graph?  
   Because a graph is needed for directed routing and future road-risk assessment, not just visualization.

2. Why `MultiDiGraph`?  
   Because roads can have parallel directed segments and multiple edges between nodes are common in real-world transport networks.

3. Why keep geometry?  
   Because later modules will intersect road lines with hazard polygons to determine affected segments.

4. Why cache GraphML?  
   Because repeated downloads are costly and unnecessary for static road data in a focused AOI.

5. Is OSM perfect?  
   No. It is useful for an MVP but not guaranteed to be complete or fully updated for every local road.

6. Does this module calculate safe routes?  
   No. This is only the data ingestion and graph modeling step.

7. Why not hard-code EPSG:32646?  
   Because geographic OSM data is generally stored in `EPSG:4326`, and project-specific metric conversion is kept simple for the current scope.

8. What comes next?  
   Road-risk assessment and later route calculation in Module 6 and Module 7.

---

## Status Summary

**Implemented**

- road-network service
- BBox validation
- OSMnx-driven graph retrieval
- `MultiDiGraph` structure
- GraphML cache save/load
- API summary endpoint
- unit tests covering core behavior

**Planned**

- road-risk scoring
- flood/road intersection
- alternate route calculation
- alerts and offline synchronization
