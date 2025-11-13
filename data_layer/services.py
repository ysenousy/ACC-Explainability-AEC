"""Service layer orchestrating IFC loading, extraction, and graph persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .exceptions import IFCLoadError
from .extract_core import extract_doors, extract_spaces
from .load_ifc import load_ifc, preview_ifc
from .models import DoorElement, SpaceElement
from .extract_rules import extract_rules_from_graph


class DataLayerService:
    """High-level workflow for turning IFC files into data-layer graphs."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._log = logger or logging.getLogger(self.__class__.__name__)

    def load_model(self, ifc_path: str | Path):
        self._log.debug("Loading IFC model from %s", ifc_path)
        return load_ifc(ifc_path)

    def extract_elements(self, model) -> Tuple[list[SpaceElement], list[DoorElement]]:
        self._log.debug("Extracting spaces and doors")
        spaces = extract_spaces(model)
        space_lookup = {space.guid: space for space in spaces}
        doors = extract_doors(model, space_lookup)
        self._log.info(
            "Extracted %s spaces and %s doors (spaces with area=%s, doors with width=%s)",
            len(spaces),
            len(doors),
            sum(1 for s in spaces if s.area_m2 is not None),
            sum(1 for d in doors if d.width_mm is not None),
        )
        return spaces, doors

    def build_graph(self, ifc_path: str | Path, include_rules: bool = False) -> Dict[str, Any]:
        model = self.load_model(ifc_path)
        if model is None:  # pragma: no cover - defensive; load_ifc raises
            raise IFCLoadError(ifc_path)

        spaces, doors = self.extract_elements(model)
        schema = getattr(model, "schema", None)

        coverage = {
            "num_spaces": len(spaces),
            "num_doors": len(doors),
            "spaces_with_area": sum(1 for s in spaces if s.area_m2 is not None),
            "doors_with_width": sum(1 for d in doors if d.width_mm is not None),
        }

        graph: Dict[str, Any] = {
            "building_id": Path(ifc_path).stem,
            "source_file": str(Path(ifc_path)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elements": {
                "spaces": [space.to_dict() for space in spaces],
                "doors": [door.to_dict() for door in doors],
            },
            "meta": {
                "schema": schema,
                "schema_version": "data-layer-v1.0",
                "generated_by": "data-layer-service",
                "coverage": coverage,
            },
        }
        # Optionally extract rules from the generated graph and embed the
        # manifest into the graph meta. Extraction is heuristic and
        # conservative; callers should enable this explicitly.
        if include_rules:
            try:
                manifest = extract_rules_from_graph(graph)
                graph.setdefault("meta", {})["rules_manifest"] = manifest
                self._log.info("Embedded rules manifest with %s rules into graph meta", len(manifest.get("rules", [])))
            except Exception as exc:  # pragma: no cover - defensive
                self._log.exception("Failed to extract rules for graph: %s", exc)
        return graph

    def save_graph(self, ifc_path: str | Path, out_path: Optional[str | Path] = None, include_rules: bool = False) -> Path:
        graph = self.build_graph(ifc_path, include_rules=include_rules)
        ifc_path = Path(ifc_path)

        if out_path is None:
            out_path = ifc_path.with_name(f"{ifc_path.stem}_dataLayer.json")

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
        self._log.info("Data-layer JSON graph saved to %s", out_path)
        return out_path

    def preview(self, ifc_path: str | Path, save_path: Optional[str | Path] = None) -> Dict[str, Any]:
        model = self.load_model(ifc_path)
        return preview_ifc(model, save_path, log=self._log)

