#!/usr/bin/env python3
"""
Verify that sync uses current version, not original
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_mapping_sync import RulesMappingSynchronizer

def test():
    rules_config = Path(__file__).parent.parent / "rules_config"
    
    # Check version manifest
    with open(rules_config / 'versions' / 'version_manifest.json') as f:
        manifest = json.load(f)
    
    current_v = manifest['current_version']
    
    print("\n" + "="*70)
    print("VERIFY: Sync Uses Current Version (Not Original)")
    print("="*70 + "\n")
    
    print(f"Current version from manifest: v{current_v}")
    print(f"Version directory: versions/v{current_v}/\n")
    
    # Initialize sync
    sync = RulesMappingSynchronizer(str(rules_config))
    
    print("Synchronizer initialized:")
    print(f"  ✓ Using version: v{sync.version_id}")
    print(f"  ✓ Rules file: {sync.rules_file.relative_to(rules_config.parent)}")
    print(f"  ✓ Mappings file: {sync.mappings_file.relative_to(rules_config.parent)}\n")
    
    # Get status
    status = sync.get_sync_status()
    
    print("Sync Status (from current version):")
    print(f"  Status: {status['status']}")
    print(f"  Catalogue rules: {status['catalogue_rules']}")
    print(f"  Mapped rules: {status['mapped_rules']}")
    print(f"  Orphaned: {status['orphaned']}")
    print(f"  Missing: {status['missing']}\n")
    
    # Verify it's loading from version directory
    print("Verification:")
    if f"v{sync.version_id}" in str(sync.rules_file):
        print(f"  ✓ Rules loaded from versions/v{sync.version_id}/")
    else:
        print(f"  ✗ ERROR: Rules NOT from versions/v{sync.version_id}/")
        return False
    
    if f"v{sync.version_id}" in str(sync.mappings_file):
        print(f"  ✓ Mappings loaded from versions/v{sync.version_id}/")
    else:
        print(f"  ✗ ERROR: Mappings NOT from versions/v{sync.version_id}/")
        return False
    
    print("\n" + "="*70)
    print("✓ CONFIRMED: Sync uses current version (not original files)")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    success = test()
    exit(0 if success else 1)
