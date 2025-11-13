from __future__ import annotations

import unittest
from data_layer.extract_rules import extract_rules_from_graph


class ExtractRulesTests(unittest.TestCase):
    def test_extracts_door_min_width_and_space_min_area(self):
        # Build a tiny fake graph similar to data-layer output
        graph = {
            "building_id": "TEST",
            "elements": {
                "doors": [
                    {
                        "id": "D1",
                        "ifc_guid": "D1",
                        "name": "Door1",
                        "width_mm": 800.0,
                        "attributes": {
                            "property_sets": {
                                "Pset_ProjectRules": {
                                    "MinDoorWidth": 900
                                }
                            }
                        }
                    }
                ],
                "spaces": [
                    {
                        "id": "S1",
                        "ifc_guid": "S1",
                        "name": "Room1",
                        "area_m2": 10.0,
                        "attributes": {
                            "property_sets": {
                                "Pset_ProjectRules": {
                                    "MinArea": 12.0
                                }
                            }
                        }
                    }
                ]
            }
        }

        manifest = extract_rules_from_graph(graph)
        rules = manifest.get("rules", [])
        # Expect at least two rules extracted
        self.assertTrue(any(r["target_type"] == "door" for r in rules))
        self.assertTrue(any(r["target_type"] == "space" for r in rules))


if __name__ == "__main__":
    unittest.main()
