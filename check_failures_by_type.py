#!/usr/bin/env python3
"""Check what element types have failures in compliance check."""

import sys
import json
from pathlib import Path
from collections import defaultdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.unified_compliance_engine import UnifiedComplianceEngine
from data_layer.services import DataLayerService

# Load IFC file
ifc_path = Path(__file__).parent / 'acc-dataset' / 'IFC' / 'AC20-Institute-Var-2.ifc'
print(f"Loading IFC: {ifc_path}")

data_svc = DataLayerService()
model = data_svc.load_model(str(ifc_path))
graph = data_svc.build_graph(str(ifc_path))

print(f"\nGraph elements available:")
elements = graph.get('elements', {})
for elem_type, elem_list in elements.items():
    print(f"  {elem_type}: {len(elem_list) if isinstance(elem_list, list) else 0} items")

# Load rules
rules_file = Path(__file__).parent / 'rules_config' / 'enhanced-regulation-rules.json'
engine = UnifiedComplianceEngine(str(rules_file))

print(f"\nRunning compliance check...")
results = engine.check_graph(graph, engine.rules, None)

# Group results by element type
failures_by_type = defaultdict(lambda: {'count': 0, 'sample_rules': set()})
passes_by_type = defaultdict(lambda: {'count': 0, 'sample_rules': set()})
unable_by_type = defaultdict(lambda: {'count': 0, 'sample_rules': set()})

for result in results.get('results', []):
    elem_type = result.get('element_type', 'Unknown')
    rule_id = result.get('rule_id', 'Unknown')
    passed = result.get('passed')
    
    if passed is True:
        passes_by_type[elem_type]['count'] += 1
        passes_by_type[elem_type]['sample_rules'].add(rule_id)
    elif passed is False:
        failures_by_type[elem_type]['count'] += 1
        failures_by_type[elem_type]['sample_rules'].add(rule_id)
    else:
        unable_by_type[elem_type]['count'] += 1
        unable_by_type[elem_type]['sample_rules'].add(rule_id)

print(f"\n{'='*60}")
print(f"SUMMARY: {results['total_checks']} total checks")
print(f"  Passed: {results['passed']}")
print(f"  Failed: {results['failed']}")
print(f"  Unable: {results['unable']}")

print(f"\n{'='*60}")
print("FAILURES BY ELEMENT TYPE:")
for elem_type in sorted(failures_by_type.keys()):
    count = failures_by_type[elem_type]['count']
    rules = failures_by_type[elem_type]['sample_rules']
    print(f"\n  {elem_type}: {count} failures")
    print(f"    Rules: {', '.join(sorted(rules))}")

print(f"\n{'='*60}")
print("PASSES BY ELEMENT TYPE:")
for elem_type in sorted(passes_by_type.keys()):
    count = passes_by_type[elem_type]['count']
    rules = passes_by_type[elem_type]['sample_rules']
    print(f"\n  {elem_type}: {count} passes")
    print(f"    Rules: {', '.join(sorted(rules))}")

print(f"\n{'='*60}")
print("UNABLE BY ELEMENT TYPE:")
for elem_type in sorted(unable_by_type.keys()):
    count = unable_by_type[elem_type]['count']
    rules = unable_by_type[elem_type]['sample_rules']
    print(f"\n  {elem_type}: {count} unable")
    print(f"    Rules: {', '.join(sorted(rules))}")

# Show sample failures
print(f"\n{'='*60}")
print("SAMPLE FAILURE DETAILS:")
sample_failures = [r for r in results.get('results', []) if r.get('passed') is False][:5]
for i, failure in enumerate(sample_failures, 1):
    print(f"\n  {i}. {failure.get('element_type')} - Rule: {failure.get('rule_id')}")
    print(f"     Element: {failure.get('element_name')} ({failure.get('element_guid')[:8]}...)")
    print(f"     Explanation: {failure.get('explanation')}")
