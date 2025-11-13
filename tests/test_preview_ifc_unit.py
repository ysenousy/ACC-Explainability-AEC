from __future__ import annotations

from data_layer.load_ifc import preview_ifc
from data_layer.load_ifc import TYPE_MAP


class FakeEntity:
    def __init__(self, type_name: str, globalid: str, name: str = None, elevation: float = None):
        self._type = type_name
        self.GlobalId = globalid
        if name is not None:
            self.Name = name
        if elevation is not None:
            self.Elevation = elevation

    def is_a(self):
        return self._type


class FakeRelation:
    def __init__(self, relating_structure, related_elements):
        # mimic IfcRelContainedInSpatialStructure
        self.RelatingStructure = relating_structure
        self.RelatedElements = related_elements


class FakeModel:
    def __init__(self):
        self._by_type = {}
        self.schema = "IFC4"

    def add(self, type_name: str, obj):
        self._by_type.setdefault(type_name, []).append(obj)

    def by_type(self, type_name: str):
        return list(self._by_type.get(type_name, []))


import unittest


class PreviewIfcUnitTests(unittest.TestCase):
    def test_preview_per_storey_counts(self):
        model = FakeModel()

        # create a storey
        storey = FakeEntity("IfcBuildingStorey", "S1", name="Storey 1", elevation=0.0)
        model.add("IfcBuildingStorey", storey)

        # create elements assigned to the storey
        space = FakeEntity("IfcSpace", "SP1", name="Room A")
        door = FakeEntity("IfcDoor", "D1", name="Door 1")
        model.add("IfcSpace", space)
        model.add("IfcDoor", door)

        # relation connecting elements to storey
        rel = FakeRelation(storey, [space, door])
        model.add("IfcRelContainedInSpatialStructure", rel)

        summary = preview_ifc(model)

        self.assertIn("counts", summary)
        counts = summary["counts"]
        self.assertEqual(counts.get("IfcBuildingStorey", 0), 1)
        self.assertEqual(counts.get("IfcSpace", 0), 1)

        self.assertIn("storey_summary", summary)
        ss = summary["storey_summary"]
        self.assertIsInstance(ss, list)
        self.assertEqual(len(ss), 1)
        storey_info = ss[0]
        sc = storey_info["counts"]
        self.assertEqual(sc["spaces"], 1)
        self.assertEqual(sc["doors"], 1)
        self.assertEqual(sc["total_elements"], 2)

    def test_preview_handles_aggregates_relation(self):
        # ensure IfcRelAggregates (RelatedObjects / RelatingObject) are handled
        model = FakeModel()
        storey = FakeEntity("IfcBuildingStorey", "S2", name="Storey 2", elevation=3.0)
        model.add("IfcBuildingStorey", storey)

        slab = FakeEntity("IfcSlab", "SL1", name="Slab 1")
        model.add("IfcSlab", slab)

        # create an aggregates-style relation: RelatingObject -> RelatedObjects
        class AggRel:
            def __init__(self, relating, related):
                self.RelatingObject = relating
                self.RelatedObjects = related

        rel = AggRel(storey, [slab])
        model.add("IfcRelAggregates", rel)

        summary = preview_ifc(model)
        self.assertIn("storey_summary", summary)
        ss = summary["storey_summary"]
        self.assertEqual(len(ss), 1)
        sc = ss[0]["counts"]
        # slab maps to 'slabs' in TYPE_MAP
        self.assertEqual(sc.get("slabs", 0), 1)


if __name__ == "__main__":
    unittest.main()
