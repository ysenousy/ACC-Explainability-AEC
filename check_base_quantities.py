#!/usr/bin/env python3
"""Check BaseQuantities values and units."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_layer.services import DataLayerService

# Load IFC file
ifc_path = Path(__file__).parent / 'acc-dataset' / 'IFC' / 'AC20-Institute-Var-2.ifc'
print(f"Loading IFC: {ifc_path}")

data_svc = DataLayerService()
graph = data_svc.build_graph(str(ifc_path))

# Check first door
doors = graph.get('elements', {}).get('doors', [])
if doors:
    door = doors[0]
    print(f"\nSample Door:")
    print(f"  GUID: {door.get('guid')}")
    print(f"  Name: {door.get('name')}")
    print(f"  Direct properties:")
    print(f"    width_mm: {door.get('width_mm')}")
    print(f"    height_mm: {door.get('height_mm')}")
    
    base_q = door.get('attributes', {}).get('property_sets', {}).get('BaseQuantities', {})
    print(f"  BaseQuantities:")
    for key, val in base_q.items():
        print(f"    {key}: {val} (type: {type(val).__name__})")

# Check first space
spaces = graph.get('elements', {}).get('spaces', [])
if spaces:
    space = spaces[0]
    print(f"\nSample Space:")
    print(f"  GUID: {space.get('guid')}")
    print(f"  Name: {space.get('name')}")
    print(f"  Direct properties:")
    print(f"    width_mm: {space.get('width_mm')}")
    print(f"    area_m2: {space.get('area_m2')}")
    
    base_q = space.get('attributes', {}).get('property_sets', {}).get('BaseQuantities', {})
    print(f"  BaseQuantities:")
    for key, val in base_q.items():
        print(f"    {key}: {val} (type: {type(val).__name__})")
