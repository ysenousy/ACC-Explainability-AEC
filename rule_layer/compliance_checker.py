"""
Compliance Checker - Evaluates IFC elements against regulation rules.
Supports enhanced rule format with QTO/PSet sources and parameterized explanations.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class ComplianceChecker:
    """Evaluates building elements against regulatory compliance rules."""

    def __init__(self, rules_file: Optional[str] = None):
        """
        Initialize compliance checker.
        
        Args:
            rules_file: Path to enhanced-regulation-rules.json
        """
        self.rules = []
        self.results = []
        if rules_file:
            self.load_rules(rules_file)

    def load_rules(self, rules_file: str) -> bool:
        """Load rules from JSON file."""
        try:
            with open(rules_file, 'r') as f:
                data = json.load(f)
                self.rules = data.get('rules', [])
                return True
        except Exception as e:
            print(f"Error loading rules: {e}")
            return False

    def get_element_by_guid(self, graph: Dict, guid: str) -> Optional[Dict]:
        """Find element in graph by GUID."""
        if not graph:
            return None
        
        # Search in different graph sections
        for section in ['elements', 'objects', 'entities']:
            if section in graph:
                for elem in graph[section]:
                    if elem.get('guid') == guid or elem.get('id') == guid:
                        return elem
        return None

    def extract_quantity(self, element: Dict, source: Dict) -> Optional[Tuple[float, str, str]]:
        """
        Extract quantity value from element with fallback support.
        
        Returns: (value, unit, source_used) tuple or None
        
        Supports fallback_sources for checking alternative properties if primary fails.
        """
        # Try primary source first
        result = self._try_extract_from_source(element, source)
        if result:
            value, unit = result
            source_name = self._get_source_name(source)
            return (value, unit, source_name)
        
        # Try fallback sources if primary failed
        fallback_sources = source.get('fallback_sources', [])
        for fallback_source in fallback_sources:
            result = self._try_extract_from_source(element, fallback_source)
            if result:
                value, unit = result
                source_name = self._get_source_name(fallback_source)
                return (value, unit, source_name)
        
        # No value found in primary or any fallback sources
        return None
    
    def _get_source_name(self, source: Dict) -> str:
        """Get human-readable name for a source."""
        if source.get('source') == 'pset':
            pset = source.get('pset', source.get('pset_name', ''))
            prop = source.get('property', '')
            return f"{pset}.{prop}"
        elif source.get('source') == 'qto':
            qto = source.get('qto_name', '')
            quant = source.get('quantity', '')
            return f"{qto}:{quant}"
        elif source.get('source') == 'attribute':
            attr = source.get('attribute', '')
            return f"attr:{attr}"
        elif source.get('source') == 'parameter':
            param = source.get('param', '')
            return f"param:{param}"
        return "unknown"
    
    def _try_extract_from_source(self, element: Dict, source: Dict) -> Optional[Tuple[float, str]]:
        """
        Try to extract quantity from a single source.
        
        Returns: (value, unit) tuple or None
        """
        if source.get('source') == 'qto':
            qto_name = source.get('qto_name')
            quantity = source.get('quantity')
            unit = source.get('unit', 'unknown')
            
            # Check QTO properties in element
            if 'qto' in element:
                qto_data = element['qto']
                if qto_name in qto_data:
                    quant_value = qto_data[qto_name].get(quantity)
                    if quant_value is not None:
                        return (float(quant_value), unit)
            
            return None
        
        elif source.get('source') == 'pset':
            pset_name = source.get('pset_name', source.get('pset'))
            prop_name = source.get('property')
            unit = source.get('unit', 'unknown')
            
            # Check PSet properties in element
            if 'pset' in element:
                pset_data = element['pset']
                if pset_name in pset_data:
                    prop_value = pset_data[pset_name].get(prop_name)
                    if prop_value is not None:
                        return (float(prop_value), unit)
            
            return None
        
        elif source.get('source') == 'attribute':
            attr_name = source.get('attribute')
            unit = source.get('unit', 'unknown')
            
            if attr_name in element:
                return (float(element[attr_name]), unit)
            
            return None
        
        return None

    def evaluate_condition(self, element: Dict, rule: Dict) -> Optional[Dict]:
        """
        Evaluate rule condition against element.
        
        Returns: {
            'passed': bool,
            'lhs_value': float,
            'rhs_value': float,
            'unit': str,
            'operator': str,
            'lhs_source': str,
            'rhs_source': str
        } or None if evaluation not possible
        """
        condition = rule.get('condition', {})
        lhs_source = condition.get('lhs', {})
        rhs_source = condition.get('rhs', {})
        operator = condition.get('op', '>=')

        # Extract LHS value
        lhs_result = self.extract_quantity(element, lhs_source)
        if not lhs_result:
            return None
        lhs_value, lhs_unit, lhs_source_used = lhs_result

        # Extract RHS value
        if rhs_source.get('source') == 'parameter':
            param_name = rhs_source.get('param')
            rhs_value = rule.get('parameters', {}).get(param_name)
            if rhs_value is None:
                return None
            rhs_value = float(rhs_value)
            rhs_source_used = f"param:{param_name}"
        else:
            rhs_result = self.extract_quantity(element, rhs_source)
            if not rhs_result:
                return None
            rhs_value, _, rhs_source_used = rhs_result

        # Evaluate condition
        passed = self._evaluate_operator(lhs_value, operator, rhs_value)

        return {
            'passed': passed,
            'lhs_value': lhs_value,
            'rhs_value': rhs_value,
            'unit': lhs_unit,
            'operator': operator,
            'lhs_source': lhs_source_used,
            'rhs_source': rhs_source_used
        }

    def _evaluate_operator(self, lhs: float, op: str, rhs: float) -> bool:
        """Evaluate comparison operator."""
        if op == '>=':
            return lhs >= rhs
        elif op == '>':
            return lhs > rhs
        elif op == '<=':
            return lhs <= rhs
        elif op == '<':
            return lhs < rhs
        elif op == '=':
            return abs(lhs - rhs) < 0.001
        elif op == '!=':
            return abs(lhs - rhs) >= 0.001
        return False

    def format_explanation(self, template: str, values: Dict) -> str:
        """
        Format explanation message with template variables.
        
        Supports: {guid}, {lhs}, {rhs}, {lhs_value}, {rhs_value}, {unit}
        """
        result = template
        for key, value in values.items():
            # Format numbers with appropriate precision
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            result = result.replace(f"{{{key}}}", formatted_value)
        return result

    def check_element(self, element: Dict, rule: Dict) -> Dict:
        """
        Check single element against single rule.
        
        Returns compliance result with passed/failed status and explanation.
        """
        result = {
            'rule_id': rule.get('id'),
            'element_guid': element.get('guid'),
            'element_type': element.get('type'),
            'rule_name': rule.get('name'),
            'passed': False,
            'explanation': '',
            'severity': rule.get('severity', 'WARNING'),
            'code_reference': rule.get('provenance', {}).get('regulation'),
            'section': rule.get('provenance', {}).get('section')
        }

        # Evaluate condition
        eval_result = self.evaluate_condition(element, rule)
        if not eval_result:
            result['passed'] = None  # Unable to evaluate
            result['explanation'] = "Unable to extract required properties"
            return result

        result['passed'] = eval_result['passed']

        # Generate explanation
        explanation = rule.get('explanation', {})
        if eval_result['passed']:
            template = explanation.get('on_pass', 'Element passes compliance check.')
        else:
            template = explanation.get('on_fail', 'Element fails compliance check.')

        format_values = {
            'guid': element.get('guid', 'unknown'),
            'lhs': f"{eval_result['lhs_value']:.2f}",
            'rhs': f"{eval_result['rhs_value']:.2f}",
            'unit': eval_result['unit'],
            'operator': eval_result['operator']
        }

        result['explanation'] = self.format_explanation(template, format_values)

        return result

    def check_graph(self, graph: Dict, rules: Optional[List[Dict]] = None,
                    target_ifc_classes: Optional[List[str]] = None) -> Dict:
        """
        Check entire IFC graph against rules.
        
        Args:
            graph: IFC graph
            rules: Specific rules to check (uses self.rules if None)
            target_ifc_classes: Filter to specific IFC classes
        
        Returns: {
            'timestamp': str,
            'total_checks': int,
            'passed': int,
            'failed': int,
            'unable': int,
            'results': [...]
        }
        """
        if not rules:
            rules = self.rules
        
        if not graph:
            return {'error': 'No graph provided'}

        results = []
        stats = {'passed': 0, 'failed': 0, 'unable': 0}

        # Get all elements from graph
        elements = []
        for section in ['elements', 'objects', 'entities']:
            if section in graph:
                elements.extend(graph[section])

        # Filter to specific IFC classes if requested
        if target_ifc_classes:
            elements = [e for e in elements 
                       if e.get('ifc_class') in target_ifc_classes]

        # Check each element against each rule
        for rule in rules:
            target = rule.get('target', {})
            target_class = target.get('ifc_class')
            
            # Filter elements by IFC class
            target_elements = elements
            if target_class:
                target_elements = [e for e in elements 
                                  if e.get('ifc_class') == target_class]

            for element in target_elements:
                check_result = self.check_element(element, rule)
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

    def get_summary_by_rule(self, check_results: Dict) -> Dict:
        """Summarize compliance results by rule."""
        summary = {}
        for result in check_results.get('results', []):
            rule_id = result['rule_id']
            if rule_id not in summary:
                summary[rule_id] = {
                    'rule_name': result['rule_name'],
                    'passed': 0,
                    'failed': 0,
                    'unable': 0,
                    'severity': result['severity']
                }
            
            if result['passed'] is True:
                summary[rule_id]['passed'] += 1
            elif result['passed'] is False:
                summary[rule_id]['failed'] += 1
            else:
                summary[rule_id]['unable'] += 1

        return summary

    def get_failing_elements(self, check_results: Dict) -> List[Dict]:
        """Get all elements that failed compliance checks."""
        return [r for r in check_results.get('results', []) 
                if r['passed'] is False]

    def export_report(self, check_results: Dict, output_file: str) -> bool:
        """Export compliance results to JSON report."""
        try:
            with open(output_file, 'w') as f:
                json.dump(check_results, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting report: {e}")
            return False
