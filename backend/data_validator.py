"""Model validation for IFC graphs."""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates IFC data QUALITY and COMPLETENESS - NOT regulatory compliance.
    
    This is an INITIAL SANITY CHECK that ensures:
    1. Required properties are extracted and present
    2. Data types are correct (string, number, etc.)
    3. Values are physically possible (e.g., positive dimensions)
    
    Regulatory compliance checking is done by the Rule Layer / Compliance Engine.
    """
    
    def __init__(self):
        """Initialize validator.
        
        Note: This validator does NOT load regulatory rules.
        It performs purely structural validation of extracted IFC data.
        """
        pass


    def validate_ifc_data(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all properties extracted from IFC graph.
        
        This performs DATA QUALITY checks only (pass/fail), NOT regulatory compliance.
        
        Args:
            graph: The data-layer graph
            
        Returns:
            {
                "by_element_type": {
                    "doors": {
                        "elements": [
                            {
                                "name": "Door_01",
                                "properties": [
                                    {
                                        "property": "width_mm",
                                        "actual_value": 900,
                                        "required_value": "100-5000 mm",
                                        "status": "pass",
                                        "message": "Width is valid",
                                        "reason": "Property meets all constraints"
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        """
        try:
            validation_result = {"by_element_type": {}}
            elements = graph.get("elements", {})

            # Define validation rules for each element type
            validation_rules = {
                "doors": self._get_door_rules(),
                "spaces": self._get_space_rules(),
                "windows": self._get_window_rules(),
                "walls": self._get_wall_rules(),
                "slabs": self._get_slab_rules(),
                "columns": self._get_column_rules(),
                "stairs": self._get_stair_rules(),
                "beams": self._get_beam_rules(),
                "roofs": self._get_roof_rules(),
                "furniture": self._get_furniture_rules(),
                "equipment": self._get_equipment_rules()
            }

            # Validate each element type
            for elem_type, elem_list in elements.items():
                if not isinstance(elem_list, list) or len(elem_list) == 0:
                    continue

                elem_type_lower = elem_type.lower()
                rules = validation_rules.get(elem_type_lower, {})
                
                if not rules:
                    continue

                element_validations = []
                for element in elem_list:
                    elem_validation = self._validate_element(element, rules, elem_type_lower)
                    if elem_validation["properties"]:  # Only include if has properties
                        element_validations.append(elem_validation)

                if element_validations:
                    validation_result["by_element_type"][elem_type_lower] = {
                        "type": elem_type_lower,
                        "count": len(elem_list),
                        "elements": element_validations
                    }

            return validation_result

        except Exception as e:
            logger.error(f"Error validating IFC data: {e}")
            return {"by_element_type": {}, "error": str(e)}

    def _validate_element(self, element: Dict[str, Any], rules: Dict[str, Any], elem_type: str) -> Dict:
        """Validate a single element against rules."""
        element_name = element.get("name", f"Unknown {elem_type}")
        
        validations = []

        # Check each required property
        for prop_name, constraints in rules.get("required", {}).items():
            value = element.get(prop_name)
            validation = self._validate_property(prop_name, value, constraints, element, is_required=True)
            validations.append(validation)

        # Check each optional property that exists
        for prop_name, constraints in rules.get("optional", {}).items():
            value = element.get(prop_name)
            if value is not None:
                validation = self._validate_property(prop_name, value, constraints, element, is_required=False)
                validations.append(validation)

        return {
            "name": element_name,
            "guid": element.get("ifc_guid", element.get("id", "")),
            "properties": validations
        }

    def _validate_property(self, prop_name: str, value: Any, constraints: Dict, element: Dict, is_required: bool = True) -> Dict:
        """Validate a single property - DATA QUALITY CHECK ONLY (pass/fail).
        
        Returns simple pass/fail status without regulatory severity.
        """
        
        # Check if property is missing
        if value is None or value == "":
            return {
                "property": prop_name,
                "actual_value": "N/A",
                "required_value": constraints.get("description", "Expected value"),
                "status": "fail",
                "message": f"Missing {prop_name}",
                "reason": f"Required property not extracted from IFC" if is_required else "Optional property not provided"
            }

        # Type validation
        expected_type = constraints.get("type")
        if expected_type and not self._check_type(value, expected_type):
            return {
                "property": prop_name,
                "actual_value": str(value),
                "required_value": f"{expected_type} type",
                "status": "fail",
                "message": f"Invalid type for {prop_name}",
                "reason": f"Expected {expected_type}, got {type(value).__name__}"
            }

        # Range validation for numbers
        if isinstance(value, (int, float)) and expected_type == "number":
            min_val = constraints.get("min")
            max_val = constraints.get("max")

            if min_val is not None and value < min_val:
                return {
                    "property": prop_name,
                    "actual_value": str(value),
                    "required_value": f">= {min_val}",
                    "status": "fail",
                    "message": f"{prop_name} below sanity check minimum",
                    "reason": f"Value {value} is less than physically reasonable minimum {min_val}"
                }

            if max_val is not None and value > max_val:
                return {
                    "property": prop_name,
                    "actual_value": str(value),
                    "required_value": f"<= {max_val}",
                    "status": "fail",
                    "message": f"{prop_name} above sanity check maximum",
                    "reason": f"Value {value} exceeds physically reasonable maximum {max_val}"
                }

        # All validations passed
        min_val = constraints.get("min")
        max_val = constraints.get("max")
        range_desc = ""
        if min_val is not None and max_val is not None:
            range_desc = f" ({min_val}-{max_val})"
        elif min_val is not None:
            range_desc = f" (>= {min_val})"
        elif max_val is not None:
            range_desc = f" (<= {max_val})"

        return {
            "property": prop_name,
            "actual_value": str(value),
            "required_value": constraints.get("description", f"{expected_type or 'value'}{range_desc}"),
            "status": "pass",
            "message": f"{prop_name} is valid",
            "reason": "Property meets all sanity check constraints"
        }

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "float": float,
            "boolean": bool
        }
        
        expected = type_map.get(expected_type.lower())
        if expected is None:
            return True
        
        return isinstance(value, expected)

    # Element-specific validation rules based on actual extracted properties
    
    def _get_door_rules(self) -> Dict:
        """Validation rules for doors - SANITY CHECKS ONLY.
        
        Doors are extracted with name (required) and optional dimensional properties.
        These are physically/logically reasonable ranges for door dimensions.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Door name/identifier"
                }
            },
            "optional": {
                "width_mm": {
                    "type": "number",
                    "min": 100,           # Minimum physically possible door width
                    "max": 5000,          # Maximum physically possible door width
                    "description": "Door width in mm (100-5000, sanity check only)"
                },
                "height_mm": {
                    "type": "number",
                    "min": 500,           # Minimum physically possible door height
                    "max": 5000,          # Maximum physically possible door height
                    "description": "Door height in mm (500-5000, sanity check only)"
                },
                "fire_rating": {
                    "type": "string",
                    "description": "Fire rating classification"
                },
                "storey_name": {
                    "type": "string",
                    "description": "Storey/level name"
                }
            }
        }

    def _get_space_rules(self) -> Dict:
        """Validation rules for spaces - SANITY CHECKS ONLY.
        
        Spaces are extracted with area_m2 as the primary dimensional property.
        These are physically reasonable ranges for space dimensions.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "area_m2": {
                    "type": "number",
                    "min": 0.1,           # Minimum physically possible space area
                    "max": 100000,        # Maximum physically possible space area
                    "description": "Space area in m² (0.1-100000, sanity check only)"
                }
            },
            "optional": {}
        }

    def _get_window_rules(self) -> Dict:
        """Validation rules for windows - SANITY CHECKS ONLY.
        
        Windows are extracted as generic elements with only name property.
        Dimensional data is available in property_sets for compliance rules.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Window name/identifier"
                }
            },
            "optional": {}
        }

    def _get_wall_rules(self) -> Dict:
        """Validation rules for walls - SANITY CHECKS ONLY.
        
        Walls are extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Wall name/identifier"
                }
            },
            "optional": {}
        }

    def _get_slab_rules(self) -> Dict:
        """Validation rules for slabs - SANITY CHECKS ONLY.
        
        Slabs are extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Slab name/identifier"
                }
            },
            "optional": {}
        }

    def _get_column_rules(self) -> Dict:
        """Validation rules for columns - SANITY CHECKS ONLY.
        
        Columns are extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Column name/identifier"
                }
            },
            "optional": {}
        }

    def _get_stair_rules(self) -> Dict:
        """Validation rules for stairs - SANITY CHECKS ONLY.
        
        Stairs are extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Stair name/identifier"
                }
            },
            "optional": {}
        }

    def _get_beam_rules(self) -> Dict:
        """Validation rules for beams - SANITY CHECKS ONLY.
        
        Beams are extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Beam name/identifier"
                }
            },
            "optional": {}
        }

    def _get_roof_rules(self) -> Dict:
        """Validation rules for roofs - SANITY CHECKS ONLY.
        
        Roofs are extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Roof name/identifier"
                }
            },
            "optional": {}
        }

    def _get_furniture_rules(self) -> Dict:
        """Validation rules for furniture - SANITY CHECKS ONLY.
        
        Furniture is extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Furniture name/identifier"
                }
            },
            "optional": {}
        }

    def _get_equipment_rules(self) -> Dict:
        """Validation rules for equipment - SANITY CHECKS ONLY.
        
        Equipment is extracted as generic elements.
        Only basic name property is extracted; no dimensional data.
        NOT regulatory compliance checks (that's handled by Rule Layer).
        """
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Equipment name/identifier"
                }
            },
            "optional": {}
        }


def validate_ifc(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to validate IFC graph."""
    validator = DataValidator()
    return validator.validate_ifc_data(graph)
