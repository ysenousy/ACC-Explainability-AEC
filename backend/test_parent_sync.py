#!/usr/bin/env python
"""Test that parent directory files are kept in sync"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_version_manager import RulesVersionManager

def test_parent_sync():
    """Test that parent files are updated when versions are created"""
    
    print("=" * 80)
    print("PARENT DIRECTORY SYNC TEST")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    rules_config_dir = project_root / "rules_config"
    
    # Get current state
    version_manager = RulesVersionManager(str(rules_config_dir))
    rules_dict, mappings_dict = version_manager.load_rules()
    current_rules = rules_dict.get('rules', [])
    current_count = len(current_rules)
    
    print(f"\nCurrent version: v{version_manager.get_current_version_id()}")
    print(f"Current catalogue has: {current_count} rules")
    
    # Check parent directory files
    parent_rules_path = rules_config_dir / "enhanced-regulation-rules.json"
    parent_mappings_path = rules_config_dir / "unified_rules_mapping.json"
    
    with open(parent_rules_path) as f:
        parent_data = json.load(f)
        parent_rules = parent_data.get('rules', [])
    
    parent_count = len(parent_rules)
    print(f"Parent directory has: {parent_count} rules")
    
    # Check if they match
    print("\nVERIFICATION:")
    if current_count == parent_count:
        print(f"  ✓ Parent directory is in sync ({current_count} rules)")
        
        current_ids = {r.get('id') for r in current_rules}
        parent_ids = {r.get('id') for r in parent_rules}
        
        if current_ids == parent_ids:
            print(f"  ✓ Rule IDs match perfectly")
            return True
        else:
            print(f"  ✗ Rule IDs don't match:")
            print(f"    In current but not parent: {current_ids - parent_ids}")
            print(f"    In parent but not current: {parent_ids - current_ids}")
            return False
    else:
        print(f"  ✗ MISMATCH: Current {current_count} vs Parent {parent_count}")
        return False

if __name__ == "__main__":
    is_synced = test_parent_sync()
    print("\n" + "=" * 80)
    if is_synced:
        print("STATUS: Parent directory is in sync ✓")
    else:
        print("STATUS: Parent directory is OUT OF SYNC ✗")
    print("=" * 80)
