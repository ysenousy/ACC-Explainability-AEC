#!/usr/bin/env python
"""Test to verify catalogue endpoint loads from enhanced-regulation-rules.json"""

import json
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_version_manager import RulesVersionManager

def test_catalogue_source():
    """Verify that get_rules_catalogue loads from enhanced-regulation-rules.json"""
    
    print("=" * 70)
    print("CATALOGUE SOURCE TEST")
    print("=" * 70)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    rules_config_dir = project_root / "rules_config"
    
    print("\nSTEP 1: Load from RulesVersionManager (what endpoint now does)")
    version_manager = RulesVersionManager(str(rules_config_dir))
    rules_dict, current_version = version_manager.load_rules()
    versioned_rules = rules_dict.get('rules', [])
    print(f"  Version type: {type(current_version).__name__}")
    print(f"  Rules loaded: {len(versioned_rules)}")
    
    # Print first few rule IDs
    print("  Rule IDs (first 5):")
    for rule in versioned_rules[:5]:
        print(f"    - {rule.get('id')}")
    
    print("\nSTEP 2: Compare with custom_rules.json (old source)")
    custom_rules_path = rules_config_dir / "custom_rules.json"
    with open(custom_rules_path, 'r', encoding='utf-8') as f:
        custom_data = json.load(f)
        custom_rules = custom_data.get('rules', [])
    
    print(f"  Custom rules loaded: {len(custom_rules)}")
    if custom_rules:
        print("  Rule IDs (first 5):")
        for rule in custom_rules[:5]:
            print(f"    - {rule.get('id')}")
    
    print("\nSTEP 3: Compare with enhanced-regulation-rules.json (correct source)")
    enhanced_rules_path = rules_config_dir / "enhanced-regulation-rules.json"
    with open(enhanced_rules_path, 'r', encoding='utf-8') as f:
        enhanced_data = json.load(f)
        enhanced_rules = enhanced_data.get('rules', [])
    
    print(f"  Enhanced rules loaded: {len(enhanced_rules)}")
    print("  Rule IDs (first 5):")
    for rule in enhanced_rules[:5]:
        print(f"    - {rule.get('id')}")
    
    # Verify counts match
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    versioned_ids = {r.get('id') for r in versioned_rules}
    enhanced_ids = {r.get('id') for r in enhanced_rules}
    custom_ids = {r.get('id') for r in custom_rules}
    
    print(f"\nVersioned rules count: {len(versioned_rules)}")
    print(f"Enhanced rules count: {len(enhanced_rules)}")
    print(f"Custom rules count: {len(custom_rules)}")
    
    # Check if versioned matches enhanced
    if versioned_ids == enhanced_ids:
        print("\n✓ SUCCESS: Versioned rules MATCH enhanced rules")
        print("  → The endpoint now loads from the correct source!")
    else:
        print("\n✗ FAILURE: Versioned rules DO NOT match enhanced rules")
        print(f"  In versioned but not enhanced: {versioned_ids - enhanced_ids}")
        print(f"  In enhanced but not versioned: {enhanced_ids - versioned_ids}")
    
    # Check if versioned matches custom
    if versioned_ids == custom_ids:
        print("\n⚠ WARNING: Versioned rules MATCH custom rules")
        print("  → This is the old behavior - may indicate issue")
    else:
        print("\n✓ GOOD: Versioned rules DO NOT match custom rules")
        print("  → Using different sources as intended")
    
    print("\n" + "=" * 70)
    if versioned_ids == enhanced_ids and versioned_ids != custom_ids:
        print("RESULT: ✓ CATALOGUE SOURCE FIXED - Endpoint uses enhanced-regulation-rules.json")
    else:
        print("RESULT: ✗ ISSUE - Catalogue source may not be correct")
    print("=" * 70)

if __name__ == "__main__":
    test_catalogue_source()

