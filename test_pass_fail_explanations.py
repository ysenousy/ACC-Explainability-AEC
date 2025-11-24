#!/usr/bin/env python3
"""Test pass and fail explanations with the new API endpoints."""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:5000/api"

print("=" * 80)
print("TESTING PASS AND FAIL EXPLANATIONS")
print("=" * 80)

# Sample failing door (too narrow)
fail_element = {
    "element_id": "door_fail_001",
    "element_type": "IfcDoor",
    "element_name": "Narrow Entrance Door",
    "failed_rules": [
        {
            "rule_id": "ADA_DOOR_MIN_WIDTH",
            "rule_name": "ADA Door Minimum Width",
            "actual_value": 700,
            "required_value": 813,
            "unit": "mm"
        }
    ]
}

# Sample passing door (adequate width)
pass_element = {
    "element_id": "door_pass_001",
    "element_type": "IfcDoor",
    "element_name": "Accessible Main Entrance",
    "passed_rules": [
        {
            "rule_id": "ADA_DOOR_MIN_WIDTH",
            "rule_name": "ADA Door Minimum Width",
            "actual_value": 900,
            "required_value": 813,
            "unit": "mm"
        },
        {
            "rule_id": "FIRE_EXIT_DOOR_HEIGHT",
            "rule_name": "Fire Exit Door Minimum Height",
            "actual_value": 2200,
            "required_value": 2032,
            "unit": "mm"
        }
    ]
}

print("\n" + "=" * 80)
print("1. ANALYZING A FAILED COMPLIANCE CHECK")
print("=" * 80)

try:
    response = requests.post(f"{BASE_URL}/reasoning/analyze-failure", json=fail_element)
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("\n✓ FAILURE ANALYSIS RECEIVED:")
            reasoning = data.get('reasoning', {})
            explanations = reasoning.get('element_explanations', [])
            if explanations:
                elem = explanations[0]
                print(f"\n  Element: {elem.get('element_type')} - {elem.get('element_name')}")
                analyses = elem.get('analyses', [])
                if analyses:
                    analysis = analyses[0]
                    print(f"\n  Rule: {analysis.get('rule_name')}")
                    print(f"  Why Failed: {analysis.get('failure_reason')}")
                    print(f"  Root Cause: {analysis.get('root_cause')}")
                    print(f"  User Impact: {analysis.get('impact_on_users')}")
                    
                    metrics = analysis.get('metrics', {})
                    print(f"\n  Metrics:")
                    print(f"    Actual: {metrics.get('actual_value')} {metrics.get('unit')}")
                    print(f"    Required: {metrics.get('required_value')} {metrics.get('unit')}")
                    print(f"    Deviation: {metrics.get('deviation_pct', 'N/A')}%")
                
                solutions = elem.get('solutions', [])
                if solutions:
                    print(f"\n  Solutions:")
                    for i, solution in enumerate(solutions[:2], 1):
                        print(f"\n    {i}. {solution.get('recommendation')}")
                        print(f"       Feasibility: {solution.get('feasibility')}")
                        print(f"       Cost: {solution.get('estimated_cost')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.json())
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 80)
print("2. ANALYZING PASSING COMPLIANCE CHECKS")
print("=" * 80)

try:
    response = requests.post(f"{BASE_URL}/reasoning/analyze-pass", json=pass_element)
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("\n✓ PASS ANALYSIS RECEIVED:")
            reasoning = data.get('reasoning', {})
            print(f"\n  Element: {reasoning.get('element_type')} - {reasoning.get('element_name')}")
            print(f"  Summary: {reasoning.get('summary')}")
            
            explanations = reasoning.get('compliance_explanations', [])
            for i, compliance in enumerate(explanations, 1):
                print(f"\n  {i}. {compliance.get('rule_name')}")
                print(f"     ✓ Why Passed: {compliance.get('why_passed')}")
                print(f"     Actual Value: {compliance.get('actual_value')} {compliance.get('unit')}")
                print(f"     Required: {compliance.get('required_value')} {compliance.get('unit')}")
                print(f"     Margin: {compliance.get('margin')}")
                print(f"     Beneficiaries: {compliance.get('beneficiaries')}")
                print(f"     Standard: {compliance.get('design_standard')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.json())
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
The system now provides comprehensive explanations for BOTH:

✗ FAILURES:
  - Why the element failed
  - Root causes
  - User impact
  - Metrics (actual vs required)
  - Severity level
  - Solutions with alternatives
  
✓ PASSES:
  - Why the element passed
  - Compliance margin (how much exceeds requirement)
  - Actual vs required values
  - Beneficiaries (who benefits)
  - Design standard reference
  - Rule description

Users can now understand BOTH the problems AND the benefits of compliance!
""")
