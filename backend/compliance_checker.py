"""Simple rule evaluation against IFC graphs."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """Evaluates rules against IFC data."""
    
    def check_rule_against_graph(self, graph: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single rule against the graph.
        
        Args:
            graph: The data-layer graph
            rule: The rule to check
            
        Returns:
            {
                "passed": bool,
                "message": str,
                "details": dict or None
            }
        """
        try:
            # Get elements from graph
            elements = graph.get("elements", {})
            
            # Determine rule format and get element type
            target = rule.get("target", {})
            target_type = rule.get("target_type", "")
            
            # Modern format: has ifc_class in target
            if target.get("ifc_class"):
                ifc_class = target.get("ifc_class")
                element_type_map = {
                    "IfcDoor": "doors",
                    "IfcSpace": "spaces",
                    "IfcWindow": "windows",
                    "IfcWall": "walls",
                    "IfcSlab": "slabs",
                    "IfcStairFlight": "stairs",
                    "IfcColumn": "columns",
                    "IfcBeam": "beams"
                }
                element_type = element_type_map.get(ifc_class, "").lower()
                selector = target.get("selector", {})
            # Legacy format: has target_type
            elif target_type:
                element_type = target_type.lower()
                selector = rule.get("selector", {})
            else:
                return {
                    "passed": False,
                    "message": "Rule has no target specification",
                    "details": None
                }
            
            if not element_type:
                return {
                    "passed": False,
                    "message": f"Unknown element type: {target_type}",
                    "details": None
                }
            
            # Get elements of this type
            matching_elements = elements.get(element_type, [])
            if not matching_elements:
                return {
                    "passed": True,
                    "message": f"No {element_type} elements found (vacuously true)",
                    "details": {"element_count": 0}
                }
            
            # Apply selector filters
            filtered_elements = self._apply_filters(matching_elements, selector.get("filters", []))
            
            if not filtered_elements:
                return {
                    "passed": True,
                    "message": f"No elements match selector (vacuously true)",
                    "details": {"filtered_count": 0}
                }
            
            # Evaluate condition
            condition = rule.get("condition", {})
            condition_result = self._evaluate_condition(filtered_elements, condition, rule.get("parameters", {}))
            
            return {
                "passed": condition_result["passed"],
                "message": condition_result["message"],
                "details": {
                    "total_elements": len(matching_elements),
                    "filtered_elements": len(filtered_elements),
                    "passed_elements": condition_result.get("passed_count", 0),
                    "failed_elements": condition_result.get("failed_count", 0),
                    "actual_value": condition_result.get("actual_value"),
                    "required_value": condition_result.get("required_value"),
                    "gap": condition_result.get("gap"),
                    "affected_elements": condition_result.get("affected_elements", [])
                }
            }
        
        except Exception as e:
            logger.error(f"Error checking rule: {e}")
            return {
                "passed": False,
                "message": f"Error evaluating rule: {str(e)}",
                "details": None
            }
    
    def _apply_filters(self, elements: List[Dict], filters: List[Dict]) -> List[Dict]:
        """Apply selector filters to elements."""
        if not filters:
            return elements
        
        result = elements
        for filter_item in filters:
            pset = filter_item.get("pset")
            property_name = filter_item.get("property")
            operator = filter_item.get("op", "=")
            value = filter_item.get("value")
            
            result = [
                elem for elem in result
                if self._filter_element(elem, pset, property_name, operator, value)
            ]
        
        return result
    
    def _filter_element(self, element: Dict, pset: str, prop: str, op: str, value: Any) -> bool:
        """Check if element passes a filter."""
        # Look for property in psets
        psets = element.get("psets", {})
        if pset in psets:
            elem_value = psets[pset].get(prop)
            return self._compare(elem_value, op, value)
        
        # Also check direct properties
        if prop in element:
            elem_value = element.get(prop)
            return self._compare(elem_value, op, value)
        
        return False
    
    def _evaluate_condition(self, elements: List[Dict], condition: Dict, parameters: Dict) -> Dict[str, Any]:
        """Evaluate condition against elements."""
        op = condition.get("op", ">=")
        lhs = condition.get("lhs", {})
        rhs = condition.get("rhs", {})
        
        passed_count = 0
        failed_count = 0
        actual_values = []
        failed_elements = []
        
        for element in elements:
            lhs_value = self._extract_value(element, lhs)
            rhs_value = self._extract_value(element, rhs, parameters)
            
            if lhs_value is not None and rhs_value is not None:
                actual_values.append(lhs_value)
                if self._compare(lhs_value, op, rhs_value):
                    passed_count += 1
                else:
                    failed_count += 1
                    failed_elements.append(element.get("name", element.get("id", "Unknown")))
        
        all_passed = failed_count == 0
        
        # Calculate gap (actual - required)
        gap = None
        actual_val = None
        required_val = None
        
        if actual_values:
            # For comparison, use first element's values
            actual_val = actual_values[0]
            required_val = rhs_value if 'rhs_value' in locals() else None
            
            if isinstance(actual_val, (int, float)) and isinstance(required_val, (int, float)):
                gap = actual_val - required_val
        
        return {
            "passed": all_passed,
            "message": f"{passed_count} of {len(elements)} elements passed" if len(elements) > 0 else "No elements to check",
            "passed_count": passed_count,
            "failed_count": failed_count,
            "actual_value": actual_val,
            "required_value": required_val,
            "gap": gap,
            "affected_elements": failed_elements
        }
    
    def _extract_value(self, element: Dict, spec: Dict, parameters: Dict = None) -> Any:
        """Extract value from element based on spec."""
        if parameters is None:
            parameters = {}
        
        # Legacy format: direct attribute name (e.g., "attr": "area_m2")
        if "attr" in spec:
            attr_name = spec.get("attr")
            return element.get(attr_name)
        
        # Legacy format: parameter reference (e.g., "param": "min_area_m2")
        if "param" in spec and "source" not in spec:
            param_name = spec.get("param")
            return parameters.get(param_name)
        
        # Modern format specifications below:
        
        # Constant value
        if spec.get("source") == "constant":
            return spec.get("value")
        
        # Parameter reference
        if spec.get("source") == "parameter":
            param_name = spec.get("param")
            return parameters.get(param_name)
        
        # QTO extraction
        if spec.get("source") == "qto":
            qto_name = spec.get("qto_name")
            quantity = spec.get("quantity")
            qtos = element.get("quantities", {})
            if qto_name in qtos:
                return qtos[qto_name].get(quantity)
        
        # PSet extraction
        if spec.get("source") == "pset":
            pset_name = spec.get("pset_name")
            prop_name = spec.get("property_name")
            psets = element.get("psets", {})
            if pset_name in psets:
                return psets[pset_name].get(prop_name)
        
        # Direct attribute
        if spec.get("source") == "attribute":
            attr_name = spec.get("attribute_name")
            return element.get(attr_name)
        
        return None
    
    def _compare(self, lhs: Any, op: str, rhs: Any) -> bool:
        """Compare two values with operator."""
        if lhs is None or rhs is None:
            return False
        
        try:
            lhs_val = float(lhs) if isinstance(lhs, (int, float)) else lhs
            rhs_val = float(rhs) if isinstance(rhs, (int, float)) else rhs
            
            if op == ">=":
                return lhs_val >= rhs_val
            elif op == ">":
                return lhs_val > rhs_val
            elif op == "<=":
                return lhs_val <= rhs_val
            elif op == "<":
                return lhs_val < rhs_val
            elif op == "=":
                return lhs_val == rhs_val
            elif op == "!=":
                return lhs_val != rhs_val
            else:
                return False
        except (TypeError, ValueError):
            # String comparison
            if op == "=":
                return lhs == rhs
            elif op == "!=":
                return lhs != rhs
            return False
