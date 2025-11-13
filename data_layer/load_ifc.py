# data_layer/load_ifc.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import ifcopenshell

from .exceptions import IFCLoadError

logger = logging.getLogger(__name__)


def load_ifc(path: str | Path):
    """Loads an IFC file and returns the model handle."""
    path = Path(path)
    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:  # pragma: no cover - depends on runtime environment
        logger.exception("Could not load IFC file '%s'", path)
        raise IFCLoadError(path, exc) from exc

    schema = getattr(model, "schema", None)
    logger.info("Loaded IFC file '%s' (schema=%s)", path, schema)
    return model


def _safe_name(e):
    return getattr(e, "Name", None) or getattr(e, "Tag", None) or getattr(e, "GlobalId", "UNKNOWN")


# Mapping from IFC entity type to friendly key used in counts.
# This is configurable to allow projects to extend/customize it.
TYPE_MAP: dict[str, str] = {
    "IfcSpace": "spaces",
    "IfcWall": "walls",
    "IfcWallStandardCase": "walls",
    "IfcDoor": "doors",
    "IfcWindow": "windows",
    "IfcSlab": "slabs",
    "IfcOpeningElement": "openings",
}

# Top-level types to include in the main summary counts (keeps compatibility with
# previous default list in the function).
PREVIEW_TYPES = [
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcSpace",
    "IfcWall",
    "IfcWallStandardCase",
    "IfcDoor",
    "IfcDoorType",
    "IfcWindow",
    "IfcSlab",
    "IfcOpeningElement",
    "IfcRelFillsElement",
]


# Relation types we will inspect to find elements assigned to spatial structures
RELATION_TYPES = [
    "IfcRelContainedInSpatialStructure",
    "IfcRelAggregates",
    "IfcRelDecomposes",
    "IfcRelNests",
]

# If the model has more than this many objects (approx), skip expensive
# per-storey detailed classification to avoid very long previews.
DETAILED_THRESHOLD = 100_000


def preview_ifc(
    model,
    save_path: Optional[str | Path] = None,
    *,
    log: Optional[logging.Logger] = None,
    type_map: Optional[Dict[str, str]] = None,
    preview_types: Optional[list[str]] = None,
    include_relation_fallbacks: bool = True,
    detailed: bool = True,
) -> Dict[str, Any]:
    """Return basic statistics about the IFC model; optionally save to JSON."""
    log = log or logger
    if not model:
        log.warning("No model loaded; skipping preview.")
        return {}

    def count(t):
        try:
            return len(model.by_type(t))
        except RuntimeError:  # pragma: no cover - depends on schema quirks
            return 0

    # allow overriding the types and mappings via function args (keeps backward
    # compatibility with module-level defaults)
    preview_types = preview_types or PREVIEW_TYPES
    type_map = type_map or TYPE_MAP

    types = preview_types

    # Single-pass caching: call model.by_type for each interesting type once and
    # reuse the results. This reduces repeated calls for large models.
    cache: Dict[str, list] = {}
    for t in set(types) | set(type_map.keys()) | set(RELATION_TYPES):
        try:
            cache[t] = model.by_type(t)
        except RuntimeError:
            cache[t] = []

    summary = {t: len(cache.get(t, [])) for t in types}
    for t, n in summary.items():
        log.info("%s: %s", f"{t:24s}", n)

    spaces = cache.get("IfcSpace", [])
    doors = cache.get("IfcDoor", [])
    walls = cache.get("IfcWall", [])

    if spaces:
        log.info("Example Space: %s (%s)", spaces[0].GlobalId, _safe_name(spaces[0]))
    if doors:
        log.info("Example Door : %s (%s)", doors[0].GlobalId, _safe_name(doors[0]))
    if walls:
        log.info("Example Wall : %s (%s)", walls[0].GlobalId, _safe_name(walls[0]))

    preview_payload = {
        "schema": getattr(model, "schema", None),
        "counts": summary,
    }

    # Per-storey breakdown: collect related elements using a set of relation
    # types (contained, aggregates, decomposes). Deduplicate elements by
    # stable identifier (GlobalId when present) and classify using type_map.
    warnings: list[str] = []
    if detailed:
        try:
            storey_summaries = []
            storeys = cache.get("IfcBuildingStorey", [])

            # quick abort if model is enormous
            total_cached = sum(len(v) for v in cache.values())
            if total_cached > DETAILED_THRESHOLD:
                warnings.append(
                    f"Model appears large ({total_cached} cached objects); skipping detailed per-storey classification"
                )
            else:
                # helper to extract related elements from a relation object
                def related_elems_from_rel(r):
                    return getattr(r, "RelatedElements", None) or getattr(r, "RelatedObjects", None) or []

                relation_lists = {rt: cache.get(rt, []) for rt in RELATION_TYPES}

                for s in storeys:
                    seen_ids: set[str] = set()
                    counts_per_storey = {v: 0 for v in set(type_map.values())}
                    counts_per_storey["total_elements"] = 0

                    # collect candidate relations that point to this storey
                    candidate_rels = []
                    for rt, rels in relation_lists.items():
                        for r in rels:
                            # try several relation attributes to identify relating structure
                            relating = getattr(r, "RelatingStructure", None) or getattr(r, "RelatingObject", None) or getattr(r, "RelatingElement", None)
                            if relating is s or (
                                getattr(relating, "GlobalId", None) == getattr(s, "GlobalId", None)
                            ):
                                candidate_rels.append(r)

                    # from the candidate relations, extract related elements
                    for r in candidate_rels:
                        for el in related_elems_from_rel(r) or []:
                            gid = getattr(el, "GlobalId", None) or str(id(el))
                            if gid in seen_ids:
                                continue
                            seen_ids.add(gid)
                            # classify by type name; if el.is_a() is callable and
                            # returns a string in fakes, handle both forms
                            tname = el.is_a() if hasattr(el, "is_a") else type(el).__name__
                            if not isinstance(tname, str) and callable(getattr(el, "is_a", None)):
                                try:
                                    tname = el.is_a()
                                except Exception:
                                    tname = type(el).__name__

                            mapped = None
                            if isinstance(tname, str):
                                # direct match or prefix match to handle subtypes
                                for k, v in type_map.items():
                                    if tname == k or tname.startswith(k):
                                        mapped = v
                                        break

                            if mapped:
                                counts_per_storey[mapped] = counts_per_storey.get(mapped, 0) + 1
                            counts_per_storey["total_elements"] += 1

                    storey_summaries.append(
                        {
                            "storey_id": getattr(s, "GlobalId", None),
                            "storey_name": _safe_name(s),
                            "elevation": getattr(s, "Elevation", None),
                            "counts": counts_per_storey,
                        }
                    )

            preview_payload["storey_summary"] = storey_summaries
        except RuntimeError:  # pragma: no cover - defensive: schema quirks may raise
            msg = "Could not compute per-storey summary due to schema/runtime error"
            log.debug(msg)
            warnings.append(msg)

    if warnings:
        preview_payload.setdefault("warnings", []).extend(warnings)

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(preview_payload, indent=2), encoding="utf-8")
        log.info("Preview summary saved to %s", save_path)

    return preview_payload
