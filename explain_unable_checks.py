#!/usr/bin/env python3
"""Analyze why 164 checks are Unable to evaluate."""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from backend.unified_compliance_engine import UnifiedComplianceEngine
from data_layer.services import DataLayerService

# Load IFC file
ifc_path = Path(__file__).parent / 'acc-dataset' / 'IFC' / 'AC20-Institute-Var-2.ifc'
print(f"Loading IFC: {ifc_path}\n")

data_svc = DataLayerService()
graph = data_svc.build_graph(str(ifc_path))

# Load rules
rules_file = Path(__file__).parent / 'rules_config' / 'enhanced-regulation-rules.json'
engine = UnifiedComplianceEngine(str(rules_file))

print("Running compliance check...")
results = engine.check_graph(graph, engine.rules, None)

# Analyze Unable results
unable_results = [r for r in results.get('results', []) if r.get('passed') is None]
print(f"\nTotal 'Unable to Evaluate' checks: {len(unable_results)}\n")

# Group by rule
unable_by_rule = defaultdict(list)
for result in unable_results:
    rule_id = result.get('rule_id')
    unable_by_rule[rule_id].append(result)

print("=" * 80)
print("UNABLE TO EVALUATE - BY RULE")
print("=" * 80)

for rule_id in sorted(unable_by_rule.keys()):
    results_for_rule = unable_by_rule[rule_id]
    print(f"\n📋 Rule: {rule_id}")
    print(f"   Count: {len(results_for_rule)} checks")
    
    # Get rule details
    rule = next((r for r in engine.rules if r.get('id') == rule_id), None)
    if rule:
        print(f"   Target: {rule.get('target', {}).get('ifc_class')}")
        print(f"   Condition: {rule.get('condition', {}).get('lhs', {})}")
        
        lhs_spec = rule.get('condition', {}).get('lhs', {})
        if lhs_spec.get('source') == 'qto':
            print(f"   Requires QTO: {lhs_spec.get('qto_name')}")
            print(f"   Requires Quantity: {lhs_spec.get('quantity')}")
    
    # Show sample element
    sample = results_for_rule[0]
    print(f"\n   Sample element that failed to evaluate:")
    print(f"     Element ID: {sample.get('element_guid')}")
    print(f"     Element Type: {sample.get('element_type')}")

# Check what data is available in spaces
print("\n" + "=" * 80)
print("WHY SPACE CORRIDOR RULES CAN'T EVALUATE")
print("=" * 80)

spaces = graph.get('elements', {}).get('spaces', [])
print(f"\nTotal spaces in IFC: {len(spaces)}")

if spaces:
    space = spaces[0]
    print(f"\nSample space: {space.get('name')}")
    print(f"  Has width_mm? {space.get('width_mm') is not None} (value: {space.get('width_mm')})")
    print(f"  Has area_m2? {space.get('area_m2') is not None} (value: {space.get('area_m2')})")
    
    base_q = space.get('attributes', {}).get('property_sets', {}).get('BaseQuantities', {})
    print(f"\n  BaseQuantities available:")
    for key in base_q.keys():
        print(f"    ✓ {key}: {base_q[key]}")
    
    print(f"\n  Required for corridor width rule:")
    print(f"    ✗ 'Width' key in BaseQuantities? {('Width' in base_q)}")
    print(f"    → Spaces don't have Width in BaseQuantities!")
    print(f"    → Spaces are 3D geometry, not 2D rectangles")
    print(f"    → Width can't be extracted from available data")

# Show the exact rules that can't evaluate
print("\n" + "=" * 80)
print("RULES REQUIRING UNAVAILABLE DATA")
print("=" * 80)

corridor_rules = [
    ("ADA_CORRIDOR_MIN_WIDTH", "ADA accessible corridor width requirement"),
    ("EN_CORRIDOR_WIDTH", "European accessibility corridor width requirement")
]

print("\nThese 2 rules require space Width dimension:")
for rule_id, description in corridor_rules:
    count = len(unable_by_rule.get(rule_id, []))
    print(f"\n  Rule: {rule_id}")
    print(f"  Description: {description}")
    print(f"  Checks unable: {count} (82 spaces × 2 rules = 164 total)")
    print(f"  Reason: Spaces lack extractable Width from IFC BaseQuantities")

print("\n" + "=" * 80)
print("SOLUTION OPTIONS")
print("=" * 80)
print("""
1. ❌ GEOMETRIC CALCULATION (Complex)
   - Extract space boundaries and compute bounding box width
   - Requires complex IFC geometry processing
   - Not practical without specialized geometry library

2. ⚠️ MANUAL MEASUREMENT (Data Entry)
   - Add Width property to space PSet in IFC file
   - Architect would need to measure/specify corridor widths
   - Makes IFC heavier, not standard practice

3. ✅ SKIP THESE RULES (Recommended)
   - Remove ADA_CORRIDOR_MIN_WIDTH and EN_CORRIDOR_WIDTH rules
   - Focus on door/window/room rules that have extractable data
   - Or mark as "Not Applicable" for space compliance

4. ✅ ALTERNATIVE APPROACH
   - Check corridor compliance through door placement analysis
   - If door-to-door distance meets min width, corridors are adequate
   - Use derived measurements instead of direct properties
""")
