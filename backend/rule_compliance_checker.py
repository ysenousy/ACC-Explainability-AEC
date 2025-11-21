"""Rule compliance checker - checks how many IFC components pass/fail each regulatory rule."""
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RuleComplianceChecker:
    """Checks IFC components against regulatory rules and shows component-level results per rule."""

    def __init__(self):
        """Initialize the compliance checker."""
        self.regulatory_rules = self._load_regulatory_rules()

    def check_compliance(self, graph: Dict[str, Any], rules_manifest_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Check how many IFC components pass/fail each regulatory rule.
        
        Args:
            graph: The IFC data-layer graph
            rules_manifest_path: Path to rules manifest JSON (optional, unused)
            
        Returns:
            {
                "summary": {
                    "total_rules": 8,
                    "components_checked": 159,
                    "total_evaluations": 456
                },
                "rules": [
                    {
                        "rule_id": "DOOR_WIDTH_REQUIREMENT",
                        "rule_name": "Door Width Requirement",
                        "rule_type": "door",
                        "code_reference": "Building Code 1015",
                        "severity": "error",
                        "components_evaluated": 77,
                        "passed": 45,
                        "failed": 32,
                        "pass_rate": 58.4,
                        "components": [
                            {"name": "Door_01", "status": "pass", "message": "..."},
                            {"name": "Door_02", "status": "fail", "message": "..."}
                        ]
                    }
                ]
            }
        """
        try:
            # Extract all IFC components
            all_components = self._extract_all_components(graph)
            
            # Load regulatory rules
            regulatory_rules = self._load_regulatory_rules()
            
            # Evaluate each rule against all applicable components
            rule_results = []
            for rule in regulatory_rules:
                rule_result = self._evaluate_rule_against_components(rule, all_components)
                rule_results.append(rule_result)
            
            # Calculate summary
            summary = self._calculate_summary(rule_results, all_components)
            
            return {
                "summary": summary,
                "rules": rule_results
            }

        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            return {
                "summary": {"total_rules": 0, "components_checked": 0, "total_evaluations": 0},
                "rules": [],
                "error": str(e)
            }

    def _extract_all_components(self, graph: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Extract all IFC components organized by type."""
        elements = graph.get("elements", {})
        components = {}
        
        # Extract all component types with full attributes
        for comp_type_plural in ["doors", "spaces", "windows", "walls", "slabs", "columns", "stairs", "beams"]:
            comp_list = elements.get(comp_type_plural, [])
            comp_type = comp_type_plural.rstrip('s')  # Singularize: doors -> door
            components[comp_type] = []
            
            for comp in comp_list:
                # Build properties dict from both top-level properties and BaseQuantities
                properties = {}
                
                # Add top-level properties (width_mm, height_mm, fire_rating, etc.)
                for key in comp:
                    if key not in ["id", "ifc_guid", "name", "provenance", "connected_spaces", "attributes"]:
                        properties[key] = comp[key]
                
                # Also extract from BaseQuantities if available
                base_q = comp.get("attributes", {}).get("property_sets", {}).get("BaseQuantities", {})
                for key, val in base_q.items():
                    if key != "id":
                        # Map standard IFC names to property names
                        if key == "Width" and "width_mm" not in properties:
                            properties["width_mm"] = val
                        elif key == "Height" and "height_mm" not in properties:
                            properties["height_mm"] = val
                        elif key == "Area" and "area_m2" not in properties:
                            properties["area_m2"] = val
                
                components[comp_type].append({
                    "name": comp.get("name", f"{comp_type}"),
                    "id": comp.get("ifc_guid", comp.get("id", "")),
                    "properties": properties,
                    "attributes": comp.get("attributes", {}),
                    "full_object": comp
                })
        
        return components

    def _evaluate_rule_against_components(self, rule: Dict[str, Any], components: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Evaluate a single rule against all applicable components."""
        # Get target IFC class from rule
        target = rule.get("target", {})
        ifc_class = target.get("ifc_class", "")
        
        # Map IFC class to component type
        ifc_class_to_type = {
            "IfcDoor": "door",
            "IfcSpace": "space",
            "IfcWindow": "window",
            "IfcWall": "wall",
            "IfcSlab": "slab",
            "IfcColumn": "column",
            "IfcStairFlight": "stair",
            "IfcBeam": "beam"
        }
        
        rule_type = ifc_class_to_type.get(ifc_class, "")
        all_components = components.get(rule_type, [])
        
        # Apply filters from the rule's selector
        selector = target.get("selector", {})
        filters = selector.get("filters", [])
        
        applicable_components = []
        if filters:
            # Check if any component has ANY of the filtered properties
            # If no components have those properties, ignore filters (fallback to all components)
            has_any_property = False
            for comp in all_components:
                if self._has_any_filtered_property(comp, filters):
                    has_any_property = True
                    break
            
            if has_any_property:
                # At least some components have the filtered property, apply filters
                for comp in all_components:
                    if self._component_matches_filters(comp, filters):
                        applicable_components.append(comp)
            else:
                # No components have the filtered property, evaluate all
                applicable_components = all_components
        else:
            # No filters, all components of this type are applicable
            applicable_components = all_components
        
        component_results = []
        passed = 0
        failed = 0
        
        for comp in applicable_components:
            comp_id = comp.get("id", "unknown")
            comp_name = comp.get("name", comp_id)
            properties = comp.get("properties", {})
            
            # Evaluate component against rule
            status, message = self._evaluate_component_against_rule(comp, rule)
            
            component_results.append({
                "name": comp_name,
                "id": comp_id,
                "status": status,
                "message": message,
                "properties": {k: v for k, v in properties.items() if k in ["width_mm", "height_mm", "area_m2", "fire_rating"]}
            })
            
            if status == "pass":
                passed += 1
            else:
                failed += 1
        
        total = len(applicable_components)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "rule_type": rule_type,
            "code_reference": rule.get("provenance", {}).get("section", ""),
            "severity": rule.get("severity", "error").lower(),
            "description": rule.get("description", ""),
            "components_evaluated": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 1),
            "components": component_results,
            "filters_applied": bool(filters) and total < len(all_components)
        }

    def _has_any_filtered_property(self, component: Dict[str, Any], filters: List[Dict]) -> bool:
        """Check if component has ANY of the filtered properties (used to decide if filters are relevant)."""
        attributes = component.get("attributes", {})
        property_sets = attributes.get("property_sets", {})
        
        for filter_spec in filters:
            pset_name = filter_spec.get("pset")
            prop_name = filter_spec.get("property")
            
            pset = property_sets.get(pset_name, {})
            if prop_name in pset:
                return True
        
        return False

    def _component_matches_filters(self, component: Dict[str, Any], filters: List[Dict]) -> bool:
        """Check if a component matches all filters in the list."""
        for filter_spec in filters:
            pset_name = filter_spec.get("pset")
            prop_name = filter_spec.get("property")
            op = filter_spec.get("op", "=")
            filter_value = filter_spec.get("value")
            
            # Get the property from the component
            attributes = component.get("attributes", {})
            property_sets = attributes.get("property_sets", {})
            pset = property_sets.get(pset_name, {})
            actual_value = pset.get(prop_name)
            
            # If property not found, component doesn't match filter
            if actual_value is None:
                return False
            
            # Evaluate filter condition
            if not self._evaluate_condition(actual_value, op, filter_value):
                return False
        
        return True

    def _evaluate_component_against_rule(self, component: Dict[str, Any], rule: Dict[str, Any]) -> tuple:
        """Evaluate a single component against a rule. Returns (status, message)."""
        try:
            # Get condition from rule
            condition = rule.get("condition", {})
            if not condition:
                return ("unknown", "No condition defined in rule")
            
            # Extract LHS value from IFC properties
            lhs_val = self._extract_rule_value(component, condition.get("lhs"))
            if lhs_val is None:
                return ("fail", "Required property not found")
            
            # Get RHS value (parameter)
            rhs_val = rule.get("parameters", {}).get(condition.get("rhs", {}).get("param"))
            if rhs_val is None:
                rhs_val = condition.get("rhs", {}).get("value")
            
            # Evaluate condition
            op = condition.get("op", ">=")
            result = self._evaluate_condition(lhs_val, op, rhs_val)
            
            # Format message
            explanation = rule.get("explanation", {})
            if result:
                status = "pass"
                msg_template = explanation.get("on_pass", f"{lhs_val} {op} {rhs_val}")
            else:
                status = "fail"
                msg_template = explanation.get("on_fail", f"{lhs_val} does not satisfy {op} {rhs_val}")
            
            # Replace placeholders
            message = msg_template.replace("{lhs}", str(lhs_val))
            message = message.replace("{rhs}", str(rhs_val))
            message = message.replace("{guid}", component.get("id", "unknown"))
            
            return (status, message)
            
        except Exception as e:
            logger.error(f"Error evaluating component: {e}")
            return ("unknown", f"Error: {str(e)}")
    
    def _extract_rule_value(self, component: Dict[str, Any], lhs_spec: Dict) -> Optional[float]:
        """Extract value from component based on rule LHS specification."""
        if not lhs_spec:
            return None
        
        source = lhs_spec.get("source")
        
        if source == "qto":
            quantity = lhs_spec.get("quantity", "")
            unit = lhs_spec.get("unit", "mm")
            
            # Get properties dict (already includes BaseQuantities values)
            properties = component.get("properties", {})
            
            # Try direct property names first (width_mm, height_mm, area_m2)
            direct_mapping = {
                "ClearWidth": "width_mm",
                "Width": "width_mm", 
                "Height": "height_mm",
                "ClearHeight": "height_mm",
                "FloorArea": "area_m2",
                "NetFloorArea": "area_m2",
                "GrossFloorArea": "area_m2",
                "Area": "area_m2"
            }
            
            prop_name = direct_mapping.get(quantity)
            if prop_name and prop_name in properties:
                val = properties[prop_name]
                # Ensure it's a number
                if isinstance(val, (int, float)):
                    return float(val)
            
            # Try the quantity name directly as a property key
            if quantity in properties:
                val = properties[quantity]
                if isinstance(val, (int, float)):
                    return float(val)
            
            return None
        
        return None
    
    def _evaluate_condition(self, lhs: float, op: str, rhs: float) -> bool:
        """Evaluate condition: lhs op rhs"""
        if lhs is None or rhs is None:
            return False
        
        if op == ">=":
            return lhs >= rhs
        elif op == ">":
            return lhs > rhs
        elif op == "<=":
            return lhs <= rhs
        elif op == "<":
            return lhs < rhs
        elif op == "=":
            return lhs == rhs
        elif op == "!=":
            return lhs != rhs
        
        return False

    def _load_regulatory_rules(self) -> List[Dict]:
        """Load regulatory rules from enhanced JSON file."""
        from pathlib import Path
        import os
        
        # Get the project root (parent of backend directory)
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        rules_file = project_root / "rules_config" / "enhanced-regulation-rules.json"
        
        if not rules_file.exists():
            logger.warning(f"Regulatory rules file not found at {rules_file}")
            return []
        
        try:
            with open(rules_file, 'r') as f:
                data = json.load(f)
                rules = data.get("rules", [])
                logger.info(f"Loaded {len(rules)} regulatory rules from enhanced file")
                return rules
                
        except Exception as e:
            logger.error(f"Error loading regulatory rules: {e}")
            return []

    def _calculate_summary(self, rule_results: List[Dict], components: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate summary statistics from rule results."""
        total_rules = len(rule_results)
        total_components_checked = sum(len(comps) for comps in components.values())
        total_evaluations = sum(rule["components_evaluated"] for rule in rule_results)
        
        return {
            "total_rules": total_rules,
            "components_checked": total_components_checked,
            "total_evaluations": total_evaluations
        }


def check_rule_compliance(graph: Dict[str, Any], rules_manifest_path: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to check compliance."""
    checker = RuleComplianceChecker()
    return checker.check_compliance(graph, rules_manifest_path)
