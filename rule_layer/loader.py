"""Manifest loader and validator for ParametricRule instances."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jsonschema
except ImportError:
    jsonschema = None

logger = logging.getLogger(__name__)


def load_manifest_schema() -> Dict[str, Any]:
    """Load the manifest JSON schema from rule_layer/manifest_schema.json."""
    schema_path = Path(__file__).parent / "manifest_schema.json"
    if not schema_path.exists():
        logger.warning("Manifest schema not found at %s", schema_path)
        return {}
    with schema_path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_manifest(manifest: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate a manifest against the JSON schema.
    
    Returns:
        (is_valid, list_of_errors)
    """
    if jsonschema is None:
        logger.debug("jsonschema not installed; skipping manifest validation")
        return True, []
    
    schema = load_manifest_schema()
    if not schema:
        return True, []
    
    errors = []
    try:
        jsonschema.validate(instance=manifest, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Validation error at {'.'.join(str(p) for p in e.path)}: {e.message}")
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e.message}")
    
    return len(errors) == 0, errors


def load_rules_from_manifest(
    manifest: Dict[str, Any],
    validate: bool = True,
    strict: bool = False,
) -> List[Any]:
    """Convert manifest entries into ParametricRule instances.
    
    Args:
        manifest: manifest dict with 'rules' key.
        validate: whether to validate manifest against schema first.
        strict: if True, raise on validation errors; else log warnings and continue.
    
    Returns:
        List of ParametricRule instances (or empty list if manifest is invalid and strict=True).
    
    Raises:
        ValueError: if strict=True and validation fails.
    """
    # Import here to avoid circular dependency
    from rule_layer.rules.parametric import ParametricRule
    
    if validate:
        is_valid, errors = validate_manifest(manifest)
        if not is_valid:
            msg = f"Manifest validation failed: {'; '.join(errors)}"
            if strict:
                raise ValueError(msg)
            else:
                logger.warning(msg)
    
    rules = []
    for entry in manifest.get("rules", []) or []:
        try:
            rule = ParametricRule.from_manifest(entry)
            rules.append(rule)
        except Exception as exc:
            if strict:
                raise
            logger.warning("Failed to load manifest rule %s: %s", entry.get("id"), exc)
    
    return rules


__all__ = ["load_manifest_schema", "validate_manifest", "load_rules_from_manifest"]
