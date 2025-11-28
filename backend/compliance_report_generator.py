"""Compliance Report Generator - Creates detailed compliance reports comparing IFC items with regulatory rules."""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ComplianceReportGenerator:
    """Generates comprehensive compliance reports."""

    def __init__(self, rules: Optional[Dict] = None):
        """Initialize report generator.
        
        Args:
            rules: Optional user-imported rules dict. If not provided, loads defaults.
        """
        if rules is not None:
            # Use user-imported rules (list of rule dicts)
            self.regulatory_rules = list(rules.values()) if isinstance(rules, dict) else rules
        else:
            # Fall back to default rules file
            self.regulatory_rules = self._load_regulatory_rules()

    def generate_report(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report.
        
        Args:
            graph: IFC data-layer graph
            
        Returns:
            {
                "report_id": "timestamp",
                "generated_at": "ISO timestamp",
                "ifc_file": "filename",
                "summary": {
                    "total_items": 50,
                    "items_by_type": {"doors": 10, "spaces": 20, ...},
                    "total_rules": 8,
                    "compliant": 6,
                    "non_compliant": 2
                },
                "items": [
                    {
                        "type": "door",
                        "name": "Door_01",
                        "id": "guid_xxx",
                        "properties": {"width_mm": 900, "height_mm": 2100},
                        "rules_evaluated": [
                            {
                                "rule_id": "DOOR_WIDTH_REQUIREMENT",
                                "rule_name": "Door Width Requirement",
                                "status": "pass",
                                "message": "Width 900mm meets requirement (800-2000mm)",
                                "code_reference": "Building Code 1015"
                            }
                        ]
                    }
                ]
            }
        """
        try:
            report_id = datetime.now().isoformat()
            
            # Extract all items from IFC
            items_report = self._extract_all_items(graph)
            
            # Evaluate each item against rules
            evaluated_items = self._evaluate_items(items_report["items"])
            
            # Calculate summary
            summary = self._calculate_summary(evaluated_items, items_report)
            
            # Get actual IFC filename from source_file or building_id
            ifc_file = graph.get("source_file", graph.get("building_id", "unknown"))
            # Extract just the filename if it's a full path
            if "/" in ifc_file or "\\" in ifc_file:
                from pathlib import Path
                ifc_file = Path(ifc_file).name
            
            return {
                "report_id": report_id,
                "generated_at": report_id,
                "ifc_file": ifc_file,
                "summary": summary,
                "items": evaluated_items
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                "report_id": datetime.now().isoformat(),
                "error": str(e),
                "summary": {"total_items": 0, "items_by_type": {}, "total_rules": 0},
                "items": []
            }

    def _extract_all_items(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all items from IFC graph."""
        elements = graph.get("elements", {})
        items = []
        items_by_type = {}
        
        # Extract doors
        doors = elements.get("doors", [])
        for door in doors:
            items.append({
                "type": "door",
                "name": door.get("name", "Door"),
                "id": door.get("ifc_guid", door.get("id", "")),
                "properties": {
                    "width_mm": door.get("width_mm"),
                    "height_mm": door.get("height_mm"),
                    "fire_rating": door.get("fire_rating"),
                    "storey": door.get("storey_name")
                },
                "attributes": door.get("attributes", {}),
                "full_object": door
            })
            items_by_type["doors"] = items_by_type.get("doors", 0) + 1
        
        # Extract spaces
        spaces = elements.get("spaces", [])
        for space in spaces:
            items.append({
                "type": "space",
                "name": space.get("name", "Space"),
                "id": space.get("ifc_guid", space.get("id", "")),
                "properties": {
                    "area_m2": space.get("area_m2"),
                    "usage_type": space.get("usage_type"),
                    "storey": space.get("storey_name")
                },
                "attributes": space.get("attributes", {}),
                "full_object": space
            })
            items_by_type["spaces"] = items_by_type.get("spaces", 0) + 1
        
        # Extract windows
        windows = elements.get("windows", [])
        for window in windows:
            items.append({
                "type": "window",
                "name": window.get("name", "Window"),
                "id": window.get("ifc_guid", window.get("id", "")),
                "properties": {
                    "width_mm": window.get("width_mm"),
                    "height_mm": window.get("height_mm")
                },
                "attributes": window.get("attributes", {}),
                "full_object": window
            })
            items_by_type["windows"] = items_by_type.get("windows", 0) + 1
        
        # Extract walls
        walls = elements.get("walls", [])
        for wall in walls:
            items.append({
                "type": "wall",
                "name": wall.get("name", "Wall"),
                "id": wall.get("ifc_guid", wall.get("id", "")),
                "properties": {
                    "fire_rating": wall.get("fire_rating")
                },
                "attributes": wall.get("attributes", {}),
                "full_object": wall
            })
            items_by_type["walls"] = items_by_type.get("walls", 0) + 1
        
        # Extract slabs
        slabs = elements.get("slabs", [])
        for slab in slabs:
            items.append({
                "type": "slab",
                "name": slab.get("name", "Slab"),
                "id": slab.get("ifc_guid", slab.get("id", "")),
                "properties": {
                    "area_m2": slab.get("area_m2")
                },
                "attributes": slab.get("attributes", {}),
                "full_object": slab
            })
            items_by_type["slabs"] = items_by_type.get("slabs", 0) + 1
        
        # Extract columns
        columns = elements.get("columns", [])
        for column in columns:
            items.append({
                "type": "column",
                "name": column.get("name", "Column"),
                "id": column.get("ifc_guid", column.get("id", "")),
                "properties": {},
                "attributes": column.get("attributes", {}),
                "full_object": column
            })
            items_by_type["columns"] = items_by_type.get("columns", 0) + 1
        
        # Extract stairs
        stairs = elements.get("stairs", [])
        for stair in stairs:
            items.append({
                "type": "stair",
                "name": stair.get("name", "Stair"),
                "id": stair.get("ifc_guid", stair.get("id", "")),
                "properties": {},
                "attributes": stair.get("attributes", {}),
                "full_object": stair
            })
            items_by_type["stairs"] = items_by_type.get("stairs", 0) + 1
        
        # Extract beams
        beams = elements.get("beams", [])
        for beam in beams:
            items.append({
                "type": "beam",
                "name": beam.get("name", "Beam"),
                "id": beam.get("ifc_guid", beam.get("id", "")),
                "properties": {},
                "attributes": beam.get("attributes", {}),
                "full_object": beam
            })
            items_by_type["beams"] = items_by_type.get("beams", 0) + 1
        
        return {
            "total_items": len(items),
            "items_by_type": items_by_type,
            "items": items
        }

    def _evaluate_items(self, items: List[Dict]) -> List[Dict]:
        """Evaluate each item against applicable rules."""
        evaluated_items = []
        
        for item in items:
            item_type = item.get("type")
            
            # Get rules applicable to this item type
            applicable_rules = self._get_rules_for_type(item_type)
            
            # Evaluate item against each rule
            rules_results = []
            for rule in applicable_rules:
                result = self._evaluate_item_against_rule(item, rule)
                rules_results.append(result)
            
            evaluated_item = {
                "type": item_type,
                "name": item.get("name"),
                "id": item.get("id"),
                "properties": item.get("properties"),
                "rules_evaluated": rules_results,
                "compliance_status": self._determine_item_status(rules_results),
                "compliance_percentage": self._calculate_compliance_percentage(rules_results)
            }
            
            evaluated_items.append(evaluated_item)
        
        return evaluated_items

    def _get_rules_for_type(self, item_type: str) -> List[Dict]:
        """Get applicable rules for item type by matching target IFC class."""
        # Map item types to IFC classes
        type_to_ifc_class = {
            "door": "IfcDoor",
            "space": "IfcSpace",
            "window": "IfcWindow",
            "wall": "IfcWall",
            "slab": "IfcSlab",
            "column": "IfcColumn",
            "stair": "IfcStairFlight",
            "beam": "IfcBeam"
        }
        
        ifc_class = type_to_ifc_class.get(item_type, "")
        if not ifc_class:
            return []
        
        # Get all rules that target this IFC class
        applicable_rules = []
        for rule in self.regulatory_rules:
            target = rule.get("target", {})
            if target.get("ifc_class") == ifc_class:
                applicable_rules.append(rule)
        
        return applicable_rules

    def _check_selector_filters(self, item: Dict, filters: List[Dict]) -> bool:
        """Check if item matches all selector filters.
        
        If no filters are specified, return True (apply rule to all items of type).
        If filters are specified but properties not found in IFC, return True anyway
        (be permissive - assume rule applies unless we can definitively prove otherwise).
        """
        if not filters:
            return True
        
        attributes = item.get("attributes", {})
        properties = item.get("properties", {})
        
        # Track if we found any filter property in the IFC
        found_any_property = False
        all_filters_match = True
        
        for filter_spec in filters:
            pset = filter_spec.get("pset", "")
            property_name = filter_spec.get("property", "")
            op = filter_spec.get("op", "=")
            required_value = filter_spec.get("value")
            
            # Get property value from attributes
            pset_data = attributes.get("property_sets", {}).get(pset, {})
            actual_value = pset_data.get(property_name)
            
            # Fallback: check simplified properties for common cases
            if actual_value is None:
                if property_name == "UsageType" and "usage_type" in properties:
                    actual_value = properties.get("usage_type")
                elif property_name == "IsAccessible" and "is_accessible" in attributes:
                    actual_value = attributes.get("is_accessible")
                elif property_name == "FireExit" and "fire_exit" in attributes:
                    actual_value = attributes.get("fire_exit")
                elif property_name == "IsExternal" and "is_external" in attributes:
                    actual_value = attributes.get("is_external")
            
            # If we found the property, evaluate it
            if actual_value is not None:
                found_any_property = True
                if not self._evaluate_filter(actual_value, op, required_value):
                    all_filters_match = False
                    break
        
        # If we found at least one property and all matched, apply rule
        if found_any_property and all_filters_match:
            return True
        
        # If we didn't find any filter properties in the IFC, be permissive
        # (assume rule applies - don't skip it)
        # This allows rules to work with IFCs that don't have standard properties
        if not found_any_property:
            return True
        
        # If we found properties but they didn't match, skip
        return False

    def _evaluate_filter(self, actual_value, op: str, required_value) -> bool:
        """Evaluate a single filter condition."""
        if actual_value is None:
            return False
        
        if op == "=":
            return actual_value == required_value
        elif op == "!=":
            return actual_value != required_value
        elif op == ">":
            return actual_value > required_value
        elif op == ">=":
            return actual_value >= required_value
        elif op == "<":
            return actual_value < required_value
        elif op == "<=":
            return actual_value <= required_value
        
        return False

    def _evaluate_item_against_rule(self, item: Dict, rule: Dict) -> Dict:
        """Evaluate if item complies with enhanced regulatory rule."""
        rule_id = rule.get("id")
        rule_name = rule.get("name", rule_id)
        status = "unknown"
        message = ""
        
        try:
            # Check if item matches rule selector before evaluating
            target = rule.get("target", {})
            selector = target.get("selector", {})
            filters = selector.get("filters", [])
            
            # If there are filters, check if element matches them
            if filters and not self._check_selector_filters(item, filters):
                # Element doesn't match selector, skip evaluation (not applicable)
                return {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "status": "skip",
                    "message": "Element does not match rule selector criteria (not applicable)",
                    "severity": rule.get("severity", "warning"),
                    "code_reference": rule.get("provenance", {}).get("section", ""),
                    "description": rule.get("description", "")
                }
            
            # Get condition from rule
            condition = rule.get("condition", {})
            if not condition:
                return {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "status": "unknown",
                    "message": "No condition defined in rule",
                    "severity": rule.get("severity", "warning"),
                    "code_reference": rule.get("code_reference", ""),
                    "description": rule.get("description", "")
                }
            
            # Extract LHS value from IFC properties
            lhs_val = self._extract_rule_value(item, condition.get("lhs"))
            if lhs_val is None:
                return {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "status": "fail",
                    "message": f"Required property not found in IFC element",
                    "severity": rule.get("severity", "warning"),
                    "code_reference": rule.get("code_reference", ""),
                    "description": rule.get("description", "")
                }
            
            # Get RHS value (parameter)
            rhs_val = rule.get("parameters", {}).get(condition.get("rhs", {}).get("param"))
            if rhs_val is None:
                rhs_val = condition.get("rhs", {}).get("value")
            
            # Evaluate condition
            op = condition.get("op", ">=")
            result = self._evaluate_condition(lhs_val, op, rhs_val)
            
            # Format message using explanation
            explanation = rule.get("explanation", {})
            if result:
                status = "pass"
                message = explanation.get("on_pass", f"{lhs_val} {op} {rhs_val}")
            else:
                status = "fail"
                message = explanation.get("on_fail", f"{lhs_val} does not satisfy {op} {rhs_val}")
            
            # Replace placeholders in message
            message = message.replace("{lhs}", str(lhs_val))
            message = message.replace("{rhs}", str(rhs_val))
            message = message.replace("{guid}", item.get("id", "unknown"))
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_id}: {e}")
            status = "unknown"
            message = f"Error evaluating rule: {str(e)}"
        
        # Extract basic details for compliance reporting only
        provenance = rule.get("provenance", {})
        
        # Build minimal report entry - no reasoning, benefits, or remediation
        result_dict = {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "status": status,
            "message": message,
            "severity": rule.get("severity", "warning"),
            "code_reference": provenance.get("section", ""),
            "description": rule.get("description", "")
        }
        
        return result_dict
    
    def _extract_rule_value(self, item: Dict, lhs_spec: Dict) -> Optional[float]:
        """Extract value from item based on rule LHS specification."""
        if not lhs_spec:
            return None
        
        source = lhs_spec.get("source")
        
        # Handle IFC attribute extraction (from converted rules)
        if source == "ifc":
            attribute = lhs_spec.get("attribute", "")
            if not attribute:
                return None
            
            # Look in properties first (extracted at top-level by _extract_all_items)
            properties = item.get("properties", {})
            if attribute in properties:
                val = properties[attribute]
                if isinstance(val, (int, float)):
                    return float(val)
            
            # Also check in full_object for direct access
            full_obj = item.get("full_object", {})
            if attribute in full_obj:
                val = full_obj[attribute]
                if isinstance(val, (int, float)):
                    return float(val)
            
            return None
        
        elif source == "qto":
            # Extract from QTO (Quantity) path
            qto_name = lhs_spec.get("qto_name", "")
            quantity = lhs_spec.get("quantity", "")
            unit = lhs_spec.get("unit", "mm")
            
            # Map QTO names to extracted properties
            properties = item.get("properties", {})
            attributes = item.get("attributes", {})
            
            # Look in BaseQuantities first (most common)
            base_q = attributes.get("property_sets", {}).get("BaseQuantities", {})
            if quantity in base_q:
                val = base_q[quantity]
                # Convert to requested unit
                if unit == "mm" and not quantity.startswith("Gross") and not quantity.startswith("Net"):
                    # Height/Width properties from IFC are in meters, convert to mm
                    if isinstance(val, (int, float)):
                        return val * 1000 if val < 100 else val
                return val
            
            # Fallback to simplified property names
            property_map = {
                "ClearWidth": "width_mm",
                "Width": "width_mm",
                "Height": "height_mm",
                "ClearHeight": "height_mm",
                "NetFloorArea": "area_m2",
                "GrossFloorArea": "area_m2"
            }
            
            prop_name = property_map.get(quantity)
            if prop_name and prop_name in properties:
                return properties[prop_name]
            
            return None
        
        elif source == "parameter":
            # This is for RHS, should not reach here
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

    def _determine_item_status(self, rules_results: List[Dict]) -> str:
        """Determine overall compliance status of item.
        
        Logic:
        - If any REQUIRED rule (ERROR severity) fails → "fail"
        - If any OPTIONAL rule (WARNING severity) fails → "partial"
        - If all required rules pass → "pass"
        - If only unknown (optional properties not found) → "pass" (still compliant)
        """
        if not rules_results:
            return "no_rules"
        
        statuses = [r["status"] for r in rules_results]
        severities = {}  # Map status to severity
        for rule in rules_results:
            status = rule["status"]
            severity = rule.get("severity", "ERROR")
            if status not in severities:
                severities[status] = []
            severities[status].append(severity)
        
        # If any REQUIRED (ERROR) rule fails, item fails
        if "fail" in statuses:
            failed_rules = [r for r in rules_results if r["status"] == "fail"]
            if any(r.get("severity") == "ERROR" for r in failed_rules):
                return "fail"
            # If only WARNING rules fail, mark as partial
            return "partial"
        
        # If only "unknown" (optional properties) remain, still pass
        if all(s == "unknown" for s in statuses):
            return "pass"
        
        # If only "unknown" and "pass", still pass
        if all(s in ["unknown", "pass"] for s in statuses):
            return "pass"
        
        # Otherwise pass (all critical rules passed)
        return "pass"

    def _calculate_compliance_percentage(self, rules_results: List[Dict]) -> float:
        """Calculate compliance percentage.
        
        Percentage is based on pass/fail rules, excluding "unknown" (optional properties not evaluated).
        """
        if not rules_results:
            return 0.0
        
        # Only count rules that were actually evaluated (pass/fail), not "unknown" (optional)
        evaluated_rules = [r for r in rules_results if r["status"] != "unknown"]
        
        if not evaluated_rules:
            return 0.0  # No rules were evaluated
        
        passed = sum(1 for r in evaluated_rules if r["status"] == "pass")
        return (passed / len(evaluated_rules)) * 100

    def _calculate_summary(self, evaluated_items: List[Dict], items_report: Dict) -> Dict:
        """Calculate report summary statistics."""
        compliant = sum(1 for item in evaluated_items if item["compliance_status"] == "pass")
        non_compliant = sum(1 for item in evaluated_items if item["compliance_status"] == "fail")
        partial = sum(1 for item in evaluated_items if item["compliance_status"] == "partial")
        no_rules = sum(1 for item in evaluated_items if item["compliance_status"] == "no_rules")
        
        total_rules_evaluated = sum(len(item["rules_evaluated"]) for item in evaluated_items)
        total_rules_passed = sum(
            sum(1 for r in item["rules_evaluated"] if r["status"] == "pass")
            for item in evaluated_items
        )
        total_rules_failed = sum(
            sum(1 for r in item["rules_evaluated"] if r["status"] == "fail")
            for item in evaluated_items
        )
        
        # Build breakdown by rule for transparency
        rules_breakdown = {}
        for item in evaluated_items:
            for rule_result in item["rules_evaluated"]:
                rule_id = rule_result.get("rule_id", "unknown")
                rule_name = rule_result.get("rule_name", rule_id)
                
                if rule_id not in rules_breakdown:
                    rules_breakdown[rule_id] = {
                        "rule_name": rule_name,
                        "passed": 0,
                        "failed": 0,
                        "unknown": 0,
                        "skipped": 0,
                        "severity": rule_result.get("severity", "WARNING"),
                        "failing_elements": []
                    }
                
                status = rule_result.get("status", "unknown")
                if status == "pass":
                    rules_breakdown[rule_id]["passed"] += 1
                elif status == "fail":
                    rules_breakdown[rule_id]["failed"] += 1
                    rules_breakdown[rule_id]["failing_elements"].append({
                        "element_id": item.get("id"),
                        "element_name": item.get("name"),
                        "element_type": item.get("type"),
                        "message": rule_result.get("message", "")
                    })
                elif status == "skip":
                    rules_breakdown[rule_id]["skipped"] += 1
                else:
                    rules_breakdown[rule_id]["unknown"] += 1
        
        # Build breakdown by element type
        items_by_type_breakdown = {}
        for item in evaluated_items:
            item_type = item.get("type", "unknown")
            if item_type not in items_by_type_breakdown:
                items_by_type_breakdown[item_type] = {
                    "pass": 0,
                    "fail": 0,
                    "partial": 0,
                    "no_rules": 0,
                    "total": 0
                }
            
            items_by_type_breakdown[item_type]["total"] += 1
            status = item.get("compliance_status", "unknown")
            if status == "pass":
                items_by_type_breakdown[item_type]["pass"] += 1
            elif status == "fail":
                items_by_type_breakdown[item_type]["fail"] += 1
            elif status == "partial":
                items_by_type_breakdown[item_type]["partial"] += 1
            elif status == "no_rules":
                items_by_type_breakdown[item_type]["no_rules"] += 1
        
        return {
            "total_items": items_report["total_items"],
            "items_by_type": items_report["items_by_type"],
            "items_by_type_breakdown": items_by_type_breakdown,
            "compliant_items": compliant,
            "non_compliant_items": non_compliant,
            "partial_compliance_items": partial,
            "items_with_no_rules": no_rules,
            "total_rules_evaluated": total_rules_evaluated,
            "total_rules_passed": total_rules_passed,
            "total_rules_failed": total_rules_failed,
            "overall_compliance_percentage": (compliant / items_report["total_items"] * 100) if items_report["total_items"] > 0 else 0,
            "rules_breakdown": rules_breakdown
        }

    def _load_regulatory_rules(self) -> List[Dict]:
        """Load regulatory rules from custom_rules.json if available, otherwise from enhanced-regulation-rules.json."""
        from pathlib import Path
        
        # Try to load custom rules first (these are converted from Rule Config and have proper IFC extraction)
        custom_rules_file = Path(__file__).parent.parent / "rules_config" / "custom_rules.json"
        if custom_rules_file.exists():
            try:
                with open(custom_rules_file, 'r') as f:
                    data = json.load(f)
                    rules = data.get("rules", [])
                    logger.info(f"Loaded {len(rules)} custom rules from Rule Config conversion")
                    return rules
            except Exception as e:
                logger.warning(f"Error loading custom rules: {e}, falling back to catalogue rules")
        
        # Fall back to catalogue rules
        rules_file = Path(__file__).parent.parent / "rules_config" / "enhanced-regulation-rules.json"
        
        if not rules_file.exists():
            logger.warning(f"Regulatory rules file not found at {rules_file}")
            return []
        
        try:
            with open(rules_file, 'r') as f:
                data = json.load(f)
                rules = data.get("rules", [])
                logger.info(f"Loaded {len(rules)} regulatory rules from enhanced file (catalogue)")
                return rules
                
        except Exception as e:
            logger.error(f"Error loading regulatory rules: {e}")
            return []


def generate_compliance_report(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to generate compliance report."""
    generator = ComplianceReportGenerator()
    return generator.generate_report(graph)
