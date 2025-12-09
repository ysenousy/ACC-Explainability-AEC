#!/usr/bin/env python
"""Diagnostic test to check what's happening with catalogue vs mappings sync"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_version_manager import RulesVersionManager
from backend.rules_mapping_sync import RulesMappingSynchronizer

def diagnose_sync_issue():
    """Diagnose the sync mismatch"""
    
    print("=" * 80)
    print("SYNC DIAGNOSTIC TEST")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    rules_config_dir = project_root / "rules_config"
    
    print("\nSTEP 1: Check version manager current version")
    version_manager = RulesVersionManager(str(rules_config_dir))
    current_version_id = version_manager.get_current_version_id()
    print(f"  Current version ID: {current_version_id}")
    
    # Check what version is being loaded
    rules_dict, mappings_dict = version_manager.load_rules()
    catalogue_rules = rules_dict.get('rules', [])
    catalogue_count = len(catalogue_rules)
    print(f"  Loaded catalogue has: {catalogue_count} rules")
    print(f"  Rules: {[r.get('id') for r in catalogue_rules[:3]]}...")
    
    print("\nSTEP 2: Check mappings")
    synchronizer = RulesMappingSynchronizer(str(rules_config_dir))
    sync_status = synchronizer.get_sync_status()
    
    mapped_count = sync_status.get('mapped_rules', 0)
    orphaned_count = sync_status.get('orphaned', 0)
    missing_count = sync_status.get('missing', 0)
    
    print(f"  Catalogue rules: {sync_status.get('catalogue_rules')}")
    print(f"  Mapped rules: {mapped_count}")
    print(f"  Orphaned: {orphaned_count}")
    print(f"  Missing: {missing_count}")
    print(f"  Status: {sync_status.get('status')}")
    
    if orphaned_count > 0:
        print(f"  Orphaned mappings: {sync_status.get('details', {}).get('orphaned', [])}")
    if missing_count > 0:
        print(f"  Missing mappings: {sync_status.get('details', {}).get('missing', [])}")
    
    print("\nSTEP 3: Check version files directly")
    v_dir = rules_config_dir / "versions" / f"v{current_version_id}"
    print(f"  Version directory: {v_dir}")
    print(f"  Exists: {v_dir.exists()}")
    
    if v_dir.exists():
        rules_file = v_dir / "enhanced-regulation-rules.json"
        mappings_file = v_dir / "unified_rules_mapping.json"
        
        with open(rules_file) as f:
            v_rules = json.load(f)
            v_rules_list = v_rules.get('rules', [])
        
        with open(mappings_file) as f:
            v_mappings = json.load(f)
            v_mappings_list = v_mappings.get('rule_mappings', [])
        
        print(f"  Version {current_version_id} has {len(v_rules_list)} rules")
        print(f"  Version {current_version_id} has {len(v_mappings_list)} mappings")
    
    print("\nSTEP 4: Check if sync is needed")
    if catalogue_count == mapped_count and orphaned_count == 0:
        print("  ✓ System is in sync!")
        return True
    else:
        print(f"  ✗ MISMATCH DETECTED:")
        print(f"    Catalogue: {catalogue_count}")
        print(f"    Mappings: {mapped_count}")
        print(f"    Orphaned: {orphaned_count}")
        print(f"    Missing: {missing_count}")
        return False

if __name__ == "__main__":
    is_synced = diagnose_sync_issue()
    print("\n" + "=" * 80)
    if is_synced:
        print("STATUS: System is in sync ✓")
    else:
        print("STATUS: System needs sync ✗")
    print("=" * 80)
