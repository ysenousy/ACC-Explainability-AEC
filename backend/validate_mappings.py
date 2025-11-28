"""
Validate Rule Config mappings against the catalogue.
Identifies orphaned mappings (mapping references rule that doesn't exist in catalogue).
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

def load_json_file(filepath: str) -> dict:
    """Load JSON file safely."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Error loading {filepath}: {e}")

def get_catalogue_rule_ids(catalogue_path: str) -> set:
    """Extract all rule IDs from the catalogue."""
    catalogue = load_json_file(catalogue_path)
    return {rule['id'] for rule in catalogue.get('rules', [])}

def get_config_rule_references(config_path: str) -> Dict[str, str]:
    """Extract all rule references from Rule Config mappings.
    Returns: {mapping_id: rule_id}
    """
    config = load_json_file(config_path)
    references = {}
    for mapping in config.get('rule_mappings', []):
        mapping_id = mapping.get('mapping_id')
        rule_id = mapping.get('rule_reference', {}).get('rule_id')
        if mapping_id and rule_id:
            references[mapping_id] = rule_id
    return references

def validate_mappings(catalogue_path: str, config_path: str) -> Tuple[List[str], int, int]:
    """
    Validate Rule Config mappings against catalogue.
    Ignores custom mappings (where rule_id is not in any standard format).
    Returns: (orphaned_mapping_ids, total_mappings, valid_mappings)
    """
    catalogue_ids = get_catalogue_rule_ids(catalogue_path)
    config_references = get_config_rule_references(config_path)
    
    orphaned = []
    for mapping_id, rule_id in config_references.items():
        # Skip custom rules (e.g., OCCUPANCY_MAX_PER_STOREY, user-defined rules)
        # Only flag as orphaned if it matches a standard format but isn't in catalogue
        is_standard_format = any([
            rule_id.startswith('ADA_'),
            rule_id.startswith('IBC_'),
            rule_id.startswith('IRC_'),
            rule_id.startswith('UK_'),
            rule_id.startswith('CA_'),
            rule_id.endswith('_WARNING'),
        ])
        
        if is_standard_format and rule_id not in catalogue_ids:
            orphaned.append(mapping_id)
    
    valid = len(config_references) - len(orphaned)
    return orphaned, len(config_references), valid

def cleanup_orphaned_mappings(config_path: str, orphaned_mapping_ids: List[str]) -> int:
    """
    Remove orphaned mappings from Rule Config.
    Returns: number of mappings removed
    """
    config = load_json_file(config_path)
    
    original_count = len(config.get('rule_mappings', []))
    config['rule_mappings'] = [
        m for m in config.get('rule_mappings', [])
        if m.get('mapping_id') not in orphaned_mapping_ids
    ]
    new_count = len(config.get('rule_mappings', []))
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return original_count - new_count

def main():
    """Main validation and cleanup routine."""
    base_path = Path(__file__).parent.parent / 'rules_config'
    catalogue_path = str(base_path / 'enhanced-regulation-rules.json')
    config_path = str(base_path / 'unified_rules_mapping.json')
    
    print("=" * 70)
    print("RULE CONFIG VALIDATION")
    print("=" * 70)
    
    # Validate
    orphaned, total, valid = validate_mappings(catalogue_path, config_path)
    
    print(f"\nCatalogue Rules: {len(get_catalogue_rule_ids(catalogue_path))}")
    print(f"Rule Config Mappings: {total}")
    print(f"Valid Mappings: {valid}")
    print(f"Orphaned Mappings: {len(orphaned)}")
    
    if orphaned:
        print(f"\n⚠️  FOUND {len(orphaned)} ORPHANED MAPPING(S):")
        for mapping_id in orphaned:
            print(f"   - {mapping_id}")
        
        # Auto-cleanup
        removed = cleanup_orphaned_mappings(config_path, orphaned)
        print(f"\n✅ Automatically removed {removed} orphaned mapping(s)")
        print(f"   Rule Config now has {total - removed} mappings")
    else:
        print("\n✅ All mappings are valid (no orphaned references)")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    main()
