"""
Rules Mapping Synchronizer

Automatically regenerates unified_rules_mapping.json based on current catalogue
Ensures mapped rules always match the catalogue rules

KEY POINT: This synchronizer loads rules from the CURRENT VERSION (latest user edits),
not from the original files. 

Flow:
  1. User edits catalogue → saved to versions/vN/
  2. Sync loads from versions/vN/ (current version)
  3. Compares rules in current version with mappings
  4. Updates mappings in versions/vN/ to match current rules
  5. Result: catalogue and mappings always in sync at current version
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RulesMappingSynchronizer:
    """Synchronizes rule mappings with the current catalogue."""
    
    def __init__(self, rules_config_dir: str, version_id: Optional[int] = None):
        """
        Initialize synchronizer.
        
        Args:
            rules_config_dir: Path to rules_config directory
            version_id: Which version to sync. If None, uses current version
        """
        self.rules_config_dir = Path(rules_config_dir)
        self.versions_dir = self.rules_config_dir / "versions"
        self.manifest_path = self.versions_dir / "version_manifest.json"
        self.version_id = version_id
        
        # Load manifest to determine current version
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Use specified version or current version
        if self.version_id is None:
            self.version_id = manifest.get('current_version', 0)
        
        # Set paths for the version
        self.version_dir = self.versions_dir / f"v{self.version_id}"
        self.rules_file = self.version_dir / "enhanced-regulation-rules.json"
        self.mappings_file = self.version_dir / "unified_rules_mapping.json"
    
    def load_catalogue(self) -> Dict[str, Any]:
        """Load current rules catalogue."""
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_mappings(self) -> Dict[str, Any]:
        """Load current mappings."""
        with open(self.mappings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_mappings(self, mappings: Dict[str, Any]):
        """Save mappings to both version directory and parent directory."""
        # Save to version directory
        with open(self.mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
        
        # Also save to parent directory for compatibility
        parent_mappings_file = self.rules_config_dir / "unified_rules_mapping.json"
        with open(parent_mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
    
    def sync_mappings(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Synchronize mappings with catalogue.
        
        Removes mappings for rules not in catalogue.
        Keeps mappings for all rules that are in catalogue.
        
        Args:
            verbose: Print sync details
        
        Returns:
            Dictionary with sync results
        """
        # Load current data
        catalogue = self.load_catalogue()
        mappings = self.load_mappings()
        
        # Get valid rule IDs from catalogue
        valid_rule_ids = {rule['id'] for rule in catalogue.get('rules', [])}
        
        # Get current mapped rule IDs
        rule_mappings = mappings.get('rule_mappings', [])
        mapped_rule_ids = {m.get('rule_reference', {}).get('rule_id') for m in rule_mappings}
        
        # Find differences
        orphaned = mapped_rule_ids - valid_rule_ids
        missing = valid_rule_ids - mapped_rule_ids
        valid = mapped_rule_ids & valid_rule_ids
        
        # Remove orphaned mappings
        original_count = len(rule_mappings)
        mappings['rule_mappings'] = [
            m for m in rule_mappings
            if m.get('rule_reference', {}).get('rule_id') in valid_rule_ids
        ]
        new_count = len(mappings['rule_mappings'])
        
        # Save updated mappings
        self.save_mappings(mappings)
        
        # Prepare result
        result = {
            "status": "synced",
            "catalogue_rules": len(valid_rule_ids),
            "mapped_rules": new_count,
            "valid_mappings": len(valid),
            "orphaned_removed": len(orphaned),
            "missing_mappings": len(missing),
            "sync_details": {
                "catalogue_rules": sorted(list(valid_rule_ids)),
                "mapped_rules": sorted(list(valid)),
                "orphaned_removed": sorted(list(orphaned)),
                "missing_mappings": sorted(list(missing))
            }
        }
        
        if verbose:
            logger.info(f"Mappings sync completed:")
            logger.info(f"  Catalogue rules: {len(valid_rule_ids)}")
            logger.info(f"  Mapped rules: {new_count}")
            logger.info(f"  Orphaned removed: {len(orphaned)}")
            logger.info(f"  Missing mappings: {len(missing)}")
            
            if orphaned:
                logger.warning(f"  Removed orphaned: {sorted(orphaned)}")
            if missing:
                logger.warning(f"  Missing mappings for: {sorted(missing)}")
        
        return result
    
    def validate_sync(self) -> bool:
        """
        Validate that mappings match catalogue.
        
        Returns:
            True if all catalogue rules have mappings
        """
        catalogue = self.load_catalogue()
        mappings = self.load_mappings()
        
        valid_rule_ids = {rule['id'] for rule in catalogue.get('rules', [])}
        mapped_rule_ids = {m.get('rule_reference', {}).get('rule_id') 
                          for m in mappings.get('rule_mappings', [])}
        
        # Check if there are orphaned mappings
        orphaned = mapped_rule_ids - valid_rule_ids
        if orphaned:
            logger.warning(f"Orphaned mappings found: {orphaned}")
            return False
        
        # Check for missing mappings
        missing = valid_rule_ids - mapped_rule_ids
        if missing:
            logger.warning(f"Missing mappings for: {missing}")
            return False
        
        logger.info(f"Validation OK: {len(valid_rule_ids)} rules, {len(mapped_rule_ids)} mappings")
        return True
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status without making changes."""
        catalogue = self.load_catalogue()
        mappings = self.load_mappings()
        
        valid_rule_ids = {rule['id'] for rule in catalogue.get('rules', [])}
        mapped_rule_ids = {m.get('rule_reference', {}).get('rule_id') 
                          for m in mappings.get('rule_mappings', [])}
        
        orphaned = mapped_rule_ids - valid_rule_ids
        missing = valid_rule_ids - mapped_rule_ids
        
        return {
            "status": "in_sync" if not orphaned and not missing else "out_of_sync",
            "catalogue_rules": len(valid_rule_ids),
            "mapped_rules": len(mapped_rule_ids),
            "orphaned": len(orphaned),
            "missing": len(missing),
            "details": {
                "catalogue_rules": sorted(list(valid_rule_ids)),
                "mapped_rules": sorted(list(mapped_rule_ids)),
                "orphaned": sorted(list(orphaned)),
                "missing": sorted(list(missing))
            }
        }
    
    def sync_mappings_with_rules(self, rules_dict: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        """
        Synchronize mappings with a custom rules dictionary (for in-memory editing).
        
        Args:
            rules_dict: Dictionary with 'rules' key containing rules list
            verbose: Print sync details
        
        Returns:
            Dictionary with sync results
        """
        try:
            # Get rules from the provided dictionary
            custom_rules = rules_dict.get('rules', [])
            valid_rule_ids = {rule['id'] for rule in custom_rules}
            
            # Load current mappings
            mappings = self.load_mappings()
            mapped_rule_ids = {m.get('rule_reference', {}).get('rule_id') 
                             for m in mappings.get('rule_mappings', [])}
            
            # Find differences
            orphaned = mapped_rule_ids - valid_rule_ids
            valid = mapped_rule_ids & valid_rule_ids
            
            # Remove orphaned mappings (mappings for deleted rules)
            original_count = len(mappings.get('rule_mappings', []))
            mappings['rule_mappings'] = [
                m for m in mappings.get('rule_mappings', [])
                if m.get('rule_reference', {}).get('rule_id') in valid_rule_ids
            ]
            new_count = len(mappings['rule_mappings'])
            
            # Save updated mappings
            self.save_mappings(mappings)
            
            if verbose:
                logger.info(f"[SYNC-WITH-RULES] Mappings updated: "
                           f"{original_count} → {new_count} mappings, "
                           f"removed {len(orphaned)} orphaned mappings")
            
            return {
                "status": "synced",
                "custom_rules": len(valid_rule_ids),
                "mapped_rules": new_count,
                "valid_mappings": len(valid),
                "orphaned_removed": len(orphaned)
            }
        except Exception as e:
            logger.error(f"[SYNC-WITH-RULES] Error syncing with custom rules: {e}")
            raise


def get_synchronizer(rules_config_dir: str = None) -> RulesMappingSynchronizer:
    """Get a synchronizer instance."""
    if rules_config_dir is None:
        rules_config_dir = Path.cwd() / "rules_config"
    return RulesMappingSynchronizer(rules_config_dir)
