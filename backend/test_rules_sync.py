"""
Test Rules Catalogue Sync System
"""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rules_mapping_sync import RulesMappingSynchronizer

def test_sync():
    """Test the sync system."""
    rules_config = Path(__file__).parent.parent / "rules_config"
    
    print("\n" + "="*60)
    print("RULES CATALOGUE SYNC TEST")
    print("="*60 + "\n")
    
    sync = RulesMappingSynchronizer(str(rules_config))
    
    # Get initial status
    print("1. Initial Status:")
    status = sync.get_sync_status()
    print(f"   Catalogue rules: {status['catalogue_rules']}")
    print(f"   Mapped rules: {status['mapped_rules']}")
    print(f"   Orphaned: {status['orphaned']}")
    print(f"   Missing: {status['missing']}")
    print(f"   Status: {status['status']}")
    
    # Show details
    if status['orphaned'] > 0:
        print(f"\n   Orphaned mappings: {status['details']['orphaned']}")
    if status['missing'] > 0:
        print(f"   Missing mappings: {status['details']['missing']}")
    
    # Perform sync if needed
    if status['status'] != 'in_sync':
        print("\n2. Performing Sync...")
        result = sync.sync_mappings(verbose=False)
        print(f"   Orphaned removed: {result['orphaned_removed']}")
        if result['sync_details']['orphaned_removed']:
            print(f"   Removed: {result['sync_details']['orphaned_removed']}")
        
        # Check again
        print("\n3. Status After Sync:")
        status = sync.get_sync_status()
        print(f"   Catalogue rules: {status['catalogue_rules']}")
        print(f"   Mapped rules: {status['mapped_rules']}")
        print(f"   Orphaned: {status['orphaned']}")
        print(f"   Missing: {status['missing']}")
        print(f"   Status: {status['status']}")
    else:
        print("\n2. Already in sync ✓")
    
    # Final validation
    print("\n4. Validation:")
    is_valid = sync.validate_sync()
    print(f"   Valid: {is_valid}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")
    
    return is_valid

if __name__ == "__main__":
    success = test_sync()
    exit(0 if success else 1)
