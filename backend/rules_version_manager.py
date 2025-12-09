"""
Rules Version Manager

Manages versioned copies of rule configurations to preserve original files
while allowing runtime modifications.

Each user modification creates a new version without affecting the original files.
"""

import json
import shutil
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path


class RulesVersionManager:
    """Manages versioned rule configurations."""
    
    def __init__(self, rules_config_dir: str):
        """
        Initialize version manager.
        
        Args:
            rules_config_dir: Path to rules_config directory
        """
        self.rules_config_dir = Path(rules_config_dir)
        self.versions_dir = self.rules_config_dir / "versions"
        self.manifest_path = self.versions_dir / "version_manifest.json"
        
        # Ensure versions directory exists
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize manifest
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load version manifest from disk."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        else:
            # Initialize empty manifest
            return {
                "current_version": 0,
                "total_versions": 0,
                "versions": [],
                "version_history": []
            }
    
    def _save_manifest(self):
        """Save version manifest to disk."""
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def get_current_version_id(self) -> int:
        """Get current active version ID (reloads manifest from disk)."""
        # Reload manifest to get latest version
        self.manifest = self._load_manifest()
        return self.manifest.get("current_version", 0)
    
    def get_version_info(self, version_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata about a specific version."""
        for version in self.manifest.get("versions", []):
            if version["version_id"] == version_id:
                return version
        return None
    
    def list_all_versions(self) -> List[Dict[str, Any]]:
        """List all available versions."""
        return self.manifest.get("versions", [])
    
    def load_rules(self, version_id: Optional[int] = None) -> tuple:
        """
        Load rules and mappings from specified version.
        
        Args:
            version_id: Version to load. If None, loads current version.
                       If -1, loads original (v0)
        
        Returns:
            Tuple of (rules_dict, mappings_dict)
        """
        if version_id is None:
            version_id = self.get_current_version_id()
        
        if version_id == -1:
            version_id = 0  # Load original
        
        version_dir = self.versions_dir / f"v{version_id}"
        
        if not version_dir.exists():
            raise ValueError(f"Version {version_id} not found")
        
        rules_path = version_dir / "enhanced-regulation-rules.json"
        mappings_path = version_dir / "unified_rules_mapping.json"
        
        with open(rules_path, 'r') as f:
            rules = json.load(f)
        
        with open(mappings_path, 'r') as f:
            mappings = json.load(f)
        
        return rules, mappings
    
    def create_new_version(
        self,
        rules_dict: Dict[str, Any],
        mappings_dict: Dict[str, Any],
        description: str,
        modifications: Optional[List[Dict[str, Any]]] = None,
        created_by: str = "user"
    ) -> int:
        """
        Create a new version with user modifications.
        
        Args:
            rules_dict: Updated rules configuration
            mappings_dict: Updated rules mappings
            description: Description of changes
            modifications: List of modification records
            created_by: Who created this version (user/system)
        
        Returns:
            New version ID
        """
        # Calculate new version ID
        new_version_id = self.manifest.get("total_versions", 0)
        version_dir = self.versions_dir / f"v{new_version_id}"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Write rule files to version directory
        rules_path = version_dir / "enhanced-regulation-rules.json"
        mappings_path = version_dir / "unified_rules_mapping.json"
        
        with open(rules_path, 'w') as f:
            json.dump(rules_dict, f, indent=2)
        
        with open(mappings_path, 'w') as f:
            json.dump(mappings_dict, f, indent=2)
        
        # Also update parent directory files to keep them in sync with current version
        parent_rules_path = self.rules_config_dir / "enhanced-regulation-rules.json"
        parent_mappings_path = self.rules_config_dir / "unified_rules_mapping.json"
        
        with open(parent_rules_path, 'w') as f:
            json.dump(rules_dict, f, indent=2)
        
        with open(parent_mappings_path, 'w') as f:
            json.dump(mappings_dict, f, indent=2)
        
        # Extract rule count and IDs
        num_rules = len(rules_dict.get("rules", []))
        rule_ids = [rule["id"] for rule in rules_dict.get("rules", [])]
        
        # Create version metadata
        version_metadata = {
            "version_id": new_version_id,
            "label": f"User Modifications #{new_version_id}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": created_by,
            "description": description,
            "num_rules": num_rules,
            "rule_ids": rule_ids,
            "modifications": modifications or []
        }
        
        # Update manifest
        self.manifest["versions"].append(version_metadata)
        self.manifest["current_version"] = new_version_id
        self.manifest["total_versions"] = new_version_id + 1
        
        # Record in history
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "create_version",
            "version_id": new_version_id,
            "description": description,
            "created_by": created_by
        }
        self.manifest["version_history"].append(history_entry)
        
        self._save_manifest()
        
        return new_version_id
    
    def rollback_to(self, version_id: int) -> tuple:
        """
        Rollback to a previous version.
        
        Args:
            version_id: Version to rollback to
        
        Returns:
            Tuple of (rules_dict, mappings_dict) from rolled-back version
        """
        if version_id >= self.manifest.get("total_versions", 0):
            raise ValueError(f"Version {version_id} does not exist")
        
        # Load the previous version
        rules, mappings = self.load_rules(version_id)
        
        # Update current version
        self.manifest["current_version"] = version_id
        
        # Record rollback in history
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "rollback",
            "to_version_id": version_id,
            "from_version_id": self.manifest["current_version"]
        }
        self.manifest["version_history"].append(history_entry)
        
        self._save_manifest()
        
        return rules, mappings
    
    def get_version_diff(self, version_id_1: int, version_id_2: int) -> Dict[str, Any]:
        """
        Compare two versions and return differences.
        
        Args:
            version_id_1: First version
            version_id_2: Second version
        
        Returns:
            Dictionary containing differences
        """
        rules_1, mappings_1 = self.load_rules(version_id_1)
        rules_2, mappings_2 = self.load_rules(version_id_2)
        
        diff = {
            "version_1": version_id_1,
            "version_2": version_id_2,
            "rules_added": [],
            "rules_removed": [],
            "rules_modified": [],
            "mappings_changed": False
        }
        
        # Compare rules
        rules_1_ids = {r["id"] for r in rules_1.get("rules", [])}
        rules_2_ids = {r["id"] for r in rules_2.get("rules", [])}
        
        diff["rules_added"] = list(rules_2_ids - rules_1_ids)
        diff["rules_removed"] = list(rules_1_ids - rules_2_ids)
        
        # Check for rule modifications
        for rule_1 in rules_1.get("rules", []):
            rule_id = rule_1["id"]
            for rule_2 in rules_2.get("rules", []):
                if rule_2["id"] == rule_id and rule_1 != rule_2:
                    diff["rules_modified"].append(rule_id)
        
        # Check if mappings changed
        diff["mappings_changed"] = (mappings_1 != mappings_2)
        
        return diff
    
    def export_version(self, version_id: int, output_dir: str):
        """
        Export a version to external directory (for backup/sharing).
        
        Args:
            version_id: Version to export
            output_dir: Directory to export to
        """
        version_dir = self.versions_dir / f"v{version_id}"
        output_path = Path(output_dir) / f"rules_v{version_id}"
        
        shutil.copytree(version_dir, output_path, dirs_exist_ok=True)
        
        # Also copy metadata
        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.get_version_info(version_id), f, indent=2)


# Convenience functions for common operations

def get_version_manager(rules_config_dir: str = None) -> RulesVersionManager:
    """
    Get or create a version manager instance.
    
    Args:
        rules_config_dir: Path to rules_config directory.
                         If None, uses current working directory + rules_config
    
    Returns:
        RulesVersionManager instance
    """
    if rules_config_dir is None:
        rules_config_dir = Path.cwd() / "rules_config"
    
    return RulesVersionManager(rules_config_dir)
