"""Rule configuration persistence and management."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Default config storage location
CONFIG_DIR = Path(__file__).parent.parent / "rules_config"
CONFIG_DIR.mkdir(exist_ok=True)
CUSTOM_RULES_FILE = CONFIG_DIR / "custom_rules.json"


def load_custom_rules() -> List[Dict[str, Any]]:
    """Load custom rules from persistent storage."""
    try:
        if CUSTOM_RULES_FILE.exists():
            with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", [])
    except Exception as e:
        logger.warning("Failed to load custom rules: %s", e)
    return []


def save_custom_rules(rules: List[Dict[str, Any]]) -> bool:
    """Save custom rules to persistent storage."""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        payload = {
            "rules": rules,
            "saved_at": datetime.utcnow().isoformat(),
            "version": 1,
        }
        with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info("Custom rules saved: %d rules", len(rules))
        return True
    except Exception as e:
        logger.error("Failed to save custom rules: %s", e)
        return False


def add_rule(rule: Dict[str, Any]) -> bool:
    """Add a rule to the custom ruleset."""
    rules = load_custom_rules()
    # Prevent duplicates
    if any(r.get("id") == rule.get("id") for r in rules):
        logger.warning("Rule %s already exists", rule.get("id"))
        return False
    rules.append(rule)
    return save_custom_rules(rules)


def delete_rule(rule_id: str) -> bool:
    """Delete a rule from the custom ruleset."""
    rules = load_custom_rules()
    original_count = len(rules)
    rules = [r for r in rules if r.get("id") != rule_id]
    if len(rules) < original_count:
        return save_custom_rules(rules)
    logger.warning("Rule %s not found", rule_id)
    return False


def get_all_rules() -> Dict[str, Any]:
    """Get baseline + custom rules combined."""
    from rule_layer import get_ruleset_metadata

    baseline = get_ruleset_metadata()
    custom_rules = load_custom_rules()

    return {
        "baseline": baseline.get("rules", []),
        "custom": custom_rules,
        "total": len(baseline.get("rules", [])) + len(custom_rules),
    }


def import_rules(rules: List[Dict[str, Any]], merge: bool = True) -> Dict[str, Any]:
    """Import rules from external source (JSON, file, etc).
    
    Args:
        rules: List of rule dicts to import
        merge: If True, merge with existing rules; if False, replace all
    
    Returns:
        {'success': bool, 'added': int, 'skipped': int, 'errors': list}
    """
    result = {"success": False, "added": 0, "skipped": 0, "errors": [], "total_imported": 0}
    
    if not isinstance(rules, list):
        result["errors"].append("Rules must be a list")
        return result
    
    result["total_imported"] = len(rules)
    current_rules = load_custom_rules() if merge else []
    existing_ids = {r.get("id") for r in current_rules}
    
    for i, rule in enumerate(rules):
        try:
            # Validate rule has required fields
            if not rule.get("id"):
                result["errors"].append(f"Rule {i}: missing 'id' field")
                result["skipped"] += 1
                continue
            if not rule.get("name"):
                result["errors"].append(f"Rule {i}: missing 'name' field")
                result["skipped"] += 1
                continue
            
            # Check for duplicates
            if rule.get("id") in existing_ids:
                result["errors"].append(f"Rule {rule.get('id')}: already exists (skipped)")
                result["skipped"] += 1
                continue
            
            # Add rule
            current_rules.append(rule)
            existing_ids.add(rule.get("id"))
            result["added"] += 1
            logger.info("Imported rule: %s", rule.get("id"))
        except Exception as e:
            result["errors"].append(f"Rule {i}: {str(e)}")
            result["skipped"] += 1
    
    # Save all rules
    if save_custom_rules(current_rules):
        result["success"] = True
        logger.info("Import complete: %d added, %d skipped", result["added"], result["skipped"])
    else:
        result["errors"].append("Failed to save rules to storage")
    
    return result


def export_rules() -> Dict[str, Any]:
    """Export all custom rules in JSON format."""
    custom_rules = load_custom_rules()
    return {
        "rules": custom_rules,
        "exported_at": datetime.utcnow().isoformat(),
        "count": len(custom_rules),
    }
