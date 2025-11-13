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


def preview_ifc(model, save_path: Optional[str | Path] = None, *, log: Optional[logging.Logger] = None) -> Dict[str, Any]:
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

    types = [
        "IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey",
        "IfcSpace","IfcWall","IfcWallStandardCase","IfcDoor",
        "IfcDoorType","IfcWindow","IfcSlab","IfcOpeningElement","IfcRelFillsElement",
    ]

    summary = {t: count(t) for t in types}
    for t, n in summary.items():
        log.info("%s: %s", f"{t:24s}", n)

    spaces = model.by_type("IfcSpace")
    doors = model.by_type("IfcDoor")
    walls = model.by_type("IfcWall")

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

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(preview_payload, indent=2), encoding="utf-8")
        log.info("Preview summary saved to %s", save_path)

    return preview_payload
