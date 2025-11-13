from __future__ import annotations

import json
import unittest
from pathlib import Path

from data_layer import DataLayerService


FIXTURE_IFC = Path(__file__).resolve().parents[1] / "acc-dataset" / "IFC" / "AC20-FZK-Haus.ifc"


@unittest.skipUnless(FIXTURE_IFC.exists(), "Fixture IFC file not found; skipping data layer tests.")
class DataLayerServiceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = DataLayerService()

    def test_build_graph_contains_expected_sections(self) -> None:
        graph = self.service.build_graph(FIXTURE_IFC)

        self.assertIn("elements", graph)
        self.assertIn("meta", graph)
        self.assertIn("coverage", graph["meta"])
        self.assertIn("generated_at", graph)

        spaces = graph["elements"]["spaces"]
        doors = graph["elements"]["doors"]

        self.assertIsInstance(spaces, list)
        self.assertGreater(len(spaces), 0)
        self.assertIsInstance(doors, list)

        first_space = spaces[0]
        self.assertIn("id", first_space)
        self.assertIn("provenance", first_space)
        self.assertIn("storey", first_space)

        if doors:
            first_door = doors[0]
            self.assertIn("connected_spaces", first_door)

    def test_preview_returns_summary(self) -> None:
        summary = self.service.preview(FIXTURE_IFC)
        self.assertIn("counts", summary)
        self.assertIn("schema", summary)
        json.dumps(summary)  # should be serialisable without raising

    def test_save_graph_persists_file(self) -> None:
        out_dir = Path(__file__).resolve().parent / "artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "test_graph.json"

        try:
            path = self.service.save_graph(FIXTURE_IFC, out_path=out_file)
            self.assertTrue(path.exists())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("elements", loaded)
        finally:
            if out_file.exists():
                out_file.unlink()
            if out_dir.exists() and not any(out_dir.iterdir()):
                out_dir.rmdir()


if __name__ == "__main__":
    unittest.main()

