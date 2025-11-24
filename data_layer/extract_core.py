# data_layer/extract_core.py
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .exceptions import ExtractionError
from .models import DoorElement, DoorSpaceConnection, SpaceElement, GenericElement

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
        # Only consider IfcBuildingStorey, not IfcBuilding or IfcSite
        if not getattr(structure, "is_a", lambda _: False)("IfcBuildingStorey"):
            continue
        storey_id = getattr(structure, "GlobalId", None)
        storey_name = getattr(structure, "LongName", None) or getattr(structure, "Name", None)
        for elem in getattr(rel, "RelatedElements", []) or []:
            elem_id = getattr(elem, "GlobalId", None)
            if elem_id:
                storey_index[elem_id] = (storey_id, storey_name)
    return storey_index



def _find_storey_from_hierarchy(element, model) -> Tuple[Optional[str], Optional[str]]:
    """
    Find storey information by traversing the spatial hierarchy.
    
    IFC spaces may not be directly contained in storeys. This function
    searches through various relationships to find the parent storey.
    """
    try:
        # Check if this element is directly contained in a storey
        related_to = getattr(element, "ContainedInStructure", None)
        if related_to:
            for rel in related_to:
                structure = getattr(rel, "RelatingStructure", None)
                if structure and getattr(structure, "is_a", lambda _: False)("IfcBuildingStorey"):
                    storey_id = getattr(structure, "GlobalId", None)
                    storey_name = getattr(structure, "LongName", None) or getattr(structure, "Name", None)
                    return (storey_id, storey_name)
        
        # If not directly contained, check via IfcZone or other spatial containers
        zones = getattr(element, "GroupedBy", None)
        if zones:
            for rel in zones:
                zone = getattr(rel, "RelatingGroup", None)
                if zone:
                    zone_name = getattr(zone, "Name", None)
                    # Try to find storey via zone's containment
                    zone_contained = getattr(zone, "ContainedInStructure", None)
                    if zone_contained:
                        for zrel in zone_contained:
                            structure = getattr(zrel, "RelatingStructure", None)
                            if structure and getattr(structure, "is_a", lambda _: False)("IfcBuildingStorey"):
                                storey_id = getattr(structure, "GlobalId", None)
                                storey_name = getattr(structure, "LongName", None) or getattr(structure, "Name", None)
                                return (storey_id, storey_name)
    except Exception as exc:
        logger.debug("Failed to traverse spatial hierarchy: %s", exc)
    
    return (None, None)


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
        
        # If storey not found in direct containment, search through hierarchy
        if not storey_id and not storey_name:
            storey_id, storey_name = _find_storey_from_hierarchy(space, model)

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
    storey_index = _extract_storey_index(model)

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

        # Get storey information from door's spatial hierarchy
        storey_id, storey_name = storey_index.get(guid, (None, None))
        
        # If storey not found in direct containment, search through hierarchy
        if not storey_id and not storey_name:
            storey_id, storey_name = _find_storey_from_hierarchy(door, model)

        # Populate BaseQuantities with extracted dimensions for compatibility with compliance rules
        # This enriches the property_sets to ensure compliance engine can find values consistently
        if not psets:
            psets = {}
        if "BaseQuantities" not in psets:
            psets["BaseQuantities"] = {}
        
        # Store width and height in meters (IFC standard) alongside existing mm values
        if width_mm is not None:
            psets["BaseQuantities"]["Width"] = width_mm / 1000.0  # Convert mm to meters
        if height_mm is not None:
            psets["BaseQuantities"]["Height"] = height_mm / 1000.0  # Convert mm to meters

        element = DoorElement(
            guid=guid,
            name=getattr(door, "Name", None),
            width_mm=width_mm,
            height_mm=height_mm,
            fire_rating=_serialise_value(pset_door.get("FireRating")),
            storey_id=storey_id,
            storey_name=storey_name,
            connections=door_connections.get(guid, []),
            attributes={"property_sets": psets} if psets else {},
        )
        doors_out.append(element)

    return doors_out


def extract_all_elements(model) -> Dict[str, List[GenericElement]]:
    """Extract all IFC entity types from the model."""
    elements_by_type: Dict[str, List[GenericElement]] = {}
    
    # List of common IFC entity types to extract
    ifc_types = [
        "IfcWall",
        "IfcWindow",
        "IfcSlab",
        "IfcBeam",
        "IfcColumn",
        "IfcStair",
        "IfcRoof",
        "IfcDoor",
        "IfcSpace",
        "IfcFurniture",
        "IfcEquipment",
    ]
    
    for ifc_type in ifc_types:
        try:
            entities = model.by_type(ifc_type)
        except RuntimeError:
            # Entity type not found in this schema
            continue
        
        elements_out: List[GenericElement] = []
        for entity in entities:
            guid = getattr(entity, "GlobalId", None)
            if not guid:
                logger.debug("Skipping %s without GlobalId: %s", ifc_type, entity)
                continue
            
            psets_raw = _get_psets_safe(entity)
            psets = _normalise_psets(psets_raw) if psets_raw else {}
            
            element = GenericElement(
                guid=guid,
                ifc_type=ifc_type,
                name=getattr(entity, "Name", None),
                provenance=f"IFC:{ifc_type}",
                attributes={"property_sets": psets} if psets else {},
            )
            elements_out.append(element)
        
        if elements_out:
            elements_by_type[ifc_type] = elements_out
    
    return elements_by_type
