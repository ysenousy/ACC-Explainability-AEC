# data_layer/extract_core.py
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .exceptions import ExtractionError
from .models import DoorElement, DoorSpaceConnection, SpaceElement

logger = logging.getLogger(__name__)

try:
    import ifcopenshell.util.element as ifc_elem
except ImportError:  # pragma: no cover - optional dependency
    ifc_elem = None


def _get_psets_safe(element) -> Dict[str, Dict[str, Any]]:
    """Return property sets for an IFC element if util is available; else empty dict."""
    if ifc_elem is None:
        return {}
    try:
        return ifc_elem.get_psets(element)
    except Exception as exc:  # pragma: no cover - depends on util implementation
        logger.debug("Failed to pull property sets for %s (%s)", element, exc)
        return {}


def _serialise_value(value: Any) -> Any:
    """Convert ifcopenshell/native values into JSON-serialisable structures."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    for attr in ("wrappedValue", "Value", "NominalValue"):
        if hasattr(value, attr):
            return _serialise_value(getattr(value, attr))
    if hasattr(value, "is_a"):
        guid = getattr(value, "GlobalId", None)
        return guid or str(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [_serialise_value(v) for v in value]
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _normalise_psets(psets: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    normalised: Dict[str, Dict[str, Any]] = {}
    for pset_name, props in psets.items():
        normalised[pset_name] = {prop: _serialise_value(val) for prop, val in props.items()}
    return normalised


def _coerce_float(value: Any) -> Optional[float]:
    value = _serialise_value(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_length_to_mm(value: Optional[float]) -> Optional[float]:
    """Normalize a length value to millimetres using a heuristic.

    Heuristic:
    - If value is None -> return None
    - If value <= 10 -> assume the value is in metres and convert to mm (x1000)
    - Else assume the value is already in millimetres and return as-is
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    # Values <= 10 are likely metres (e.g. 0.9, 1.8, 2.0)
    if v <= 10:
        return v * 1000.0
    return v


def _extract_storey_index(model) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    storey_index: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    try:
        relationships = model.by_type("IfcRelContainedInSpatialStructure")
    except RuntimeError as exc:  # pragma: no cover - schema quirks
        logger.debug("Failed to gather spatial containment relationships: %s", exc)
        return storey_index

    for rel in relationships:
        structure = getattr(rel, "RelatingStructure", None)
        if structure is None:
            continue
        storey_id = getattr(structure, "GlobalId", None)
        storey_name = getattr(structure, "LongName", None) or getattr(structure, "Name", None)
        for elem in getattr(rel, "RelatedElements", []) or []:
            elem_id = getattr(elem, "GlobalId", None)
            if elem_id:
                storey_index[elem_id] = (storey_id, storey_name)
    return storey_index


def _build_space_lookup(spaces: Iterable[SpaceElement]) -> Dict[str, SpaceElement]:
    return {space.guid: space for space in spaces}


def _build_door_connections(model, space_lookup: Mapping[str, SpaceElement]) -> Dict[str, List[DoorSpaceConnection]]:
    mapping: Dict[str, List[DoorSpaceConnection]] = defaultdict(list)

    try:
        boundaries = model.by_type("IfcRelSpaceBoundary")
    except RuntimeError as exc:  # pragma: no cover - schema quirks
        logger.debug("Failed to gather space boundaries: %s", exc)
        return mapping

    for rel in boundaries:
        door = getattr(rel, "RelatedBuildingElement", None)
        space = getattr(rel, "RelatingSpace", None)
        if door is None or not getattr(door, "is_a", lambda _: False)("IfcDoor"):
            continue
        if space is None:
            continue

        door_id = getattr(door, "GlobalId", None)
        space_id = getattr(space, "GlobalId", None)
        if not door_id or not space_id:
            continue

        space_name = getattr(space, "LongName", None) or getattr(space, "Name", None)
        if space_id in space_lookup:
            space_name = space_lookup[space_id].name or space_name

        connection = DoorSpaceConnection(
            space_id=space_id,
            space_name=space_name,
            boundary_type=getattr(rel, "PhysicalOrVirtualBoundary", None),
            boundary_side=getattr(rel, "InternalOrExternalBoundary", None),
        )
        mapping[door_id].append(connection)

    return mapping


def extract_spaces(model) -> List[SpaceElement]:
    """Extract enriched data about spaces from the IFC model."""
    spaces_out: List[SpaceElement] = []
    storey_index = _extract_storey_index(model)

    try:
        spaces = model.by_type("IfcSpace")
    except RuntimeError as exc:  # pragma: no cover
        raise ExtractionError(message=f"Failed to iterate spaces: {exc}") from exc

    for space in spaces:
        guid = getattr(space, "GlobalId", None)
        if not guid:
            logger.debug("Skipping space without GlobalId: %s", space)
            continue

        psets_raw = _get_psets_safe(space)
        psets = _normalise_psets(psets_raw) if psets_raw else {}

        qto_space = psets.get("BaseQuantities") or psets.get("Qto_SpaceBaseQuantities")
        area_m2 = None
        if qto_space:
            area_m2 = _coerce_float(qto_space.get("NetFloorArea") or qto_space.get("GrossFloorArea"))

        storey_id, storey_name = storey_index.get(guid, (None, None))

        element = SpaceElement(
            guid=guid,
            name=getattr(space, "Name", None),
            long_name=getattr(space, "LongName", None),
            storey_id=storey_id,
            storey_name=storey_name,
            area_m2=area_m2,
            usage_type=getattr(space, "LongName", None),
            attributes={"property_sets": psets} if psets else {},
        )
        spaces_out.append(element)

    return spaces_out


def extract_doors(model, space_lookup: Optional[Mapping[str, SpaceElement]] = None) -> List[DoorElement]:
    """Extract enriched data about doors from the IFC model."""
    doors_out: List[DoorElement] = []
    space_lookup = space_lookup or {}
    door_connections = _build_door_connections(model, space_lookup)

    try:
        doors = model.by_type("IfcDoor")
    except RuntimeError as exc:  # pragma: no cover
        raise ExtractionError(message=f"Failed to iterate doors: {exc}") from exc

    for door in doors:
        guid = getattr(door, "GlobalId", None)
        if not guid:
            logger.debug("Skipping door without GlobalId: %s", door)
            continue

        psets_raw = _get_psets_safe(door)
        psets = _normalise_psets(psets_raw) if psets_raw else {}
        pset_door = psets.get("Pset_DoorCommon", {})

        width_mm = _coerce_float(
            pset_door.get("ClearWidth")
            or pset_door.get("OverallWidth")
            or getattr(door, "OverallWidth", None)
        )
        height_mm = _coerce_float(
            pset_door.get("ClearHeight")
            or getattr(door, "OverallHeight", None)
        )

        # Normalize lengths to millimetres using a conservative heuristic so
        # that downstream rules which expect mm (e.g. MinDoorWidthRule) get
        # consistent units.
        width_mm = _normalize_length_to_mm(width_mm)
        height_mm = _normalize_length_to_mm(height_mm)

        element = DoorElement(
            guid=guid,
            name=getattr(door, "Name", None),
            width_mm=width_mm,
            height_mm=height_mm,
            fire_rating=_serialise_value(pset_door.get("FireRating")),
            connections=door_connections.get(guid, []),
            attributes={"property_sets": psets} if psets else {},
        )
        doors_out.append(element)

    return doors_out
