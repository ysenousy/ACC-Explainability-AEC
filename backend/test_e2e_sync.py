#!/usr/bin/env python
"""
End-to-end test: Verify that catalogue and mappings stay in sync
when using the corrected data source.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_version_manager import RulesVersionManager
from backend.rules_mapping_sync import RulesMappingSynchronizer

def test_end_to_end():
    """Test the complete flow: load catalogue, sync mappings"""
    
    print("=" * 80)
    print("END-TO-END TEST: Catalogue Source & Sync Integration")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    rules_config_dir = project_root / "rules_config"
    
    # Step 1: Load catalogue using new endpoint logic
    print("\nSTEP 1: Load catalogue (as /api/rules/catalogue endpoint does)")
    version_manager = RulesVersionManager(str(rules_config_dir))
    rules_dict, version_info = version_manager.load_rules()
    catalogue_rules = rules_dict.get('rules', [])
    print(f"  ✓ Loaded {len(catalogue_rules)} rules from versioned system")
    
    catalogue_ids = {r.get('id') for r in catalogue_rules}
    print(f"  Rule IDs: {sorted(list(catalogue_ids))[:3]}...")
    
    # Step 2: Verify it matches enhanced-regulation-rules.json
    print("\nSTEP 2: Verify catalogue matches enhanced-regulation-rules.json")
    enhanced_path = rules_config_dir / "enhanced-regulation-rules.json"
    with open(enhanced_path) as f:
        enhanced_data = json.load(f)
        enhanced_rules = enhanced_data.get('rules', [])
    
    enhanced_ids = {r.get('id') for r in enhanced_rules}
    
    if catalogue_ids == enhanced_ids:
        print(f"  ✓ Catalogue matches enhanced source ({len(catalogue_ids)} rules)")
    else:
        print(f"  ✗ MISMATCH: {len(catalogue_ids)} vs {len(enhanced_ids)} rules")
        return False
    
    # Step 3: Load mappings and sync
    print("\nSTEP 3: Load mappings and verify sync")
    synchronizer = RulesMappingSynchronizer(str(rules_config_dir))
    sync_status = synchronizer.get_sync_status()
    
    mapped_count = sync_status.get('mapped_rules', 0)
    orphaned_count = sync_status.get('orphaned', 0)
    missing_count = sync_status.get('missing', 0)
    
    print(f"  Catalogue rules: {sync_status.get('catalogue_rules')}")
    print(f"  Mapped rules: {mapped_count}")
    print(f"  Orphaned mappings: {orphaned_count}")
    print(f"  Missing mappings: {missing_count}")
    print(f"  Status: {sync_status.get('status')}")
    
    # Step 4: Verify counts match
    print("\nSTEP 4: Verify catalogue and mappings are in sync")
    
    if mapped_count == len(catalogue_ids) and orphaned_count == 0:
        print(f"  ✓ PERFECT MATCH: {mapped_count} rules = {len(catalogue_ids)} catalogue")
        print(f"  ✓ No orphaned mappings")
        print(f"  ✓ System is in sync")
        return True
    else:
        print(f"  ✗ MISMATCH:")
        print(f"    - Catalogue: {len(catalogue_ids)} rules")
        print(f"    - Mappings: {mapped_count} valid")
        print(f"    - Orphaned: {orphaned_count}")
        return False

if __name__ == "__main__":
    success = test_end_to_end()
    print("\n" + "=" * 80)
    if success:
        print("✓✓✓ END-TO-END TEST PASSED ✓✓✓")
        print("Catalogue source fixed and sync working correctly!")
    else:
        print("✗✗✗ END-TO-END TEST FAILED ✗✗✗")
    print("=" * 80)
    sys.exit(0 if success else 1)
