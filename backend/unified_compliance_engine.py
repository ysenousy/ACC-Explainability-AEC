"""Unified Compliance Engine - Single source of truth for all compliance checking.

This module consolidates compliance checking for:
1. Legacy rule formats (target_type, selector)
2. Modern regulatory rules (IFC classes, QTO/PSet sources)
3. Component-level evaluation (door widths, room areas, etc.)

Supports both:
- Element-by-element compliance checking
- Aggregate component-level compliance reporting
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class UnifiedComplianceEngine:
    """Unified compliance checking engine supporting all rule formats."""

    def __init__(self, rules_file: Optional[str] = None):
        """Initialize the engine with optional rules file.
        
        IMPORTANT: This engine should NOT automatically load rules from files.
        Rules should be explicitly set via the 'rules' attribute or passed via rules_file parameter.
        This ensures the engine only uses rules explicitly provided by the user.
        """
        self.rules = []
        self.results = []
        if rules_file:
            self._load_rules(rules_file)
        # NOTE: We do NOT call _load_default_rules() here anymore.
        # Rules must be explicitly provided, not loaded from cached files.
        logger.info("[COMPLIANCE ENGINE] Initialized with 0 rules. Rules must be explicitly set.")

    def _load_rules(self, rules_file: str) -> bool:
        """Load rules from JSON file."""
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rules = data.get('rules', [])
                logger.info(f"Loaded {len(self.rules)} rules from {rules_file}")
                return True
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            return False

    def _load_default_rules(self) -> bool:
        """Try to load rules from default locations (enhanced-regulation-rules.json first, then custom_rules.json).
        
        Note: This loads from the repository's rule files. For user-imported rules, 
        they should be passed via rules_manifest_path parameter in check_compliance().
        """
        from pathlib import Path
        
        # Prefer enhanced rules (which contain the latest regulatory rules with fallback sources)
        regulatory_rules_file = Path(__file__).parent.parent / "rules_config" / "enhanced-regulation-rules.json"
        if regulatory_rules_file.exists():
            return self._load_rules(str(regulatory_rules_file))
        
        # Fall back to custom rules if enhanced not found
        custom_rules_file = Path(__file__).parent.parent / "rules_config" / "custom_rules.json"
        if custom_rules_file.exists():
            return self._load_rules(str(custom_rules_file))
        
        logger.warning("No rules files found in default locations")
        return False

    # =========================================================================
    # UNIFIED VALUE EXTRACTION
    # =========================================================================

    def _extract_value(self, element: Dict, spec: Dict, parameters: Dict = None) -> Optional[Any]:
        """
        Extract value from element based on specification.
        
        Supports multiple source formats:
        - Legacy: "attr" key for direct attributes, "param" for parameters
        - Modern: "source" key (qto, pset, parameter, constant, attribute)
        """
        if parameters is None:
            parameters = {}

        # Legacy format - direct attribute
        if "attr" in spec:
            return element.get(spec.get("attr"))

        # Legacy format - parameter reference (without source key)
        if "param" in spec and "source" not in spec:
            return parameters.get(spec.get("param"))

        # Modern format - use source specification
        source = spec.get("source")

        if source == "constant":
            return spec.get("value")

        elif source == "parameter":
            return parameters.get(spec.get("param"))

        elif source == "qto":
            return self._extract_from_qto(element, spec)

        elif source == "pset":
            return self._extract_from_pset(element, spec)

        elif source == "attribute":
            return element.get(spec.get("attribute_name"))

        return None

    def _extract_value_with_source(self, element: Dict, spec: Dict, parameters: Dict = None) -> Optional[tuple]:
        """
        Extract value from element and return which source was actually used.
        
        Returns: (value, source_used) tuple or None
        
        Supports fallback_sources for trying alternative properties if primary fails.
        """
        if parameters is None:
            parameters = {}
        
        # Try primary source
        value = self._extract_value(element, spec, parameters)
        if value is not None:
            source_name = self._get_source_name(spec)
            return (value, source_name)
        
        # Try fallback sources if primary failed
        fallback_sources = spec.get('fallback_sources', [])
        for fallback_spec in fallback_sources:
            value = self._extract_value(element, fallback_spec, parameters)
            if value is not None:
                source_name = self._get_source_name(fallback_spec)
                return (value, source_name)
        
        # No value found in primary or fallback sources
        return None
    
    def _get_source_name(self, spec: Dict) -> str:
        """Get human-readable name for a source specification."""
        source = spec.get('source')
        if source == 'pset':
            pset = spec.get('pset_name', spec.get('pset', ''))
            prop = spec.get('property_name', spec.get('property', ''))
            return f"{pset}.{prop}"
        elif source == 'qto':
            qto = spec.get('qto_name', '')
            quant = spec.get('quantity', '')
            return f"{qto}:{quant}"
        elif source == 'attribute':
            attr = spec.get('attribute', spec.get('attribute_name', ''))
            return f"attr:{attr}"
        elif source == 'parameter':
            param = spec.get('param', '')
            return f"parameter:{param}"
        elif source == 'constant':
            return "constant"
        return "unknown"

    def _extract_from_qto(self, element: Dict, spec: Dict) -> Optional[float]:
        """Extract value from QTO (Quantity Take-Off).
        
        Tries multiple strategies in order of speed/likelihood:
        1. Direct top-level properties (width_mm, height_mm, area_m2) - FASTEST
        2. Legacy QTO locations (quantities, qto)
        3. Modern format BaseQuantities
        4. Property set fallback
        """
        quantity = spec.get("quantity")
        target_unit = spec.get("unit", "mm")
        
        # STRATEGY 1: Direct top-level properties (FASTEST - try first)
        direct_mapping = {
            "ClearWidth": "width_mm",
            "Width": "width_mm",
            "ClearHeight": "height_mm",
            "Height": "height_mm",
            "FloorArea": "area_m2",
            "NetFloorArea": "area_m2",
            "GrossFloorArea": "area_m2",
            "Area": "area_m2"
        }
        
        prop_name = direct_mapping.get(quantity)
        if prop_name and prop_name in element:
            val = element[prop_name]
            if val is not None and isinstance(val, (int, float)):
                logger.debug(f"[QTO] Found direct property '{prop_name}': {val}")
                return float(val)
        
        # STRATEGY 2: Try 'quantities' key (legacy format)
        qto_name = spec.get("qto_name")
        if "quantities" in element and qto_name:
            qtos = element["quantities"]
            if qto_name in qtos:
                val = qtos[qto_name].get(quantity)
                if val is not None:
                    logger.debug(f"[QTO] Found in 'quantities': {val}")
                    return float(val)

        # STRATEGY 3: Try 'qto' key
        if "qto" in element and qto_name:
            qto_data = element["qto"]
            if qto_name in qto_data:
                val = qto_data[qto_name].get(quantity)
                if val is not None:
                    logger.debug(f"[QTO] Found in 'qto': {val}")
                    return float(val)

        # STRATEGY 4: Modern format - attributes.property_sets.BaseQuantities
        base_q = element.get("attributes", {}).get("property_sets", {}).get("BaseQuantities", {})
        if base_q:
            quantity_mapping = {
                "ClearWidth": "Width",
                "Width": "Width",
                "ClearHeight": "Height",
                "Height": "Height",
                "NetFloorArea": "Area",
                "GrossFloorArea": "Area",
                "FloorArea": "Area",
                "Area": "Area",
                "Perimeter": "Perimeter",
                "Volume": "Volume",
                "Depth": "Depth"
            }
            
            mapped_quantity = quantity_mapping.get(quantity, quantity)
            if mapped_quantity in base_q:
                val = base_q[mapped_quantity]
                if val is not None and isinstance(val, (int, float)):
                    if target_unit == "mm" and mapped_quantity in ["Width", "Height", "Depth", "Perimeter"]:
                        logger.debug(f"[QTO] Found BaseQuantities (meters): {val}, converting to mm")
                        return float(val) * 1000.0
                    else:
                        logger.debug(f"[QTO] Found BaseQuantities: {val}")
                        return float(val)
        
        # STRATEGY 5: Check pset properties as fallback
        psets = element.get("attributes", {}).get("property_sets", {})
        for pset_name, pset_data in psets.items():
            if pset_data and isinstance(pset_data, dict):
                for key in ["ClearWidth", "Width", "ClearHeight", "Height", "Area"]:
                    if key in pset_data:
                        val = pset_data[key]
                        if val is not None and isinstance(val, (int, float)):
                            logger.debug(f"[QTO] Found in pset '{pset_name}' property '{key}': {val}")
                            return float(val)
        
        logger.debug(f"[QTO] Could not extract '{quantity}' from element. Available keys: {list(element.keys())}")
        return None

    def _extract_from_pset(self, element: Dict, spec: Dict) -> Optional[Any]:
        """Extract value from PSet (Property Set)."""
        pset_name = spec.get("pset_name")
        prop_name = spec.get("property_name") or spec.get("property")

        # Check multiple possible PSet locations
        if "psets" in element:
            psets = element["psets"]
            if pset_name in psets:
                val = psets[pset_name].get(prop_name)
                return float(val) if val is not None else None

        if "pset" in element:
            pset_data = element["pset"]
            if pset_name in pset_data:
                val = pset_data[pset_name].get(prop_name)
                return float(val) if val is not None else None

        if "attributes" in element:
            property_sets = element["attributes"].get("property_sets", {})
            if pset_name in property_sets:
                val = property_sets[pset_name].get(prop_name)
                return float(val) if val is not None else None

        return None

    # =========================================================================
    # UNIFIED OPERATORS
    # =========================================================================

    def _compare(self, lhs: Any, op: str, rhs: Any) -> bool:
        """Evaluate comparison: lhs op rhs."""
        if lhs is None or rhs is None:
            return False

        try:
            # Numeric comparison
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
                return abs(lhs_val - rhs_val) < 0.001 if isinstance(lhs_val, float) else lhs_val == rhs_val
            elif op == "!=":
                return abs(lhs_val - rhs_val) >= 0.001 if isinstance(lhs_val, float) else lhs_val != rhs_val
            else:
                return False
        except (TypeError, ValueError):
            # String comparison fallback
            if op == "=":
                return lhs == rhs
            elif op == "!=":
                return lhs != rhs
            return False

    # =========================================================================
    # FILTERING & SELECTION
    # =========================================================================

    def _apply_filters(self, elements: List[Dict], filters: List[Dict]) -> List[Dict]:
        """Apply selector filters to elements (legacy format)."""
        if not filters:
            return elements

        result = elements
        for filter_item in filters:
            result = [e for e in result if self._filter_element(e, filter_item)]
        return result

    def _filter_element(self, element: Dict, filter_item: Dict) -> bool:
        """Check if element passes a single filter."""
        pset = filter_item.get("pset")
        prop = filter_item.get("property")
        op = filter_item.get("op", "=")
        value = filter_item.get("value")

        # Check in psets
        psets = element.get("psets", {})
        if pset in psets:
            elem_value = psets[pset].get(prop)
            return self._compare(elem_value, op, value)

        # Check in direct properties
        if prop in element:
            return self._compare(element.get(prop), op, value)

        return False

    def _component_matches_filters(self, component: Dict, filters: List[Dict]) -> bool:
        """Check if component matches all filters (modern format)."""
        for filter_spec in filters:
            pset_name = filter_spec.get("pset")
            prop_name = filter_spec.get("property")
            op = filter_spec.get("op", "=")
            filter_value = filter_spec.get("value")

            # Get property from component
            attributes = component.get("attributes", {})
            property_sets = attributes.get("property_sets", {})
            pset = property_sets.get(pset_name, {})
            actual_value = pset.get(prop_name)

            if actual_value is None:
                return False

            if not self._compare(actual_value, op, filter_value):
                return False

        return True

    def _has_any_filtered_property(self, component: Dict, filters: List[Dict]) -> bool:
        """Check if component has any of the filtered properties (smart fallback)."""
        attributes = component.get("attributes", {})
        property_sets = attributes.get("property_sets", {})

        for filter_spec in filters:
            pset_name = filter_spec.get("pset")
            prop_name = filter_spec.get("property")
            pset = property_sets.get(pset_name, {})
            if prop_name in pset:
                return True

        return False

    # =========================================================================
    # ELEMENT-BY-ELEMENT EVALUATION (Legacy Format)
    # =========================================================================

    def check_element_against_rule(self, element: Dict, rule: Dict) -> Dict[str, Any]:
        """Check single element against single rule (legacy format)."""
        result = {
            'rule_id': rule.get('id'),
            'element_guid': element.get('guid') or element.get('id'),
            'element_type': element.get('type') or element.get('ifc_class'),
            'element_name': element.get('name'),
            'rule_name': rule.get('name'),
            'passed': False,
            'explanation': '',
            'severity': rule.get('severity', 'WARNING'),
            'code_reference': rule.get('provenance', {}).get('regulation'),
            'section': rule.get('provenance', {}).get('section'),
            'actual_value': None,
            'required_value': None,
            'unit': None,
            'data_source': None,
            'data_status': 'unknown'
        }

        # Evaluate condition
        condition = rule.get('condition', {})
        lhs_source = condition.get('lhs', {})
        rhs_source = condition.get('rhs', {})
        operator = condition.get('op', '>=')

        # Extract LHS value
        lhs_result = self._extract_value_with_source(element, lhs_source, rule.get('parameters', {}))
        if lhs_result is None:
            # MORE LENIENT: Mark as "Unable" but still try to pass if element doesn't have required properties
            # This prevents false negatives when IFC data isn't fully populated
            result['passed'] = None
            result['explanation'] = f"Unable to extract property '{lhs_source.get('quantity', 'unknown')}' from element - insufficient data"
            result['data_status'] = 'missing'
            logger.debug(f"Rule {rule.get('id')}: Could not extract LHS from element {element.get('name', 'unknown')}")
            return result
        
        lhs_value, lhs_source_used = lhs_result

        # Extract RHS value
        if rhs_source.get('source') == 'parameter':
            rhs_value = rule.get('parameters', {}).get(rhs_source.get('param'))
            rhs_source_used = f"parameter:{rhs_source.get('param')}"
        else:
            rhs_result = self._extract_value_with_source(element, rhs_source, rule.get('parameters', {}))
            if rhs_result is None:
                result['passed'] = None
                result['explanation'] = "Unable to extract comparison value from rule"
                result['data_status'] = 'missing'
                logger.debug(f"Rule {rule.get('id')}: Could not extract RHS")
                return result
            rhs_value, rhs_source_used = rhs_result

        # Store actual and required values for reasoning
        result['actual_value'] = lhs_value
        result['required_value'] = rhs_value
        result['unit'] = lhs_source.get('unit', '')
        result['data_source'] = lhs_source_used
        result['data_status'] = 'complete'

        # Evaluate
        result['passed'] = self._compare(lhs_value, operator, rhs_value)

        # Generate explanation
        explanation = rule.get('explanation', {})
        template = explanation.get('on_pass') if result['passed'] else explanation.get('on_fail')
        if template:
            result['explanation'] = self._format_explanation(template, {
                'guid': element.get('guid', 'unknown'),
                'lhs': f"{lhs_value:.2f}" if isinstance(lhs_value, float) else str(lhs_value),
                'rhs': f"{rhs_value:.2f}" if isinstance(rhs_value, float) else str(rhs_value),
                'operator': operator
            })

        return result

    def check_graph(self, graph: Dict, rules: Optional[List[Dict]] = None,
                    target_ifc_classes: Optional[List[str]] = None) -> Dict:
        """Check entire graph against rules (legacy format)."""
        if not rules:
            rules = self.rules

        if not graph:
            return {'error': 'No graph provided', 'results': [], 'total_checks': 0, 'passed': 0, 'failed': 0}

        results = []
        stats = {'passed': 0, 'failed': 0, 'unable': 0}

        # Get elements from graph
        elements = []
        for section in ['elements', 'objects', 'entities']:
            if section in graph:
                section_data = graph[section]
                # Handle both list format and dict format
                if isinstance(section_data, dict):
                    # Modern format: {"doors": [...], "spaces": [...], ...}
                    for comp_type, comp_list in section_data.items():
                        if isinstance(comp_list, list):
                            elements.extend(comp_list)
                elif isinstance(section_data, list):
                    # Legacy format: [element1, element2, ...]
                    elements.extend(section_data)

        # Filter to specific IFC classes if requested
        if target_ifc_classes:
            elements = [e for e in elements if isinstance(e, dict) and e.get('ifc_class') in target_ifc_classes]

        # Check each element against each rule
        for rule in rules:
            target = rule.get('target', {})
            target_class = target.get('ifc_class')

            target_elements = elements
            if target_class:
                target_elements = [e for e in elements if isinstance(e, dict) and e.get('ifc_class') == target_class]

            for element in target_elements:
                check_result = self.check_element_against_rule(element, rule)
                results.append(check_result)

                if check_result['passed'] is True:
                    stats['passed'] += 1
                elif check_result['passed'] is False:
                    stats['failed'] += 1
                else:
                    stats['unable'] += 1

        return {
            'timestamp': datetime.now().isoformat(),
            'total_checks': len(results),
            'passed': stats['passed'],
            'failed': stats['failed'],
            'unable': stats['unable'],
            'pass_rate': (stats['passed'] / len(results) * 100) if results else 0,
            'results': results
        }

    # =========================================================================
    # COMPONENT-LEVEL EVALUATION (Modern Format)
    # =========================================================================

    def _extract_all_components(self, graph: Dict) -> Dict[str, List[Dict]]:
        """Extract all IFC components organized by type (modern format).
        
        Note: The graph has inconsistent key naming:
        - Doors and spaces use PLURAL: "doors", "spaces"
        - Other elements use SINGULAR: "wall", "slab", "column", etc.
        """
        elements = graph.get("elements", {})
        components = {}

        # Map component types to their actual keys in the graph
        # Doors and spaces are plural, others are singular
        type_to_key = {
            "door": "doors",
            "space": "spaces",
            "window": "windows",  # Could be plural or singular, try both
            "wall": "wall",
            "slab": "slab",
            "column": "column",
            "stair": "stair",
            "beam": "beam"
        }
        
        for comp_type, graph_key in type_to_key.items():
            # Try the mapped key first
            comp_list = elements.get(graph_key, [])
            
            # If not found and it's typically singular, try plural
            if not comp_list and graph_key == graph_key.lower() and not graph_key.endswith('s'):
                comp_list = elements.get(graph_key + 's', [])
            
            # If not found and it's typically plural, try singular
            if not comp_list and graph_key.endswith('s'):
                comp_list = elements.get(graph_key[:-1], [])
            
            components[comp_type] = []

            for comp in comp_list:
                # Build properties dict from top-level and BaseQuantities
                properties = {}

                # Top-level properties
                for key in comp:
                    if key not in ["id", "ifc_guid", "name", "provenance", "connected_spaces", "attributes"]:
                        properties[key] = comp[key]

                # BaseQuantities
                base_q = comp.get("attributes", {}).get("property_sets", {}).get("BaseQuantities", {})
                for key, val in base_q.items():
                    if key != "id":
                        if key == "Width" and "width_mm" not in properties:
                            properties["width_mm"] = val
                        elif key == "Height" and "height_mm" not in properties:
                            properties["height_mm"] = val
                        elif key == "Area" and "area_m2" not in properties:
                            properties["area_m2"] = val

                # Extract property_sets and attributes for use by _extract_pset_value and _extract_attribute_value
                psets = comp.get("attributes", {}).get("property_sets", {})
                attributes = comp.get("attributes", {}).get("attributes", {})

                components[comp_type].append({
                    "name": comp.get("name", f"{comp_type}"),
                    "id": comp.get("ifc_guid", comp.get("id", "")),
                    "properties": properties,
                    "attributes": comp.get("attributes", {}),
                    "data": {
                        "psets": psets,
                        "attributes": attributes
                    },
                    "full_object": comp
                })
        
        # Debug logging
        for comp_type, comps in components.items():
            if comps:
                logger.info(f"[EXTRACT] {comp_type}: {len(comps)} components, Sample psets: {list(comps[0].get('data', {}).get('psets', {}).keys())[:3]}")

        return components

    def _extract_rule_value(self, component: Dict, lhs_spec: Dict) -> Optional[float]:
        """Extract value from component based on rule LHS specification (modern format).
        
        Supports:
        - qto: Quantities (e.g., Qto_DoorBaseQuantities.ClearWidth)
        - pset: Property Sets with fallback sources (e.g., Pset_WallCommon.FireRating)
        - attribute: Direct attributes on component
        
        Returns the first value found from primary source or fallback sources.
        """
        if not lhs_spec:
            return None

        source = lhs_spec.get("source")
        properties = component.get("properties", {})

        # Handle QTO (Quantities)
        if source == "qto":
            quantity = lhs_spec.get("quantity", "")

            # Map IFC quantity names to property dict keys
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
                if isinstance(val, (int, float)):
                    return float(val)

            # Try quantity name directly
            if quantity in properties:
                val = properties[quantity]
                if isinstance(val, (int, float)):
                    return float(val)

            return None

        # Handle PSET (Property Sets) with fallback sources
        elif source == "pset":
            pset = lhs_spec.get("pset", "")
            property_name = lhs_spec.get("property", "")
            
            # Try primary source
            val = self._extract_pset_value(component, pset, property_name)
            if val is not None:
                return val
            
            # Try fallback sources
            fallback_sources = lhs_spec.get("fallback_sources", [])
            for fallback in fallback_sources:
                fb_source = fallback.get("source", "")
                
                if fb_source == "pset":
                    fb_pset = fallback.get("pset", "")
                    fb_prop = fallback.get("property", "")
                    val = self._extract_pset_value(component, fb_pset, fb_prop)
                    if val is not None:
                        return val
                
                elif fb_source == "attribute":
                    fb_attr = fallback.get("attribute", "")
                    val = self._extract_attribute_value(component, fb_attr)
                    if val is not None:
                        return val
            
            return None

        # Handle ATTRIBUTE (Direct attributes)
        elif source == "attribute":
            attribute = lhs_spec.get("attribute", "")
            return self._extract_attribute_value(component, attribute)

        return None

    def _extract_pset_value(self, component: Dict, pset: str, property_name: str) -> Optional[float]:
        """Extract value from a property set. Returns None if not found."""
        component_data = component.get("data", {})
        psets = component_data.get("psets", {})
        
        if pset in psets:
            pset_data = psets[pset]
            if property_name in pset_data:
                val = pset_data[property_name]
                # Try to convert to float
                try:
                    if isinstance(val, (int, float)):
                        return float(val)
                    elif isinstance(val, str):
                        return float(val)
                except (ValueError, TypeError):
                    pass
        
        return None

    def _extract_attribute_value(self, component: Dict, attribute: str) -> Optional[float]:
        """Extract value from direct component attribute. Returns None if not found."""
        component_data = component.get("data", {})
        attributes = component_data.get("attributes", {})
        
        if attribute in attributes:
            val = attributes[attribute]
            # Try to convert to float
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                elif isinstance(val, str):
                    return float(val)
            except (ValueError, TypeError):
                pass
        
        return None

    def check_component_against_rule(self, component: Dict, rule: Dict) -> Tuple[str, str]:
        """Evaluate a component against a rule. Returns (status, message)."""
        try:
            condition = rule.get("condition", {})
            if not condition:
                return ("unknown", "No condition defined in rule")

            # Extract LHS
            lhs_val = self._extract_rule_value(component, condition.get("lhs"))
            if lhs_val is None:
                return ("unknown", "Required property not found - cannot determine compliance")

            # Extract RHS
            rhs_val = rule.get("parameters", {}).get(condition.get("rhs", {}).get("param"))
            if rhs_val is None:
                rhs_val = condition.get("rhs", {}).get("value")

            # Evaluate
            op = condition.get("op", ">=")
            result = self._compare(lhs_val, op, rhs_val)

            # Format message
            explanation = rule.get("explanation", {})
            if result:
                status = "pass"
                msg_template = explanation.get("on_pass", f"{lhs_val} {op} {rhs_val}")
            else:
                status = "fail"
                msg_template = explanation.get("on_fail", f"{lhs_val} does not satisfy {op} {rhs_val}")

            message = msg_template.replace("{lhs}", str(lhs_val))
            message = message.replace("{rhs}", str(rhs_val))
            message = message.replace("{guid}", component.get("id", "unknown"))

            return (status, message)

        except Exception as e:
            logger.error(f"Error evaluating component: {e}")
            return ("unknown", f"Error: {str(e)}")

    def check_compliance(self, graph: Dict, rules_manifest_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Check component-level compliance against regulatory rules (modern format).
        
        Returns component-by-component results per rule.
        """
        try:
            # Load regulatory rules if not already loaded
            if not self.rules and rules_manifest_path:
                self._load_rules(rules_manifest_path)

            logger.info(f"[COMPLIANCE CHECK] Rules loaded: {len(self.rules)}")
            logger.info(f"[COMPLIANCE CHECK] First 3 rule IDs: {[r.get('id', 'N/A') for r in self.rules[:3]]}")

            # Extract components
            all_components = self._extract_all_components(graph)
            logger.info(f"[COMPLIANCE CHECK] Components extracted: {[(k, len(v)) for k, v in all_components.items() if v]}")

            # Evaluate each rule
            rule_results = []
            for rule in self.rules:
                rule_result = self._evaluate_regulatory_rule(rule, all_components)
                rule_results.append(rule_result)

            # Calculate summary
            summary = {
                "total_rules": len(rule_results),
                "components_checked": sum(len(comps) for comps in all_components.values()),
                "total_evaluations": sum(r["components_evaluated"] for r in rule_results)
            }

            return {
                "summary": summary,
                "rules": rule_results
            }

        except Exception as e:
            logger.error(f"Error checking compliance: {e}", exc_info=True)
            return {
                "summary": {"total_rules": 0, "components_checked": 0, "total_evaluations": 0},
                "rules": [],
                "error": str(e)
            }

    def _evaluate_regulatory_rule(self, rule: Dict, components: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Evaluate a regulatory rule against components (modern format)."""
        target = rule.get("target", {})
        ifc_class = target.get("ifc_class", "")

        # Map IFC class to component type
        ifc_class_to_type = {
            "IfcDoor": "door", "IfcSpace": "space", "IfcWindow": "window",
            "IfcWall": "wall", "IfcSlab": "slab", "IfcColumn": "column",
            "IfcStairFlight": "stair", "IfcBeam": "beam"
        }

        rule_type = ifc_class_to_type.get(ifc_class, "")
        all_components = components.get(rule_type, [])
        
        # Debug logging
        rule_name = rule.get("name", "Unknown")
        logger.info(f"[RULE EVAL] Rule: {rule_name}, IFC Class: {ifc_class}, Rule Type: {rule_type}, Components Available: {len(all_components)}")
        if all_components:
            logger.info(f"[RULE EVAL] Sample component: {all_components[0].get('name', 'N/A')}")

        # Apply filters
        selector = target.get("selector", {})
        filters = selector.get("filters", [])

        applicable_components = []
        if filters:
            # Check if any component has the filtered properties
            has_any_property = any(self._has_any_filtered_property(c, filters) for c in all_components)

            if has_any_property:
                # Apply filters
                applicable_components = [c for c in all_components if self._component_matches_filters(c, filters)]
            else:
                # Fallback: evaluate all if no components have property
                applicable_components = all_components
        else:
            applicable_components = all_components
        
        logger.info(f"[RULE EVAL] {rule_name}: Applicable components = {len(applicable_components)}")

        # Evaluate components
        component_results = []
        passed = 0
        failed = 0

        for comp in applicable_components:
            comp_id = comp.get("id", "unknown")
            comp_name = comp.get("name", comp_id)
            properties = comp.get("properties", {})

            status, message = self.check_component_against_rule(comp, rule)

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

    # =========================================================================
    # GENERIC RULE CHECKING (Supports Both Formats)
    # =========================================================================

    def check_rule_against_graph(self, graph: Dict, rule: Dict) -> Dict[str, Any]:
        """Generic rule checking supporting both legacy and modern formats."""
        try:
            elements = graph.get("elements", {})

            # Determine rule format and extract target
            target = rule.get("target", {})
            ifc_class = target.get("ifc_class")
            target_type = rule.get("target_type", "")

            # Modern format with ifc_class
            if ifc_class:
                element_type_map = {
                    "IfcDoor": "doors", "IfcSpace": "spaces", "IfcWindow": "windows",
                    "IfcWall": "walls", "IfcSlab": "slabs", "IfcStairFlight": "stairs",
                    "IfcColumn": "columns", "IfcBeam": "beams"
                }
                element_type = element_type_map.get(ifc_class, "").lower()
                selector = target.get("selector", {})
            # Legacy format with target_type
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

            # Apply filters
            filtered_elements = self._apply_filters(matching_elements, selector.get("filters", []))

            if not filtered_elements:
                return {
                    "passed": True,
                    "message": f"No elements match selector (vacuously true)",
                    "details": {"filtered_count": 0}
                }

            # Evaluate condition
            condition = rule.get("condition", {})
            condition_result = self._evaluate_condition_on_elements(filtered_elements, condition, rule.get("parameters", {}))

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

    def _evaluate_condition_on_elements(self, elements: List[Dict], condition: Dict, parameters: Dict) -> Dict[str, Any]:
        """Evaluate condition against multiple elements."""
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

        # Calculate gap
        gap = None
        actual_val = None
        required_val = None

        if actual_values:
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

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _format_explanation(self, template: str, values: Dict) -> str:
        """Format explanation message with template variables."""
        result = template
        for key, value in values.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def get_summary_by_rule(self, check_results: Dict) -> Dict:
        """Summarize results by rule."""
        summary = {}
        for result in check_results.get('results', []):
            rule_id = result['rule_id']
            if rule_id not in summary:
                summary[rule_id] = {
                    'rule_name': result['rule_name'],
                    'passed': 0,
                    'failed': 0,
                    'unable': 0,
                    'severity': result.get('severity', 'ERROR')
                }

            if result['passed'] is True:
                summary[rule_id]['passed'] += 1
            elif result['passed'] is False:
                summary[rule_id]['failed'] += 1
            else:
                summary[rule_id]['unable'] += 1

        return summary

    def get_failing_elements(self, check_results: Dict) -> List[Dict]:
        """Get all failing elements from check results."""
        return [r for r in check_results.get('results', []) if r['passed'] is False]

    def export_report(self, check_results: Dict, output_file: str) -> bool:
        """Export results to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(check_results, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return False


# ============================================================================
# CONVENIENCE FUNCTIONS (Drop-in replacements for old imports)
# ============================================================================

def check_rule_compliance(graph: Dict[str, Any], rules_manifest_path: Optional[str] = None) -> Dict[str, Any]:
    """Check component-level compliance (convenience function)."""
    engine = UnifiedComplianceEngine(rules_manifest_path)
    return engine.check_compliance(graph, rules_manifest_path)
