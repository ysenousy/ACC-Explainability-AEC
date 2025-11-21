"""Data validation for IFC graphs."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates IFC data completeness and quality."""

    def validate_ifc_data(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all properties extracted from IFC graph.
        
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
                                        "required_value": "> 800",
                                        "status": "pass",
                                        "severity": "error",
                                        "message": "Width is valid"
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
                "beams": self._get_beam_rules()
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
        """Validate a single property."""
        
        # Check if property is missing
        if value is None or value == "":
            return {
                "property": prop_name,
                "actual_value": "N/A",
                "required_value": constraints.get("description", "Expected value"),
                "status": "fail",
                "severity": "error" if is_required else "warning",
                "message": f"Missing {prop_name}",
                "reason": f"Required property not found" if is_required else "Optional property not provided"
            }

        # Type validation
        expected_type = constraints.get("type")
        if expected_type and not self._check_type(value, expected_type):
            return {
                "property": prop_name,
                "actual_value": str(value),
                "required_value": f"{expected_type} type",
                "status": "fail",
                "severity": "error",
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
                    "severity": "error",
                    "message": f"{prop_name} below minimum",
                    "reason": f"Value {value} is less than minimum {min_val}"
                }

            if max_val is not None and value > max_val:
                return {
                    "property": prop_name,
                    "actual_value": str(value),
                    "required_value": f"<= {max_val}",
                    "status": "fail",
                    "severity": "warning",
                    "message": f"{prop_name} above maximum",
                    "reason": f"Value {value} exceeds maximum {max_val}"
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
            "severity": "info",
            "message": f"{prop_name} is valid",
            "reason": "Property meets all constraints"
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
        """Validation rules for doors."""
        return {
            "required": {
                "width_mm": {
                    "type": "number",
                    "min": 600,
                    "max": 2000,
                    "description": "Width in mm (600-2000)"
                },
                "height_mm": {
                    "type": "number",
                    "min": 1800,
                    "max": 3000,
                    "description": "Height in mm (1800-3000)"
                }
            },
            "optional": {
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
        """Validation rules for spaces."""
        return {
            "required": {
                "area_m2": {
                    "type": "number",
                    "min": 1.0,
                    "max": 5000,
                    "description": "Area in m² (1-5000)"
                }
            },
            "optional": {
                "usage_type": {
                    "type": "string",
                    "description": "Space usage type"
                },
                "storey_name": {
                    "type": "string",
                    "description": "Storey/level name"
                }
            }
        }

    def _get_window_rules(self) -> Dict:
        """Validation rules for windows."""
        return {
            "required": {
                "width_mm": {
                    "type": "number",
                    "min": 400,
                    "max": 3000,
                    "description": "Width in mm (400-3000)"
                },
                "height_mm": {
                    "type": "number",
                    "min": 400,
                    "max": 3000,
                    "description": "Height in mm (400-3000)"
                }
            },
            "optional": {
                "storey_name": {
                    "type": "string",
                    "description": "Storey/level name"
                }
            }
        }

    def _get_wall_rules(self) -> Dict:
        """Validation rules for walls."""
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Wall name/identifier"
                }
            },
            "optional": {
                "height_mm": {
                    "type": "number",
                    "min": 1000,
                    "max": 10000,
                    "description": "Height in mm"
                }
            }
        }

    def _get_slab_rules(self) -> Dict:
        """Validation rules for slabs."""
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Slab name/identifier"
                }
            },
            "optional": {
                "area_m2": {
                    "type": "number",
                    "min": 1.0,
                    "description": "Slab area in m²"
                }
            }
        }

    def _get_column_rules(self) -> Dict:
        """Validation rules for columns."""
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Column name/identifier"
                }
            },
            "optional": {
                "height_mm": {
                    "type": "number",
                    "min": 1000,
                    "description": "Column height in mm"
                }
            }
        }

    def _get_stair_rules(self) -> Dict:
        """Validation rules for stairs."""
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Stair name/identifier"
                }
            },
            "optional": {
                "height_mm": {
                    "type": "number",
                    "min": 0,
                    "max": 10000,
                    "description": "Total stair height in mm"
                }
            }
        }

    def _get_beam_rules(self) -> Dict:
        """Validation rules for beams."""
        return {
            "required": {
                "name": {
                    "type": "string",
                    "description": "Beam name/identifier"
                }
            },
            "optional": {
                "length_mm": {
                    "type": "number",
                    "min": 1000,
                    "description": "Beam length in mm"
                }
            }
        }


def validate_ifc(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to validate IFC graph."""
    validator = DataValidator()
    return validator.validate_ifc_data(graph)
