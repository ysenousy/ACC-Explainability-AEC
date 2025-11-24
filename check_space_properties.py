#!/usr/bin/env python3
"""Analyze space geometry to see if width can be calculated."""

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

# Check spaces for all available properties
spaces = graph.get('elements', {}).get('spaces', [])
print(f"Total spaces: {len(spaces)}\n")

if spaces:
    # Analyze first 3 spaces
    for i, space in enumerate(spaces[:3]):
        print(f"Space {i+1}: {space.get('name')}")
        print(f"  Top-level keys: {list(space.keys())}")
        
        # Check attributes
        attrs = space.get('attributes', {})
        print(f"  Attributes: {list(attrs.keys())}")
        
        # Check property sets
        psets = attrs.get('property_sets', {})
        print(f"  Property Sets: {list(psets.keys())}")
        
        # Check for geometry
        if 'geometry' in space:
            geo = space['geometry']
            print(f"  Geometry: {geo}")
        
        # Check for bounds
        for key in ['bounds', 'bounding_box', 'bbox', 'extents']:
            if key in space:
                print(f"  {key}: {space[key]}")
        
        print()
