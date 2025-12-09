#!/usr/bin/env python
"""Test what the API endpoints are actually returning"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_version_manager import RulesVersionManager

def test_endpoint_responses():
    """Simulate what the API endpoints return"""
    
    print("=" * 80)
    print("API ENDPOINT RESPONSE TEST")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    rules_config_dir = project_root / "rules_config"
    
    # Simulate GET /api/rules/catalogue
    print("\nSIMULATE: GET /api/rules/catalogue")
    version_manager = RulesVersionManager(str(rules_config_dir))
    rules_dict, _ = version_manager.load_rules()
    rules = rules_dict.get('rules', [])
    
    print(f"  Returns {len(rules)} rules")
    print(f"  Rule IDs: {[r.get('id') for r in rules[:3]]}...")
    
    # Simulate GET /api/rules/custom
    print("\nSIMULATE: GET /api/rules/custom")
    rules_dict, _ = version_manager.load_rules()
    rules = rules_dict.get('rules', [])
    
    print(f"  Returns {len(rules)} rules")
    print(f"  Rule IDs: {[r.get('id') for r in rules[:3]]}...")
    
    # Check unified_rules_mapping.json directly
    print("\nCHECK: unified_rules_mapping.json in current version")
    current_version_id = version_manager.get_current_version_id()
    v_dir = rules_config_dir / "versions" / f"v{current_version_id}"
    mappings_file = v_dir / "unified_rules_mapping.json"
    
    with open(mappings_file) as f:
        mappings_data = json.load(f)
        mappings_list = mappings_data.get('rule_mappings', [])
    
    print(f"  Has {len(mappings_list)} rule mappings")
    
    # Check if they match
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    catalogue_ids = {r.get('id') for r in rules}
    mapped_rule_ids = {m.get('rule_reference', {}).get('rule_id') for m in mappings_list}
    
    print(f"\nCatalogue rules: {len(catalogue_ids)}")
    print(f"Mapped rules: {len(mapped_rule_ids)}")
    
    if catalogue_ids == mapped_rule_ids:
        print("✓ They match perfectly!")
    else:
        print("✗ They don't match!")
        print(f"  In catalogue but not mapped: {catalogue_ids - mapped_rule_ids}")
        print(f"  In mappings but not catalogue: {mapped_rule_ids - catalogue_ids}")

if __name__ == "__main__":
    test_endpoint_responses()
