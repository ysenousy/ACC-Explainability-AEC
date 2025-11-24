"""
Test script to check compliance scores for all IFC files against regulatory rules.
"""

import json
import sys
from pathlib import Path
from data_layer.services import DataLayerService
from backend.compliance_report_generator import ComplianceReportGenerator
from backend.unified_compliance_engine import UnifiedComplianceEngine

# Fix encoding for Windows console
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# IFC files to test
IFC_FILES = [
    "acc-dataset/IFC/AC20-FZK-Haus.ifc",
    "acc-dataset/IFC/AC20-Institute-Var-2.ifc",
    "acc-dataset/IFC/BasicHouse.ifc",
]

def test_ifc_compliance(ifc_path: str):
    """Test a single IFC file for compliance."""
    ifc_file = Path(ifc_path)
    
    if not ifc_file.exists():
        print(f"❌ File not found: {ifc_path}")
        return None
    
    print(f"\n{'='*70}")
    print(f"Testing: {ifc_file.name}")
    print(f"{'='*70}")
    
    try:
        # Load IFC and build graph
        print(f"Loading IFC...")
        svc = DataLayerService()
        graph = svc.build_graph(str(ifc_file), include_rules=False)
        
        # Get element summary
        elements = graph.get("elements", {})
        print(f"\nElements in IFC:")
        print(f"  Doors: {len(elements.get('doors', []))}")
        print(f"  Spaces: {len(elements.get('spaces', []))}")
        print(f"  Windows: {len(elements.get('windows', []))}")
        print(f"  Stairs: {len(elements.get('stairs', []))}")
        print(f"  Walls: {len(elements.get('walls', []))}")
        print(f"  Slabs: {len(elements.get('slabs', []))}")
        
        # Generate compliance report
        print(f"\nGenerating compliance report...")
        generator = ComplianceReportGenerator()
        report = generator.generate_report(graph)
        
        # Extract summary
        summary = report.get("summary", {})
        print(f"\nCompliance Summary:")
        print(f"  Total Items: {summary.get('total_items', 0)}")
        print(f"  Compliant: {summary.get('compliant_items', 0)}")
        print(f"  Non-Compliant: {summary.get('non_compliant_items', 0)}")
        print(f"  Partial: {summary.get('partial_compliance_items', 0)}")
        print(f"  Overall Compliance: {summary.get('overall_compliance_percentage', 0):.1f}%")
        
        # Show rules breakdown
        print(f"\nRules Breakdown:")
        rules_breakdown = summary.get("rules_breakdown", {})
        for rule_id, rule_info in rules_breakdown.items():
            passed = rule_info.get("passed", 0)
            failed = rule_info.get("failed", 0)
            skipped = rule_info.get("skipped", 0)
            total = passed + failed + skipped
            
            if total > 0:
                compliance_rate = (passed / total) * 100 if total > 0 else 0
                print(f"\n  {rule_info.get('rule_name', rule_id)}:")
                print(f"    [PASS] Passed: {passed}")
                print(f"    [FAIL] Failed: {failed}")
                print(f"    [SKIP] Skipped: {skipped}")
                print(f"    Compliance Rate: {compliance_rate:.1f}%")
                
                # Show failing elements if any
                if failed > 0:
                    failing = rule_info.get("failing_elements", [])
                    print(f"    Failing Elements ({len(failing)}):")
                    for elem in failing[:3]:  # Show first 3
                        print(f"      - {elem.get('element_name')} ({elem.get('element_type')})")
                    if len(failing) > 3:
                        print(f"      ... and {len(failing) - 3} more")
        
        return {
            "file": ifc_file.name,
            "overall_compliance": summary.get("overall_compliance_percentage", 0),
            "total_items": summary.get("total_items", 0),
            "compliant": summary.get("compliant_items", 0),
            "non_compliant": summary.get("non_compliant_items", 0),
            "partial": summary.get("partial_compliance_items", 0)
        }
        
    except Exception as e:
        print(f"❌ Error processing {ifc_path}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Test all IFC files."""
    print("\n" + "="*70)
    print("IFC COMPLIANCE SCORE REVIEW")
    print("="*70)
    print(f"Testing against regulatory rules from: enhanced-regulation-rules.json")
    
    results = []
    
    for ifc_path in IFC_FILES:
        result = test_ifc_compliance(ifc_path)
        if result:
            results.append(result)
    
    # Summary table
    print(f"\n\n{'='*70}")
    print("SUMMARY TABLE")
    print(f"{'='*70}\n")
    print(f"{'IFC File':<30} {'Compliance':<15} {'Items':<10} {'Pass':<8} {'Fail':<8} {'Partial':<8}")
    print(f"{'-'*70}")
    
    for result in results:
        print(f"{result['file']:<30} {result['overall_compliance']:>6.1f}%        {result['total_items']:<10} {result['compliant']:<8} {result['non_compliant']:<8} {result['partial']:<8}")
    
    # Average compliance
    if results:
        avg_compliance = sum(r['overall_compliance'] for r in results) / len(results)
        print(f"{'-'*70}")
        print(f"{'Average Compliance':<30} {avg_compliance:>6.1f}%")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
