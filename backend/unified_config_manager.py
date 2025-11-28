"""
Unified Rules Configuration Manager

Handles loading, validation, updating, and saving the unified_rules_mapping.json configuration.
Bridges between regulation rules, generated rules, and IFC attributes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "rules_config" / "unified_rules_mapping.json"


class UnifiedConfigManager:
    """Manages unified rules configuration with CRUD operations."""

    def __init__(self, config_path: Optional[str | Path] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Optional[Dict[str, Any]] = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return self._get_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logger.info(f"Loaded config from {self.config_path}")
            return self._config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def save_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Save configuration to file."""
        try:
            # Validate before saving
            is_valid, errors = self.validate_config(config)
            if not is_valid:
                return False, f"Validation failed: {'; '.join(errors)}"

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._config = config
            logger.info(f"Saved config to {self.config_path}")
            return True, "Configuration saved successfully"
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False, str(e)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration (load if not already loaded)."""
        if self._config is None:
            self.load_config()
        return self._config or self._get_default_config()

    def reload(self) -> Dict[str, Any]:
        """Force reload configuration from file, clearing cache."""
        self._config = None
        return self.load_config()

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration schema."""
        errors = []

        # Check required top-level keys
        required_keys = ["version", "metadata", "ifc_element_mappings", "rule_mappings"]
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required key: {key}")

        # Validate rule mappings
        if "rule_mappings" in config:
            for i, mapping in enumerate(config["rule_mappings"]):
                if "mapping_id" not in mapping:
                    errors.append(f"Rule mapping {i} missing 'mapping_id'")
                if "element_type" not in mapping:
                    errors.append(f"Rule mapping {i} missing 'element_type'")
                if "rule_reference" not in mapping:
                    errors.append(f"Rule mapping {i} missing 'rule_reference'")
                if "attribute_extraction" not in mapping:
                    errors.append(f"Rule mapping {i} missing 'attribute_extraction'")

        # Validate IFC element mappings
        if "ifc_element_mappings" in config:
            for elem_type, elem_config in config["ifc_element_mappings"].items():
                if "attributes" not in elem_config:
                    errors.append(f"Element type '{elem_type}' missing 'attributes'")
                if not isinstance(elem_config.get("attributes", []), list):
                    errors.append(f"Element type '{elem_type}' attributes must be a list")

        return len(errors) == 0, errors

    def get_ifc_element_mappings(self) -> Dict[str, Any]:
        """Get all IFC element type mappings."""
        config = self.get_config()
        return config.get("ifc_element_mappings", {})

    def get_element_attributes(self, element_type: str) -> List[Dict[str, Any]]:
        """Get attributes for a specific element type."""
        mappings = self.get_ifc_element_mappings()
        element = mappings.get(element_type, {})
        return element.get("attributes", [])

    def add_element_attribute(self, element_type: str, attribute: Dict[str, Any]) -> Tuple[bool, str]:
        """Add a new attribute to an element type."""
        config = self.get_config()
        mappings = config.get("ifc_element_mappings", {})

        if element_type not in mappings:
            return False, f"Element type '{element_type}' not found"

        if "attributes" not in mappings[element_type]:
            mappings[element_type]["attributes"] = []

        mappings[element_type]["attributes"].append(attribute)
        config["ifc_element_mappings"] = mappings
        config["metadata"]["last_updated"] = datetime.now().isoformat()

        return self.save_config(config)

    def update_element_attribute(
        self, element_type: str, attribute_name: str, updated_attribute: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update an existing attribute in an element type."""
        config = self.get_config()
        mappings = config.get("ifc_element_mappings", {})

        if element_type not in mappings:
            return False, f"Element type '{element_type}' not found"

        attributes = mappings[element_type].get("attributes", [])
        found = False
        for i, attr in enumerate(attributes):
            if attr.get("name") == attribute_name:
                attributes[i] = updated_attribute
                found = True
                break

        if not found:
            return False, f"Attribute '{attribute_name}' not found in element type '{element_type}'"

        mappings[element_type]["attributes"] = attributes
        config["ifc_element_mappings"] = mappings
        config["metadata"]["last_updated"] = datetime.now().isoformat()

        return self.save_config(config)

    def delete_element_attribute(self, element_type: str, attribute_name: str) -> Tuple[bool, str]:
        """Delete an attribute from an element type."""
        config = self.get_config()
        mappings = config.get("ifc_element_mappings", {})

        if element_type not in mappings:
            return False, f"Element type '{element_type}' not found"

        attributes = mappings[element_type].get("attributes", [])
        original_count = len(attributes)
        attributes = [a for a in attributes if a.get("name") != attribute_name]

        if len(attributes) == original_count:
            return False, f"Attribute '{attribute_name}' not found"

        mappings[element_type]["attributes"] = attributes
        config["ifc_element_mappings"] = mappings
        config["metadata"]["last_updated"] = datetime.now().isoformat()

        return self.save_config(config)

    def get_rule_mappings(self) -> List[Dict[str, Any]]:
        """Get all rule mappings."""
        config = self.get_config()
        return config.get("rule_mappings", [])

    def get_rule_mapping(self, mapping_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific rule mapping by ID."""
        for mapping in self.get_rule_mappings():
            if mapping.get("mapping_id") == mapping_id:
                return mapping
        return None

    def add_rule_mapping(self, mapping: Dict[str, Any]) -> Tuple[bool, str]:
        """Add a new rule mapping."""
        config = self.get_config()
        mappings = config.get("rule_mappings", [])

        # Check for duplicate
        if any(m.get("mapping_id") == mapping.get("mapping_id") for m in mappings):
            return False, f"Mapping with ID '{mapping.get('mapping_id')}' already exists"

        mappings.append(mapping)
        config["rule_mappings"] = mappings
        config["metadata"]["last_updated"] = datetime.now().isoformat()

        return self.save_config(config)

    def update_rule_mapping(self, mapping_id: str, updated_mapping: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing rule mapping."""
        config = self.get_config()
        mappings = config.get("rule_mappings", [])

        found = False
        for i, m in enumerate(mappings):
            if m.get("mapping_id") == mapping_id:
                mappings[i] = updated_mapping
                found = True
                break

        if not found:
            return False, f"Mapping with ID '{mapping_id}' not found"

        config["rule_mappings"] = mappings
        config["metadata"]["last_updated"] = datetime.now().isoformat()

        return self.save_config(config)

    def delete_rule_mapping(self, mapping_id: str) -> Tuple[bool, str]:
        """Delete a rule mapping."""
        config = self.get_config()
        mappings = config.get("rule_mappings", [])
        original_count = len(mappings)
        mappings = [m for m in mappings if m.get("mapping_id") != mapping_id]

        if len(mappings) == original_count:
            return False, f"Mapping with ID '{mapping_id}' not found"

        config["rule_mappings"] = mappings
        config["metadata"]["last_updated"] = datetime.now().isoformat()

        return self.save_config(config)

    def enable_rule_mapping(self, mapping_id: str, enabled: bool) -> Tuple[bool, str]:
        """Enable or disable a rule mapping."""
        mapping = self.get_rule_mapping(mapping_id)
        if not mapping:
            return False, f"Mapping with ID '{mapping_id}' not found"

        mapping["enabled"] = enabled
        return self.update_rule_mapping(mapping_id, mapping)

    def get_rule_groups(self) -> Dict[str, Any]:
        """Get all rule groups."""
        config = self.get_config()
        return config.get("rule_groups", {})

    def export_config(self) -> Dict[str, Any]:
        """Export current configuration."""
        return self.get_config()

    def import_config(self, imported_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Import and merge configuration."""
        is_valid, errors = self.validate_config(imported_config)
        if not is_valid:
            return False, f"Invalid configuration: {'; '.join(errors)}"

        config = self.get_config()

        # Merge configurations
        config["ifc_element_mappings"].update(imported_config.get("ifc_element_mappings", {}))
        config["rule_mappings"].extend(imported_config.get("rule_mappings", []))

        # Remove duplicates in rule mappings
        seen_ids = set()
        unique_mappings = []
        for mapping in config["rule_mappings"]:
            mapping_id = mapping.get("mapping_id")
            if mapping_id not in seen_ids:
                seen_ids.add(mapping_id)
                unique_mappings.append(mapping)
        config["rule_mappings"] = unique_mappings

        config["metadata"]["last_updated"] = datetime.now().isoformat()
        return self.save_config(config)

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default empty configuration."""
        return {
            "version": "1.0.0",
            "metadata": {
                "title": "Unified Rules Configuration & Mapping",
                "description": "Declarative configuration for mapping IFC attributes to compliance rules",
                "last_updated": datetime.now().isoformat(),
            },
            "global_settings": {
                "rule_resolution_priority": ["regulation", "generated", "custom"],
                "strict_mode": False,
            },
            "ifc_element_mappings": {},
            "rule_mappings": [],
            "rule_groups": {},
        }


# Global instance
_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager(config_path: Optional[str | Path] = None) -> UnifiedConfigManager:
    """Get or create singleton config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfigManager(config_path)
    return _config_manager


__all__ = [
    "UnifiedConfigManager",
    "get_config_manager",
]
