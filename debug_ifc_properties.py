"""
Debug script to inspect element properties in IFC files.
"""

import json
from pathlib import Path
from data_layer.services import DataLayerService

IFC_FILE = "acc-dataset/IFC/AC20-Institute-Var-2.ifc"

print(f"Loading {IFC_FILE}...")
svc = DataLayerService()
graph = svc.build_graph(IFC_FILE, include_rules=False)

elements = graph.get("elements", {})

# Inspect a few doors
doors = elements.get("doors", [])
if doors:
    print(f"\n{'='*70}")
    print(f"Sample Door Properties (first 3):")
    print(f"{'='*70}")
    
    for i, door in enumerate(doors[:3]):
        print(f"\nDoor {i+1}: {door.get('name', 'Unknown')}")
        print(f"  GUID: {door.get('ifc_guid', 'N/A')}")
        print(f"  Attributes keys: {list(door.get('attributes', {}).keys())}")
        
        # Check property sets
        psets = door.get('attributes', {}).get('property_sets', {})
        print(f"  Property Sets: {list(psets.keys())}")
        
        # Check DoorCommon
        if 'Pset_DoorCommon' in psets:
            print(f"    Pset_DoorCommon: {psets['Pset_DoorCommon']}")
        
        # Check all attributes
        attrs = door.get('attributes', {})
        for key in ['is_accessible', 'fire_exit', 'usage_type', 'IsAccessible', 'FireExit']:
            if key in attrs:
                print(f"  {key}: {attrs[key]}")

# Inspect spaces
spaces = elements.get("spaces", [])
if spaces:
    print(f"\n{'='*70}")
    print(f"Sample Space Properties (first 3):")
    print(f"{'='*70}")
    
    for i, space in enumerate(spaces[:3]):
        print(f"\nSpace {i+1}: {space.get('name', 'Unknown')}")
        print(f"  GUID: {space.get('ifc_guid', 'N/A')}")
        print(f"  Attributes keys: {list(space.get('attributes', {}).keys())}")
        
        # Check property sets
        psets = space.get('attributes', {}).get('property_sets', {})
        print(f"  Property Sets: {list(psets.keys())}")
        
        # Check SpaceCommon
        if 'Pset_SpaceCommon' in psets:
            print(f"    Pset_SpaceCommon: {psets['Pset_SpaceCommon']}")
        
        # Check all attributes
        attrs = space.get('attributes', {})
        for key in ['usage_type', 'UsageType', 'area_m2']:
            if key in attrs:
                print(f"  {key}: {attrs[key]}")

print("\n" + "="*70)
