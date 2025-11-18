"""Extract rule-like definitions from a data-layer graph or IFC model.

This module implements extraction strategies:
1. Heuristic: Scans property sets for rule parameters
2. Statistical: Generates baselines from building data
3. Metadata: Detects missing data and completeness issues

Produces a normalized rules manifest suitable for loading by the rule layer.
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


def _extract_statistical_rules(graph: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Generate rules from statistical analysis of building elements.
    
    Analyzes all elements of a type to calculate baseline thresholds
    (percentiles, means, etc.) and generates rules based on them.
    """
    rules: List[Dict[str, Any]] = []
    elements = graph.get("elements", {}) or {}
    
    # Collect door widths
    door_widths = []
    for door in elements.get("doors", []) or []:
        width = door.get("width_mm")
        if width is not None:
            try:
                door_widths.append(float(width))
            except (TypeError, ValueError):
                continue
    
    # Generate door width baseline rule (10th percentile)
    if len(door_widths) >= 3:
        sorted_widths = sorted(door_widths)
        p10_width = sorted_widths[max(0, len(sorted_widths) // 10)]
        
        rule = {
            "id": "STAT_DOOR_WIDTH_10TH_PERCENTILE",
            "name": "Door width baseline (10th percentile from building)",
            "target_type": "door",
            "selector": {"by": "type", "value": "door"},
            "condition": {"op": "<", "lhs": {"attr": "width_mm"}, "rhs": {"param": "min_width_mm"}},
            "parameters": {"min_width_mm": round(p10_width, 2)},
            "severity": "WARNING",
            "code_reference": None,
            "provenance": {
                "source": "statistical_analysis",
                "sample_size": len(door_widths),
                "method": "10th_percentile"
            }
        }
        rules.append(rule)
    
    # Collect space areas
    space_areas = []
    for space in elements.get("spaces", []) or []:
        area = space.get("area_m2")
        if area is not None:
            try:
                space_areas.append(float(area))
            except (TypeError, ValueError):
                continue
    
    # Generate space area baseline rule (10th percentile)
    if len(space_areas) >= 3:
        sorted_areas = sorted(space_areas)
        p10_area = sorted_areas[max(0, len(sorted_areas) // 10)]
        
        rule = {
            "id": "STAT_SPACE_AREA_10TH_PERCENTILE",
            "name": "Space area baseline (10th percentile from building)",
            "target_type": "space",
            "selector": {"by": "type", "value": "space"},
            "condition": {"op": "<", "lhs": {"attr": "area_m2"}, "rhs": {"param": "min_area_m2"}},
            "parameters": {"min_area_m2": round(p10_area, 2)},
            "severity": "WARNING",
            "code_reference": None,
            "provenance": {
                "source": "statistical_analysis",
                "sample_size": len(space_areas),
                "method": "10th_percentile"
            }
        }
        rules.append(rule)
    
    return rules


def _extract_metadata_rules(graph: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Generate validation rules based on data completeness and metadata.
    
    Checks for missing property sets, incomplete data, and structural issues.
    """
    rules: List[Dict[str, Any]] = []
    elements = graph.get("elements", {}) or {}
    
    # Check doors with missing widths
    doors_missing_width = 0
    for door in elements.get("doors", []) or []:
        if door.get("width_mm") is None:
            doors_missing_width += 1
    
    if doors_missing_width > 0:
        rule = {
            "id": "METADATA_DOORS_MISSING_WIDTH",
            "name": "Doors missing width data",
            "target_type": "door",
            "selector": {"by": "type", "value": "door"},
            "condition": {"op": "==", "lhs": {"attr": "width_mm"}, "rhs": None},
            "parameters": {},
            "severity": "INFO",
            "code_reference": None,
            "provenance": {
                "source": "metadata_analysis",
                "issue": f"{doors_missing_width} doors without width data",
                "recommendation": "Add width property sets to incomplete doors"
            }
        }
        rules.append(rule)
    
    # Check spaces with missing areas
    spaces_missing_area = 0
    for space in elements.get("spaces", []) or []:
        if space.get("area_m2") is None:
            spaces_missing_area += 1
    
    if spaces_missing_area > 0:
        rule = {
            "id": "METADATA_SPACES_MISSING_AREA",
            "name": "Spaces missing area data",
            "target_type": "space",
            "selector": {"by": "type", "value": "space"},
            "condition": {"op": "==", "lhs": {"attr": "area_m2"}, "rhs": None},
            "parameters": {},
            "severity": "INFO",
            "code_reference": None,
            "provenance": {
                "source": "metadata_analysis",
                "issue": f"{spaces_missing_area} spaces without area data",
                "recommendation": "Add area property sets to incomplete spaces"
            }
        }
        rules.append(rule)
    
    return rules


def extract_rules_from_graph(graph: Mapping[str, Any], strategies: Optional[List[str]] = None) -> Dict[str, Any]:
    """Scan a data-layer graph (dict) for rule-like property sets and return
    a normalized rules manifest.

    Args:
        graph: The data-layer graph dictionary
        strategies: List of extraction strategies to use:
            - "pset": Property set heuristic extraction (default)
            - "statistical": Statistical baseline generation
            - "metadata": Data completeness validation
            If None, uses ["pset", "statistical", "metadata"]

    Returns:
        A rules manifest dict suitable for the rule layer
    """
    if strategies is None:
        strategies = ["pset", "statistical", "metadata"]
    
    manifest: Dict[str, Any] = {
        "manifest_id": f"ifc_rules_manifest_{graph.get('building_id', 'unknown')}",
        "source": "data-layer-multi-strategy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rules": [],
        "extraction_strategies": strategies,
    }

    elements = graph.get("elements", {}) or {}
    seen_ids = set()

    # Strategy 1: Property set heuristic extraction
    if "pset" in strategies:
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
                        r.setdefault("provenance", {})["pset_name"] = pset_name
                        r.setdefault("provenance", {})["element_id"] = el_id
                        r.setdefault("provenance", {})["element_type"] = etype
                        manifest["rules"].append(r)

    # Strategy 2: Statistical baseline generation
    if "statistical" in strategies:
        stat_rules = _extract_statistical_rules(graph)
        for r in stat_rules:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                manifest["rules"].append(r)

    # Strategy 3: Metadata completeness validation
    if "metadata" in strategies:
        meta_rules = _extract_metadata_rules(graph)
        for r in meta_rules:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                manifest["rules"].append(r)

    return manifest


def write_manifest(manifest: Dict[str, Any], out_path: Optional[str | Path]) -> Path:
    out_path = Path(out_path or f"{manifest.get('manifest_id','rules')}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path


__all__ = ["extract_rules_from_graph", "write_manifest"]
