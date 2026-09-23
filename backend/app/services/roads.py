"""Road network ingestion service for OpenStreetMap + OSMnx + NetworkX."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, Tuple

import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, Point
from shapely import wkt

logger = logging.getLogger(__name__)

CACHE_ROADS_DIR = os.path.abspath(
    os.getenv(
        "ROADS_CACHE_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache", "roads"),
    )
)


class RoadNetworkService:
    """Minimal road-network service for Module 5."""

    def __init__(self, cache_dir: str = CACHE_ROADS_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        ox.settings.use_cache = True
        ox.settings.log_console = False

    @staticmethod
    def validate_bbox(
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> Tuple[float, float, float, float]:
        """Validate a geographic bounding box."""
        if not all(value is not None for value in (min_lon, min_lat, max_lon, max_lat)):
            raise ValueError("All bounding box values are required.")

        min_lon, min_lat, max_lon, max_lat = map(float, (min_lon, min_lat, max_lon, max_lat))

        if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
            raise ValueError("Longitude bounds must be between -180 and 180.")
        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise ValueError("Latitude bounds must be between -90 and 90.")
        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError("Bounding box min values must be less than max values.")

        return min_lon, min_lat, max_lon, max_lat

    @staticmethod
    def compute_bbox_hash(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
        key = f"{min_lon:.4f}_{min_lat:.4f}_{max_lon:.4f}_{max_lat:.4f}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]

    def _get_cache_filepath(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
        h = self.compute_bbox_hash(min_lon, min_lat, max_lon, max_lat)
        return os.path.join(self.cache_dir, f"road_graph_{h}.graphml")

    def create_synthetic_road_graph(
        self,
        min_lon: float = 91.50,
        min_lat: float = 26.00,
        max_lon: float = 92.00,
        max_lat: float = 26.50,
    ) -> nx.MultiDiGraph:
        """Simple deterministic fallback graph for tests and offline operation."""
        G = nx.MultiDiGraph()
        G.graph["crs"] = "EPSG:4326"

        lats = [min_lat + (max_lat - min_lat) * i / 4.0 for i in range(5)]
        lons = [min_lon + (max_lon - min_lon) * j / 4.0 for j in range(5)]

        node_id = 1
        node_grid = {}
        for r_idx, lat in enumerate(lats):
            for c_idx, lon in enumerate(lons):
                G.add_node(node_id, y=lat, x=lon, osmid=node_id, street_count=4)
                node_grid[(r_idx, c_idx)] = node_id
                node_id += 1

        for r_idx in range(5):
            for c_idx in range(5):
                u = node_grid[(r_idx, c_idx)]

                if c_idx < 4:
                    v = node_grid[(r_idx, c_idx + 1)]
                    u_lon, u_lat = G.nodes[u]["x"], G.nodes[u]["y"]
                    v_lon, v_lat = G.nodes[v]["x"], G.nodes[v]["y"]
                    geom = LineString([(u_lon, u_lat), ((u_lon + v_lon) / 2.0, (u_lat + v_lat) / 2.0), (v_lon, v_lat)])
                    dist_m = float(Point(u_lon, u_lat).distance(Point(v_lon, v_lat)) * 111320.0)
                    label = "Assam Trunk Highway" if r_idx == 2 else "Regional Connector"
                    G.add_edge(
                        u, v, 0,
                        osmid=1000 + u,
                        name=f"{label} {r_idx + 1}",
                        highway="trunk" if r_idx == 2 else "primary",
                        oneway=False,
                        length=round(dist_m, 2),
                        maxspeed="60",
                        geometry=geom,
                    )
                    G.add_edge(
                        v, u, 0,
                        osmid=1000 + u,
                        name=f"{label} {r_idx + 1}",
                        highway="trunk" if r_idx == 2 else "primary",
                        oneway=False,
                        length=round(dist_m, 2),
                        geometry=LineString(list(geom.coords)[::-1]),
                    )

                if r_idx < 4:
                    v = node_grid[(r_idx + 1, c_idx)]
                    u_lon, u_lat = G.nodes[u]["x"], G.nodes[u]["y"]
                    v_lon, v_lat = G.nodes[v]["x"], G.nodes[v]["y"]
                    geom = LineString([(u_lon, u_lat), (v_lon, v_lat)])
                    dist_m = float(Point(u_lon, u_lat).distance(Point(v_lon, v_lat)) * 111320.0)
                    G.add_edge(
                        u, v, 0,
                        osmid=2000 + u,
                        name=f"Regional Link Corridor {c_idx + 1}",
                        highway="secondary",
                        oneway=False,
                        length=round(dist_m, 2),
                        maxspeed="40",
                        geometry=geom,
                    )
                    G.add_edge(
                        v, u, 0,
                        osmid=2000 + u,
                        name=f"Regional Link Corridor {c_idx + 1}",
                        highway="secondary",
                        oneway=False,
                        length=round(dist_m, 2),
                        geometry=LineString([(v_lon, v_lat), (u_lon, u_lat)]),
                    )

        return G

    def save_graph_to_cache(self, G: nx.MultiDiGraph, path: str) -> str:
        """Persist graph to GraphML while converting Shapely geometry to WKT for compatibility."""
        snapshot = G.copy()
        for _, _, _, data in snapshot.edges(keys=True, data=True):
            geom = data.get("geometry")
            if geom is not None:
                data["geometry_wkt"] = geom.wkt
                data.pop("geometry", None)
        nx.write_graphml(snapshot, path)
        return path

    def load_graph_from_cache(self, path: str) -> nx.MultiDiGraph:
        """Load cached graph and restore WKT geometry back to Shapely LineString objects."""
        G = nx.read_graphml(path, force_multigraph=True)
        for _, _, _, data in G.edges(keys=True, data=True):
            geom_wkt = data.get("geometry_wkt")
            if geom_wkt:
                data["geometry"] = wkt.loads(geom_wkt)
                data.pop("geometry_wkt", None)
        G.graph.setdefault("crs", "EPSG:4326")
        return G

    def get_road_network_for_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        force_refresh: bool = False,
        allow_fallback: bool = False,
    ) -> Tuple[nx.MultiDiGraph, str]:
        """Return a cached graph when available or a live OSM graph; never silently use synthetic roads in production."""
        min_lon, min_lat, max_lon, max_lat = self.validate_bbox(min_lon, min_lat, max_lon, max_lat)
        cache_path = self._get_cache_filepath(min_lon, min_lat, max_lon, max_lat)

        if not force_refresh and os.path.exists(cache_path):
            try:
                return self.load_graph_from_cache(cache_path), "cache"
            except Exception as exc:
                logger.warning("Failed to load cached road graph: %s", exc)

        try:
            bbox = (max_lat, min_lat, max_lon, min_lon)
            G = ox.graph_from_bbox(bbox=bbox, network_type="drive", simplify=True)
            if G.number_of_edges() == 0:
                raise ValueError("OSMnx returned an empty graph for the requested bounding box.")

            for u, v, k, data in G.edges(keys=True, data=True):
                data.setdefault("name", "Unnamed Road")
                data.setdefault("highway", "unclassified")
                data.setdefault("length", 0.0)
                data.setdefault("oneway", False)
                if "geometry" not in data:
                    u_x, u_y = G.nodes[u]["x"], G.nodes[u]["y"]
                    v_x, v_y = G.nodes[v]["x"], G.nodes[v]["y"]
                    data["geometry"] = LineString([(u_x, u_y), (v_x, v_y)])
                data["crs"] = "EPSG:4326"

            try:
                self.save_graph_to_cache(G, cache_path)
            except Exception as save_err:
                logger.warning("Failed to cache graph: %s", save_err)

            return G, "live_osm"
        except Exception as osm_err:
            logger.warning(
                "OSM / OSMnx query failed for BBox (%s, %s, %s, %s): %s",
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                osm_err,
            )
            if allow_fallback:
                logger.warning("Synthetic fallback allowed only for explicit test use.")
                fallback = self.create_synthetic_road_graph(min_lon, min_lat, max_lon, max_lat)
                return fallback, "synthetic_fallback"
            raise RuntimeError(f"Unable to fetch road network from OpenStreetMap for bbox ({min_lon}, {min_lat}, {max_lon}, {max_lat}): {osm_err}")

    def graph_to_geojson(self, G: nx.MultiDiGraph) -> Dict[str, Any]:
        """Serialize the graph to a minimal GeoJSON feature collection."""
        features = []
        for u, v, k, data in G.edges(keys=True, data=True):
            geom = data.get("geometry")
            if geom is None:
                u_x, u_y = G.nodes[u]["x"], G.nodes[u]["y"]
                v_x, v_y = G.nodes[v]["x"], G.nodes[v]["y"]
                coords = [[u_x, u_y], [v_x, v_y]]
            else:
                coords = [list(pt) for pt in geom.coords]

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "road_id": f"{u}_{v}_{k}",
                        "u": int(u),
                        "v": int(v),
                        "key": int(k),
                        "name": data.get("name", "Unnamed Road"),
                        "highway": data.get("highway", "unclassified"),
                        "length_m": float(data.get("length", 0.0)),
                        "oneway": bool(data.get("oneway", False)),
                        "maxspeed": data.get("maxspeed", "N/A"),
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "nodes_count": G.number_of_nodes(),
                "edges_count": G.number_of_edges(),
                "crs": G.graph.get("crs", "EPSG:4326"),
            },
        }

    @staticmethod
    def get_network_statistics(G: nx.MultiDiGraph) -> Dict[str, Any]:
        """Return summary statistics for the graph."""
        total_length_m = sum(float(data.get("length", 0.0)) for _, _, data in G.edges(data=True))
        highway_counts: Dict[str, int] = {}
        for _, _, data in G.edges(data=True):
            highway = data.get("highway", "unclassified")
            if isinstance(highway, list):
                highway = highway[0] if highway else "unclassified"
            highway_counts[highway] = highway_counts.get(highway, 0) + 1
        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "total_length_km": round(total_length_m / 1000.0, 2),
            "highway_classes": highway_counts,
            "crs": G.graph.get("crs", "EPSG:4326"),
        }

    def get_summary(self, G: nx.MultiDiGraph, source_mode: str = "cache") -> Dict[str, Any]:
        return {
            "success": True,
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "crs": G.graph.get("crs", "EPSG:4326"),
            "cache_used": source_mode == "cache",
            "source_mode": source_mode,
        }


road_network_service = RoadNetworkService()


def get_road_network_service() -> RoadNetworkService:
    return road_network_service
