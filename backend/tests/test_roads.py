import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.roads import RoadNetworkService


class TestRoadNetworkService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = RoadNetworkService(cache_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_bbox_valid(self):
        self.assertEqual(
            self.service.validate_bbox(91.50, 26.00, 92.00, 26.50),
            (91.50, 26.00, 92.00, 26.50),
        )

    def test_validate_bbox_invalid(self):
        with self.assertRaises(ValueError):
            self.service.validate_bbox(92.00, 26.00, 91.50, 26.50)
        with self.assertRaises(ValueError):
            self.service.validate_bbox(91.50, 100.00, 92.00, 26.50)

    def test_create_synthetic_graph(self):
        G = self.service.create_synthetic_road_graph(91.50, 26.00, 92.00, 26.50)
        self.assertEqual(G.graph.get("crs"), "EPSG:4326")
        self.assertTrue(G.number_of_nodes() > 0)
        self.assertTrue(G.number_of_edges() > 0)
        self.assertIsInstance(G, __import__("networkx").MultiDiGraph)

        for _, _, data in G.edges(data=True):
            self.assertIn("length", data)
            self.assertIn("geometry", data)
            self.assertIn("highway", data)

    def test_missing_osm_attributes_are_handled(self):
        G = self.service.create_synthetic_road_graph()
        for _, _, data in G.edges(data=True):
            self.assertIn("highway", data)
            self.assertNotEqual(data.get("name", "Unnamed Road"), None)
            self.assertIn("length", data)

    def test_cache_round_trip(self):
        G = self.service.create_synthetic_road_graph()
        path = self.service._get_cache_filepath(91.50, 26.00, 92.00, 26.50)
        self.service.save_graph_to_cache(G, path)
        reloaded = self.service.load_graph_from_cache(path)
        self.assertEqual(reloaded.number_of_nodes(), G.number_of_nodes())
        self.assertEqual(reloaded.number_of_edges(), G.number_of_edges())
        self.assertEqual(reloaded.graph.get("crs"), "EPSG:4326")

    def test_api_network_summary(self):
        osm_graph = self.service.create_synthetic_road_graph()
        with patch("app.api.roads.road_network_service", self.service), patch(
            "app.services.roads.ox.graph_from_bbox", return_value=osm_graph
        ):
            client = TestClient(app)
            response = client.get(
                "/api/roads/network?min_lon=91.50&min_lat=26.00&max_lon=92.00&max_lat=26.50"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("nodes", payload)
        self.assertIn("edges", payload)
        self.assertIn("crs", payload)
        self.assertIn("cache_used", payload)
        self.assertEqual(payload["crs"], "EPSG:4326")
        self.assertEqual(payload["source_mode"], "live_osm")
        self.assertFalse(payload["cache_used"])

    def test_api_network_returns_error_when_osm_fetch_fails(self):
        with patch("app.api.roads.road_network_service", self.service), patch(
            "app.services.roads.ox.graph_from_bbox", side_effect=RuntimeError("Overpass unavailable")
        ):
            client = TestClient(app)
            response = client.get(
                "/api/roads/network?min_lon=91.50&min_lat=26.00&max_lon=92.00&max_lat=26.50"
            )

        self.assertEqual(response.status_code, 500)
        self.assertIn("Overpass unavailable", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
