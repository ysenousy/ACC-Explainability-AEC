"""Dataclasses describing the canonical data-layer payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class SpaceElement:
    guid: str
    name: Optional[str]
    long_name: Optional[str]
    storey_id: Optional[str]
    storey_name: Optional[str]
    area_m2: Optional[float]
    usage_type: Optional[str]
    provenance: str = "IFC:IfcSpace"
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.guid,
            "ifc_guid": self.guid,
            "name": self.name,
            "long_name": self.long_name,
            "storey": self.storey_id,
            "storey_name": self.storey_name,
            "area_m2": self.area_m2,
            "usage_type": self.usage_type,
            "provenance": self.provenance,
        }
        if self.attributes:
            data["attributes"] = self.attributes
        return data


@dataclass(slots=True)
class DoorSpaceConnection:
    space_id: str
    space_name: Optional[str]
    boundary_type: Optional[str]
    boundary_side: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "space_id": self.space_id,
            "space_name": self.space_name,
            "boundary_type": self.boundary_type,
            "boundary_side": self.boundary_side,
        }


@dataclass(slots=True)
class DoorElement:
    guid: str
    name: Optional[str]
    width_mm: Optional[float]
    height_mm: Optional[float]
    fire_rating: Optional[str]
    storey_id: Optional[str] = None
    storey_name: Optional[str] = None
    connections: List[DoorSpaceConnection] = field(default_factory=list)
    provenance: str = "IFC:IfcDoor"
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.guid,
            "ifc_guid": self.guid,
            "name": self.name,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "fire_rating": self.fire_rating,
            "storey_id": self.storey_id,
            "storey_name": self.storey_name,
            "provenance": self.provenance,
            "connected_spaces": [c.to_dict() for c in self.connections],
        }
        if self.attributes:
            data["attributes"] = self.attributes
        return data


@dataclass(slots=True)
class GenericElement:
    """Generic IFC element for all other entity types."""
    guid: str
    ifc_type: str  # e.g., 'IfcWall', 'IfcWindow', 'IfcSlab'
    name: Optional[str]
    provenance: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.guid,
            "ifc_guid": self.guid,
            "ifc_type": self.ifc_type,
            "name": self.name,
            "provenance": self.provenance or f"IFC:{self.ifc_type}",
        }
        if self.attributes:
            data["attributes"] = self.attributes
        return data

