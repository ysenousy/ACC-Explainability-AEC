from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

from rule_layer import BaseRule, RuleConfig, get_all_rules, get_ruleset_metadata, load_rule_config
from rule_layer.config import (
    BuildingRuleConfig,
    DoorRuleConfig,
    SpaceRuleConfig,
)
from rule_layer.engine import RuleEngine
from rule_layer.io import save_results
from rule_layer.models import RuleResult, RuleSeverity, RuleStatus
from rule_layer.rules.building import MaxOccupancyPerStoreyRule
from rule_layer.rules.doors import MinDoorWidthRule
from rule_layer.rules.spaces import MinSpaceAreaRule


SAMPLE_GRAPH: Dict[str, object] = {
    "building_id": "TestBuilding",
    "elements": {
        "doors": [
            {
                "id": "D1",
                "name": "Door Wide",
                "width_mm": 900.0,
                "connected_spaces": [{"space_id": "S1"}, {"space_id": "S2"}],
            },
            {
                "id": "D2",
                "name": "Door Narrow",
                "width_mm": 700.0,
                "connected_spaces": [{"space_id": "S2"}],
            },
            {
                "id": "D3",
                "name": "Door Unknown",
                "connected_spaces": [{"space_id": "S3"}],
            },
        ],
        "spaces": [
            {
                "id": "S1",
                "name": "Lobby",
                "storey": "Level 1",
                "area_m2": 20.0,
                "attributes": {
                    "property_sets": {
                        "OccupancyPset": {"Occupancy": 30},
                        "BaseQuantities": {"NetFloorArea": 20.0},
                    }
                },
            },
            {
                "id": "S2",
                "name": "Office",
                "storey": "Level 1",
                "area_m2": 4.0,
                "attributes": {
                    "property_sets": {
                        "OccupancyPset": {"Occupancy": 25},
                        "BaseQuantities": {"NetFloorArea": 4.0},
                    }
                },
            },
            {
                "id": "S3",
                "name": "Storage",
                "storey": "Level 2",
                "attributes": {
                    "property_sets": {
                        "BaseQuantities": {"NetFloorArea": 10.0},
                    }
                },
            },
        ],
    },
    "meta": {"schema": "IFC4", "coverage": {"num_spaces": 3, "num_doors": 3}},
}


class RuleLayerConfigTests(unittest.TestCase):
    def test_load_rule_config_from_mapping(self) -> None:
        data = {
            "door": {"min_width_mm": 800, "severity": "warning"},
            "space": {"min_area_m2": 10, "severity": "INFO"},
            "building": {"max_occupancy_per_storey": 40, "severity": "ERROR"},
            "ruleset_id": "custom_ruleset_v1",
        }
        config = load_rule_config(data)

        self.assertEqual(config.door.min_width_mm, 800.0)
        self.assertEqual(config.door.severity, RuleSeverity.WARNING)
        self.assertEqual(config.space.min_area_m2, 10.0)
        self.assertEqual(config.space.severity, RuleSeverity.INFO)
        self.assertEqual(config.building.max_occupancy_per_storey, 40)
        self.assertEqual(config.ruleset_id, "custom_ruleset_v1")

    def test_get_all_rules_uses_config(self) -> None:
        config = RuleConfig(
            door=DoorRuleConfig(min_width_mm=750.0, severity=RuleSeverity.WARNING),
            space=SpaceRuleConfig(min_area_m2=5.0, severity=RuleSeverity.INFO),
            building=BuildingRuleConfig(max_occupancy_per_storey=60, severity=RuleSeverity.ERROR),
            ruleset_id="rs_test",
        )

        rules = get_all_rules(config)
        self.assertEqual(len(rules), 3)

        door_rule = next(r for r in rules if isinstance(r, MinDoorWidthRule))
        self.assertEqual(door_rule.min_width_mm, 750.0)
        self.assertEqual(door_rule.severity, RuleSeverity.WARNING)

        space_rule = next(r for r in rules if isinstance(r, MinSpaceAreaRule))
        self.assertEqual(space_rule.min_area_m2, 5.0)
        self.assertEqual(space_rule.severity, RuleSeverity.INFO)

        building_rule = next(r for r in rules if isinstance(r, MaxOccupancyPerStoreyRule))
        self.assertEqual(building_rule.max_occupancy, 60)
        self.assertEqual(building_rule.severity, RuleSeverity.ERROR)

        metadata = get_ruleset_metadata(config)
        self.assertEqual(metadata["ruleset_id"], "rs_test")
        self.assertEqual(len(metadata["rules"]), 3)


class RuleEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        config = RuleConfig()
        self.rules = get_all_rules(config)
        self.engine = RuleEngine(self.rules)

    def test_rule_engine_evaluates_graph(self) -> None:
        results = self.engine.run(SAMPLE_GRAPH)  # type: ignore[arg-type]
        self.assertGreaterEqual(len(results), 5)

        door_results = [r for r in results if r.target_type == "door"]
        self.assertEqual(len(door_results), 3)
        self.assertTrue(any(r.status == RuleStatus.FAIL for r in door_results))

        space_results = [r for r in results if r.target_type == "space"]
        self.assertEqual(len(space_results), 3)
        self.assertTrue(any(r.status == RuleStatus.FAIL for r in space_results))

        storey_results = [r for r in results if r.target_type == "storey"]
        self.assertTrue(any(r.status == RuleStatus.FAIL for r in storey_results))
        self.assertTrue(any(r.status == RuleStatus.NOT_APPLICABLE for r in storey_results))

    def test_rule_engine_handles_rule_exception(self) -> None:
        class FaultyRule(BaseRule):
            id = "FAULTY"
            name = "Faulty Rule"

            def evaluate(self, graph):  # type: ignore[override]
                raise RuntimeError("boom")

        engine = RuleEngine(self.rules + [FaultyRule()], strict=False)
        results = engine.run(SAMPLE_GRAPH)  # type: ignore[arg-type]
        fallback = [r for r in results if r.rule_id == "FAULTY"]
        self.assertEqual(len(fallback), 1)
        self.assertEqual(fallback[0].status, RuleStatus.NOT_APPLICABLE)

        engine_strict = RuleEngine([FaultyRule()], strict=True)
        with self.assertRaises(RuntimeError):
            engine_strict.run(SAMPLE_GRAPH)  # type: ignore[arg-type]


class RuleIOTests(unittest.TestCase):
    def test_save_results_uses_graph_metadata(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        try:
            graph_path = temp_dir / "test_dataLayer.json"
            graph_path.write_text(json.dumps(SAMPLE_GRAPH), encoding="utf-8")

            results: List[RuleResult] = [
                RuleResult(
                    rule_id="TEST",
                    rule_name="Test Rule",
                    target_type="door",
                    target_id="D1",
                    status=RuleStatus.PASS,
                    message="All good",
                    severity=RuleSeverity.INFO,
                )
            ]

            out_path = save_results(
                results,
                graph_path,
                ruleset_id="unit_test_ruleset",
                graph_metadata=SAMPLE_GRAPH,
            )
            self.assertTrue(out_path.exists())

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["building_id"], "TestBuilding")
            self.assertIn("graph_meta", payload)
            self.assertEqual(payload["ruleset_id"], "unit_test_ruleset")
        finally:
            for child in temp_dir.glob("*"):
                child.unlink()
            temp_dir.rmdir()


if __name__ == "__main__":
    unittest.main()

