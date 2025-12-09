#!/usr/bin/env python
"""Sync parent directory files with current version"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_version_manager import RulesVersionManager

def sync_parent_directory():
    """Update parent directory files to match current version"""
    
    print("=" * 80)
    print("SYNCING PARENT DIRECTORY WITH CURRENT VERSION")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    rules_config_dir = project_root / "rules_config"
    
    version_manager = RulesVersionManager(str(rules_config_dir))
    current_version_id = version_manager.get_current_version_id()
    
    print(f"\nCurrent version: v{current_version_id}")
    
    # Load current version
    rules_dict, mappings_dict = version_manager.load_rules()
    current_rules_count = len(rules_dict.get('rules', []))
    current_mappings_count = len(mappings_dict.get('rule_mappings', []))
    
    print(f"Loading v{current_version_id}...")
    print(f"  Rules: {current_rules_count}")
    print(f"  Mappings: {current_mappings_count}")
    
    # Update parent directory files
    parent_rules_path = rules_config_dir / "enhanced-regulation-rules.json"
    parent_mappings_path = rules_config_dir / "unified_rules_mapping.json"
    
    print(f"\nUpdating parent directory files...")
    
    with open(parent_rules_path, 'w') as f:
        json.dump(rules_dict, f, indent=2)
    print(f"  ✓ Updated {parent_rules_path.name}")
    
    with open(parent_mappings_path, 'w') as f:
        json.dump(mappings_dict, f, indent=2)
    print(f"  ✓ Updated {parent_mappings_path.name}")
    
    # Verify
    print(f"\nVerifying sync...")
    with open(parent_rules_path) as f:
        parent_data = json.load(f)
        parent_rules_count = len(parent_data.get('rules', []))
    
    with open(parent_mappings_path) as f:
        parent_data = json.load(f)
        parent_mappings_count = len(parent_data.get('rule_mappings', []))
    
    print(f"  Parent rules: {parent_rules_count}")
    print(f"  Parent mappings: {parent_mappings_count}")
    
    if parent_rules_count == current_rules_count and parent_mappings_count == current_mappings_count:
        print(f"\n✓ SUCCESS: Parent directory synced with v{current_version_id}")
        return True
    else:
        print(f"\n✗ FAILED: Parent directory sync failed")
        return False

if __name__ == "__main__":
    sync_parent_directory()
