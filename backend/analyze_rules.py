"""Rule analysis utilities for hybrid explainability."""
from __future__ import annotations
import logging
from typing import Any, Dict
from data_layer.extract_rules import extract_rules_from_graph
from data_layer.load_ifc import preview_ifc

logger = logging.getLogger(__name__)

def analyze_ifc_rules(model) -> Dict[str, Any]:
    """
    Analyze an IFC model for:
      - element types present
      - extracted rule-like parameters (manifest)
      - applicable hardcoded rules
      - element types with no rules
    """
    preview = preview_ifc(model)
    element_types = {k: v for k, v in (preview.get("counts") or {}).items() if v > 0}
    # For now, only spaces/doors/walls/windows/slabs/openings
    known_types = set([
        "spaces", "doors", "walls", "windows", "slabs", "openings"
    ])
    present_types = {k for k in element_types.keys() if k in known_types}

    # Extract rules from the model's graph (simulate by empty graph for now)
    # In real use, would pass the canonical graph
    # For now, just return empty manifest
    manifest = {"rules": []}
    # TODO: integrate with actual graph extraction

    # Hardcoded rules
    from rule_layer import get_ruleset_metadata
    hardcoded = get_ruleset_metadata()
    hardcoded_rules = hardcoded.get("rules", [])
    hardcoded_targets = {r.get("parameters", {}).get("target_type", None) for r in hardcoded_rules}

    # Find element types with no rules
    types_with_no_rules = [t for t in present_types if not any(t in (r.get("target_type") or "") for r in hardcoded_rules)]

    return {
        "element_types_present": element_types,
        "extracted_rules": manifest.get("rules", []),
        "applicable_rules": [r["id"] for r in hardcoded_rules],
        "unapplied_rules": types_with_no_rules,
    }
