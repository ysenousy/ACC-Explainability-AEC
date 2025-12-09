#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from backend.rules_mapping_sync import RulesMappingSynchronizer

sync = RulesMappingSynchronizer(str(Path('rules_config')))
result = sync.sync_mappings(verbose=True)

print(f'\nOrphaned removed: {result["orphaned_removed"]}')
if result["sync_details"]["orphaned_removed"]:
    print(f'Removed: {result["sync_details"]["orphaned_removed"]}')
