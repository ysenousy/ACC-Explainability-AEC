#!/usr/bin/env python3
"""
Clean orphaned rule mappings from unified_rules_mapping.json
Removes mappings for rules that don't exist in enhanced-regulation-rules.json
"""

import json
from pathlib import Path

def clean_mappings():
    """Remove orphaned mappings."""
    base_path = Path(__file__).parent.parent
    
    # Load the rules file to get valid rule IDs
    rules_path = base_path / "rules_config" / "enhanced-regulation-rules.json"
    with open(rules_path, 'r', encoding='utf-8') as f:
        rules_data = json.load(f)
    
    valid_rule_ids = {rule['id'] for rule in rules_data.get('rules', [])}
    print(f"✓ Valid rule IDs in catalogue: {len(valid_rule_ids)}")
    print(f"  {sorted(valid_rule_ids)}\n")
    
    # Load the mappings file
    mappings_path = base_path / "rules_config" / "unified_rules_mapping.json"
    with open(mappings_path, 'r', encoding='utf-8') as f:
        mappings_data = json.load(f)
    
    # Count original mappings
    original_mappings = mappings_data.get('rule_mappings', [])
    original_count = len(original_mappings)
    print(f"✓ Original mappings: {original_count}")
    
    # Get rule IDs from mappings
    mapped_rule_ids = {m.get('rule_reference', {}).get('rule_id') for m in original_mappings}
    print(f"  {sorted(mapped_rule_ids)}\n")
    
    # Find orphaned mappings
    orphaned = mapped_rule_ids - valid_rule_ids
    print(f"✗ Orphaned mappings (not in catalogue): {len(orphaned)}")
    for rule_id in sorted(orphaned):
        print(f"  - {rule_id}")
    
    # Filter to keep only valid mappings
    mappings_data['rule_mappings'] = [
        m for m in original_mappings
        if m.get('rule_reference', {}).get('rule_id') in valid_rule_ids
    ]
    
    new_count = len(mappings_data['rule_mappings'])
    print(f"\n✓ New mappings: {new_count}")
    print(f"  Removed: {original_count - new_count}")
    
    # Save the cleaned file
    with open(mappings_path, 'w', encoding='utf-8') as f:
        json.dump(mappings_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved cleaned unified_rules_mapping.json")
    
    # Show remaining rule IDs
    remaining_ids = {m.get('rule_reference', {}).get('rule_id') for m in mappings_data.get('rule_mappings', [])}
    print(f"\n✓ Remaining mapped rules: {sorted(remaining_ids)}")
    
    return new_count == original_count - len(orphaned)

if __name__ == "__main__":
    success = clean_mappings()
    exit(0 if success else 1)
