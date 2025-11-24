#!/usr/bin/env python3
"""Create a mock non-compliant IFC structure to generate failures for testing."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.unified_compliance_engine import UnifiedComplianceEngine

# Create a mock graph with non-compliant elements
mock_graph = {
    "schema": "IFC2X3",
    "elements": {
        "doors": [
            {
                "guid": "door_001_narrow",
                "ifc_class": "IfcDoor",
                "name": "Narrow Door",
                "attributes": {
                    "property_sets": {
                        "Pset_DoorCommon": {
                            "IsAccessible": True,
                            "FireExit": False
                        },
                        "BaseQuantities": {
                            "Width": 0.6,    # 600mm - FAILS ADA min 813mm
                            "Height": 2.1,   # 2100mm - OK
                            "Depth": 0.1,
                            "Perimeter": 5.4,
                            "Area": 1.26,
                            "Volume": 0.126
                        }
                    }
                },
                "width_mm": 600.0,
                "height_mm": 2100.0
            },
            {
                "guid": "door_002_short",
                "ifc_class": "IfcDoor",
                "name": "Short Exit Door",
                "attributes": {
                    "property_sets": {
                        "Pset_DoorCommon": {
                            "IsAccessible": False,
                            "FireExit": True
                        },
                        "BaseQuantities": {
                            "Width": 0.9,    # 900mm - OK
                            "Height": 1.8,   # 1800mm - FAILS exit min 2032mm
                            "Depth": 0.1,
                            "Perimeter": 5.6,
                            "Area": 1.62,
                            "Volume": 0.162
                        }
                    }
                },
                "width_mm": 900.0,
                "height_mm": 1800.0
            }
        ],
        "spaces": [
            {
                "guid": "space_001_small",
                "ifc_class": "IfcSpace",
                "name": "Tiny Bedroom",
                "area_m2": 5.0,  # FAILS bedroom min 6.5m²
                "usage_type": "Bedroom",
                "attributes": {
                    "property_sets": {
                        "Pset_SpaceCommon": {
                            "IsAccessible": True,
                            "UsageType": "Bedroom"
                        },
                        "BaseQuantities": {
                            "Height": 2.7,
                            "GrossFloorArea": 5.0,
                            "NetFloorArea": 5.0
                        }
                    }
                }
            }
        ],
        "window": [
            {
                "guid": "window_001_small",
                "ifc_class": "IfcWindow",
                "name": "Small Window",
                "attributes": {
                    "property_sets": {
                        "Pset_WindowCommon": {
                            "IsExternal": True
                        },
                        "BaseQuantities": {
                            "Width": 0.8,     # 800mm
                            "Height": 0.8,    # 800mm
                            "Area": 0.64      # 0.64m² - FAILS bedroom window min 0.93m²
                        }
                    }
                }
            }
        ]
    }
}

# Run compliance check
rules_file = Path(__file__).parent / 'rules_config' / 'enhanced-regulation-rules.json'
engine = UnifiedComplianceEngine(str(rules_file))
results = engine.check_graph(mock_graph, engine.rules, None)

print("=" * 70)
print("COMPLIANCE CHECK RESULTS - MOCK NON-COMPLIANT IFC")
print("=" * 70)
print(f"\nSummary:")
print(f"  Total checks: {results['total_checks']}")
print(f"  Passed: {results['passed']} ✅")
print(f"  Failed: {results['failed']} ❌")
print(f"  Unable: {results['unable']} ⚠️")
print(f"  Pass rate: {results['pass_rate']:.1%}")

print(f"\n{'=' * 70}")
print("FAILURES REQUIRING FIXES:")
print(f"{'=' * 70}")

failures = [r for r in results.get('results', []) if r.get('passed') is False]
for i, failure in enumerate(failures, 1):
    elem_name = failure.get('element_name') or failure.get('name') or 'Unknown'
    print(f"\n{i}. {failure['element_type']} - {elem_name}")
    print(f"   Rule: {failure['rule_id']}")
    print(f"   Issue: {failure['explanation']}")
    print(f"   Severity: {failure['severity']}")

print(f"\n{'=' * 70}")
print("ELEMENTS NEEDING REMEDIATION:")
print(f"{'=' * 70}")

failures_by_element = {}
for failure in failures:
    elem_name = failure.get('element_name') or failure.get('name') or 'Unknown'
    if elem_name not in failures_by_element:
        failures_by_element[elem_name] = []
    failures_by_element[elem_name].append({
        'rule': failure['rule_id'],
        'explanation': failure['explanation']
    })

for elem_name, issues in failures_by_element.items():
    print(f"\n📍 {elem_name}:")
    for issue in issues:
        print(f"   • {issue['rule']}")
        print(f"     {issue['explanation']}")

# Save results to file for frontend testing
output_file = Path(__file__).parent / 'mock_compliance_results.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n\n✅ Results saved to: {output_file}")
print("\nTo test the Reasoning Layer with these failures:")
print("1. Manually upload AC20-Institute-Var-2.ifc (or use mock data)")
print("2. The system will now show failures that need fixes")
print("3. Click on failed elements to see detailed explanations")
