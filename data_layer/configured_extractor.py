"""
Configuration-driven IFC element extraction.

Reads extraction_config.json to dynamically extract any IFC element type
with normalized fields (width_mm, height_mm, area_m2, fire_rating, etc).

Supports fallback chains for different IFC vendors and schemas.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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
    from typing import Iterable
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [_serialise_value(v) for v in value]
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _coerce_float(value: Any) -> Optional[float]:
    """Safely coerce value to float."""
    value = _serialise_value(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_length_to_mm(value: Optional[float], threshold: float = 10) -> Optional[float]:
    """
    Normalize length value to millimetres using heuristic.
    
    If value <= threshold, assume metres and convert to mm (x1000).
    Otherwise assume already in mm.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= threshold:
        return v * 1000.0
    return v


def _get_psets_safe(element) -> Dict[str, Dict[str, Any]]:
    """Return property sets for an IFC element."""
    try:
        import ifcopenshell.util.element as ifc_elem
        if ifc_elem is None:
            return {}
        return ifc_elem.get_psets(element)
    except (ImportError, Exception):
        return {}


def _normalise_psets(psets) -> Dict[str, Dict[str, Any]]:
    """Normalize property set values."""
    if not psets:
        return {}
    normalised: Dict[str, Dict[str, Any]] = {}
    for pset_name, props in psets.items():
        if isinstance(props, dict):
            normalised[pset_name] = {prop: _serialise_value(val) for prop, val in props.items()}
    return normalised


class ConfiguredExtractor:
    """
    Configuration-driven IFC element extractor.
    
    Uses extraction_config.json to define how to extract each IFC element type
    with normalized top-level properties and consistent property set handling.
    """

    def __init__(self, config_path: str | Path):
        """Initialize with extraction config."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.element_types_config = self.config.get("element_types", {})
        self.unit_conversions = self.config.get("unit_conversions", {})

    def _load_config(self) -> Dict[str, Any]:
        """Load extraction configuration from JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Extraction config not found at %s", self.config_path)
            return {"element_types": {}}
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in extraction config: %s", e)
            return {"element_types": {}}

    def extract_element(self, ifc_type: str, ifc_entity, model) -> Optional[Dict[str, Any]]:
        """
        Extract a single IFC entity using config-driven approach.
        
        Args:
            ifc_type: IFC entity type (e.g., 'IfcDoor', 'IfcWindow')
            ifc_entity: ifcopenshell entity object
            model: ifcopenshell model (for storey lookup)
            
        Returns:
            Normalized element dict or None if extraction fails
        """
        if ifc_type not in self.element_types_config:
            logger.debug("No config for element type %s", ifc_type)
            return None

        guid = getattr(ifc_entity, "GlobalId", None)
        if not guid:
            logger.debug("Skipping %s without GlobalId", ifc_type)
            return None

        config = self.element_types_config[ifc_type]

        # Extract all property sets
        psets_raw = _get_psets_safe(ifc_entity)
        psets = _normalise_psets(psets_raw) if psets_raw else {}

        # Build element dict with top-level properties
        element: Dict[str, Any] = {
            "id": guid,
            "ifc_guid": guid,
            "ifc_class": ifc_type,
            "ifc_type": ifc_type,
            "name": getattr(ifc_entity, "Name", None),
            "provenance": f"IFC:{ifc_type}",
        }

        # Extract normalized top-level properties if configured
        top_level_config = config.get("top_level_properties", {})
        for prop_name, prop_config in top_level_config.items():
            value = self._extract_property_with_fallbacks(
                ifc_entity, psets, prop_config, ifc_type
            )
            if value is not None:
                element[prop_name] = value

        # Store all property sets in attributes
        if psets:
            element["attributes"] = {"property_sets": psets}
        else:
            element["attributes"] = {}

        return element

    def _extract_property_with_fallbacks(
        self,
        ifc_entity,
        psets: Dict[str, Dict[str, Any]],
        prop_config: Dict[str, Any],
        ifc_type: str,
    ) -> Optional[Any]:
        """
        Extract property with fallback chain.
        
        Fallback chain: pset_fallbacks -> attribute_fallbacks -> None
        """
        normalize_unit = prop_config.get("normalize_unit")

        # Try pset fallbacks
        pset_fallbacks = prop_config.get("pset_fallbacks", [])
        for fallback in pset_fallbacks:
            if "/" not in fallback:
                continue
            pset_name, prop_name = fallback.split("/", 1)
            if pset_name in psets and prop_name in psets[pset_name]:
                value = _coerce_float(psets[pset_name][prop_name])
                if value is not None:
                    return self._normalize_value(value, normalize_unit)

        # Try attribute fallbacks (direct IFC attributes)
        attr_fallbacks = prop_config.get("attribute_fallbacks", [])
        for attr_name in attr_fallbacks:
            if hasattr(ifc_entity, attr_name):
                value = _coerce_float(getattr(ifc_entity, attr_name))
                if value is not None:
                    return self._normalize_value(value, normalize_unit)

        return None

    def _normalize_value(self, value: float, normalize_unit: Optional[str]) -> Optional[float]:
        """Apply unit normalization to value."""
        if normalize_unit is None or value is None:
            return value

        if normalize_unit == "mm":
            return _normalize_length_to_mm(value)
        elif normalize_unit == "m2":
            # For area, normalize similar to length
            # Values < 0.1 likely in m, others in m2
            threshold = self.unit_conversions.get("m2", {}).get("threshold", 0.1)
            if value < threshold:
                return value * 1000000  # m2 to mm2 (not typically used, but for consistency)
            return value

        return value

    def extract_all_by_config(self, model) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all element types defined in config.
        
        Returns:
            Dict mapping output_key (e.g., 'doors', 'windows') to list of elements
        """
        results: Dict[str, List[Dict[str, Any]]] = {}

        for ifc_type, type_config in self.element_types_config.items():
            output_key = type_config.get("output_key", ifc_type.lower())

            try:
                entities = model.by_type(ifc_type)
            except RuntimeError:
                logger.debug("Element type %s not found in model", ifc_type)
                continue

            elements_out = []
            for entity in entities:
                element = self.extract_element(ifc_type, entity, model)
                if element:
                    elements_out.append(element)

            if elements_out:
                results[output_key] = elements_out
                logger.info(
                    "Extracted %d %s elements",
                    len(elements_out),
                    ifc_type,
                )

        return results
