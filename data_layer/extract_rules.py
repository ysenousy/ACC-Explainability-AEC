"""Extract rule-like definitions from a data-layer graph or IFC model.

This module implements a small heuristic extractor that scans property sets
and common property names for rule parameters (e.g. min_width_mm,
max_occupancy_per_storey, min_area_m2) and produces a normalized
rules manifest suitable for loading by the rule layer.

The extractor is intentionally conservative: it emits parameterised
manifest entries (condition AST + parameters) rather than executing
any code found in the IFC.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger(__name__)


def _heuristic_extract_from_pset(pset: Mapping[str, Any], element_type: str, element_id: str) -> List[Dict[str, Any]]:
    """Given a property-set dict and the element context, return zero or more
    rule manifest entries discovered in the pset.
    """
    rules: List[Dict[str, Any]] = []
    # flatten keys to lower for simple heuristic matching
    for prop_name, prop_value in pset.items():
        lname = prop_name.lower()
        # door min width
        if "min" in lname and "width" in lname and "door" in element_type.lower():
            try:
                val = float(prop_value)
            except Exception:
                continue
            rule = {
                "id": f"IFC_PARAM_DOOR_MIN_WIDTH_{element_id}",
                "name": "Door minimum width (extracted from IFC)",
                "target_type": "door",
                "selector": {"by": "type", "value": "door"},
                "condition": {"op": "<", "lhs": {"attr": "width_mm"}, "rhs": {"param": "min_width_mm"}},
                "parameters": {"min_width_mm": val},
                "severity": "ERROR",
                "code_reference": None,
                "provenance": {"pset": prop_name},
            }
            rules.append(rule)

        # space min area
        if ("min" in lname and "area" in lname) or ("min" in lname and "m2" in lname) or ("area" in lname and "space" in element_type.lower()):
            try:
                val = float(prop_value)
            except Exception:
                continue
            rule = {
                "id": f"IFC_PARAM_SPACE_MIN_AREA_{element_id}",
                "name": "Space minimum area (extracted from IFC)",
                "target_type": "space",
                "selector": {"by": "type", "value": "space"},
                "condition": {"op": "<", "lhs": {"attr": "area_m2"}, "rhs": {"param": "min_area_m2"}},
                "parameters": {"min_area_m2": val},
                "severity": "ERROR",
                "code_reference": None,
                "provenance": {"pset": prop_name},
            }
            rules.append(rule)

        # building max occupancy
        if "max" in lname and "occup" in lname:
            try:
                val = int(prop_value)
            except Exception:
                try:
                    val = int(float(prop_value))
                except Exception:
                    continue
            rule = {
                "id": f"IFC_PARAM_BUILDING_MAX_OCC_{element_id}",
                "name": "Building max occupancy per storey (extracted from IFC)",
                "target_type": "building",
                "selector": {"by": "type", "value": "building"},
                "condition": {"op": "<=", "lhs": {"expr": "sum_spaces_occupancy"}, "rhs": {"param": "max_occupancy_per_storey"}},
                "parameters": {"max_occupancy_per_storey": val},
                "severity": "WARNING",
                "code_reference": None,
                "provenance": {"pset": prop_name},
            }
            rules.append(rule)

    return rules


def extract_rules_from_graph(graph: Mapping[str, Any]) -> Dict[str, Any]:
    """Scan a data-layer graph (dict) for rule-like property sets and return
    a normalized rules manifest.

    The returned manifest includes metadata and a `rules` list that can be
    consumed by the rule layer.
    """
    manifest: Dict[str, Any] = {
        "manifest_id": f"ifc_rules_manifest_{graph.get('building_id', 'unknown')}",
        "source": "data-layer-pset-extraction",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rules": [],
    }

    elements = graph.get("elements", {}) or {}
    seen_ids = set()

    for etype, elist in elements.items():
        for el in elist:
            el_id = el.get("id") or el.get("ifc_guid") or str(id(el))
            psets = el.get("attributes", {}).get("property_sets", {}) or {}
            for pset_name, pset in psets.items():
                try:
                    extracted = _heuristic_extract_from_pset(pset, etype, el_id)
                except Exception as exc:
                    logger.debug("Error extracting rules from pset %s: %s", pset_name, exc)
                    continue
                for r in extracted:
                    if r["id"] in seen_ids:
                        continue
                    seen_ids.add(r["id"])
                    # attach provenance details including pset name and element id
                    r.setdefault("provenance", {})["pset_name"] = pset_name
                    r.setdefault("provenance", {})["element_id"] = el_id
                    r.setdefault("provenance", {})["element_type"] = etype
                    manifest["rules"].append(r)

    return manifest


def write_manifest(manifest: Dict[str, Any], out_path: Optional[str | Path]) -> Path:
    out_path = Path(out_path or f"{manifest.get('manifest_id','rules')}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path


__all__ = ["extract_rules_from_graph", "write_manifest"]
