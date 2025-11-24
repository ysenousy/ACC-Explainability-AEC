"""
Reasoning Engine

Orchestrates the reasoning layer components (justifier, analyzer, solution generator)
to provide complete explanations for compliance checking.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging

from reasoning_layer.models import (
    ReasoningResult, ReasoningType, reasoning_result_to_dict,
    ElementFailureExplanation
)
from reasoning_layer.reasoning_justifier import RuleJustifier
from reasoning_layer.element_analyzer import ElementFailureAnalyzer
from reasoning_layer.solution_generator import SolutionGenerator

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Orchestrates reasoning components to provide explainability."""
    
    def __init__(self, rules_file: Optional[str] = None, custom_rules_file: Optional[str] = None):
        """
        Initialize reasoning engine with regulatory and custom rules.
        
        Args:
            rules_file: Path to enhanced-regulation-rules.json (regulatory rules)
            custom_rules_file: Path to custom_rules.json (generated/imported rules)
        """
        self.justifier = RuleJustifier(rules_file)
        self.analyzer = ElementFailureAnalyzer()
        self.generator = SolutionGenerator()
        
        # Load all rules (regulatory + custom)
        self.rules = {}
        self.regulatory_rules = {}
        self.custom_rules = {}
        
        # Load regulatory rules
        if rules_file and Path(rules_file).exists():
            self._load_rules_from_file(rules_file, rule_type='regulatory')
        
        # Load custom/generated rules
        if custom_rules_file and Path(custom_rules_file).exists():
            self._load_rules_from_file(custom_rules_file, rule_type='custom')
        
        logger.info(f"ReasoningEngine loaded {len(self.rules)} total rules")
        logger.info(f"  Regulatory: {len(self.regulatory_rules)}")
        logger.info(f"  Custom: {len(self.custom_rules)}")
    
    def _load_rules_from_file(self, rules_file: str, rule_type: str = 'regulatory'):
        """Load rules from a file and categorize them."""
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            rules_list = []
            
            # Handle different file structures
            if isinstance(rules_data, dict):
                if 'rules' in rules_data:
                    # Structure: {"rules": [...], "metadata": ...}
                    rules_list = rules_data.get('rules', [])
                else:
                    # Structure: {"rule_id": {...}, "rule_id": {...}}
                    first_value = next(iter(rules_data.values())) if rules_data else None
                    if isinstance(first_value, dict) and 'id' in first_value:
                        rules_list = list(rules_data.values())
                    elif isinstance(first_value, dict):
                        # Convert dict format to list
                        rules_list = [
                            {**rule_data, 'id': rule_id} 
                            for rule_id, rule_data in rules_data.items()
                        ]
            elif isinstance(rules_data, list):
                # Structure: [{"id": ..., ...}, ...]
                rules_list = rules_data
            
            # Process rules
            for rule in rules_list:
                if isinstance(rule, dict) and 'id' in rule:
                    rule_id = rule.get('id')
                    self.rules[rule_id] = rule
                    
                    if rule_type == 'regulatory':
                        self.regulatory_rules[rule_id] = rule
                    elif rule_type == 'custom':
                        self.custom_rules[rule_id] = rule
            
            logger.info(f"Loaded {len(rules_list)} {rule_type} rules from {rules_file}")
            if rules_list:
                logger.info(f"Sample {rule_type} rules: {[r.get('id') for r in rules_list[:3]]}")
        
        except Exception as e:
            logger.warning(f"Could not load {rule_type} rules from {rules_file}: {e}")
    
    def explain_rule(self, rule_id: str,
                    applicable_elements: Optional[List[str]] = None,
                    elements_checked: int = 0,
                    elements_passing: int = 0,
                    elements_failing: int = 0) -> Dict[str, Any]:
        """
        Explain WHY a rule exists.
        
        Args:
            rule_id: Which rule to explain
            applicable_elements: IFC types this rule applies to
            elements_checked: How many elements were checked
            elements_passing: How many passed
            elements_failing: How many failed
            
        Returns:
            Dict with rule explanation
        """
        if rule_id not in self.rules:
            logger.warning(f"Rule {rule_id} not found in loaded rules. Available rules: {list(self.rules.keys())}")
            return {"error": f"Rule {rule_id} not found. Available: {len(self.rules)} rules"}
        
        rule = self.rules[rule_id]
        
        explanation = self.justifier.generate_rule_explanation(
            rule,
            applicable_elements or [],
            elements_checked,
            elements_passing,
            elements_failing
        )
        
        return reasoning_result_to_dict(ReasoningResult(
            reasoning_type=ReasoningType.RULE_JUSTIFICATION,
            rule_explanations=[explanation],
            total_rules_analyzed=1
        ))
    
    def explain_failure(self, element_id: str, element_type: str,
                       element_name: Optional[str],
                       failed_rule_results: List[Dict]) -> Dict[str, Any]:
        """
        Explain WHY an element failed rules and HOW to fix it.
        
        Args:
            element_id: IFC element identifier
            element_type: Type like "IfcDoor", "IfcStair"
            element_name: Name in model
            failed_rule_results: List of dicts with:
                - rule: Rule dict
                - actual_value: What element has
                - required_value: What it should have
                - unit: Measurement unit
                - location: Optional location
                
        Returns:
            Dict with failure explanations and solutions
        """
        # Generate failure analysis for all failed rules
        explanation = self.analyzer.generate_element_explanation(
            element_id, element_type, element_name, failed_rule_results
        )
        
        # Generate solutions for each failure
        for analysis in explanation.analyses:
            rule_id = analysis.rule_id
            if rule_id in self.rules:
                rule = self.rules[rule_id]
                solution = self.generator.generate_solution(analysis, rule)
                explanation.solutions.append(solution)
        
        return reasoning_result_to_dict(ReasoningResult(
            reasoning_type=ReasoningType.FAILURE_ANALYSIS,
            element_explanations=[explanation],
            total_failures_analyzed=len(explanation.analyses),
            total_solutions_provided=len(explanation.solutions)
        ))
    
    def explain_compliance_check(self, compliance_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add reasoning to compliance check results.
        
        Args:
            compliance_results: Results from UnifiedComplianceEngine.check_graph()
            
        Returns:
            Compliance results with added reasoning explanations
        """
        results_with_reasoning = compliance_results.copy()
        
        # Group failures by element
        failures_by_element = {}
        for result in compliance_results.get('results', []):
            if not result.get('passed'):
                element_guid = result.get('element_guid')
                if element_guid not in failures_by_element:
                    failures_by_element[element_guid] = {
                        'element_type': result.get('element_type'),
                        'element_name': result.get('element_name'),
                        'failures': []
                    }
                
                failures_by_element[element_guid]['failures'].append({
                    'rule_id': result.get('rule_id'),
                    'rule_name': result.get('rule_name'),
                    'explanation': result.get('explanation')
                })
        
        # Add reasoning to failing elements
        element_explanations = []
        for element_guid, element_info in failures_by_element.items():
            failures = []
            for failure in element_info['failures']:
                rule_id = failure['rule_id']
                if rule_id in self.rules:
                    rule = self.rules[rule_id]
                    # Note: In real scenario, would need actual vs required values
                    # For now, using explanation as proxy
                    failures.append({
                        'rule': rule,
                        'actual_value': 'See rule check for details',
                        'required_value': rule.get('value', 'See rule check'),
                        'unit': rule.get('unit', ''),
                        'location': None
                    })
            
            if failures:
                element_explanation = self.analyzer.generate_element_explanation(
                    element_guid,
                    element_info['element_type'],
                    element_info.get('element_name'),
                    failures
                )
                element_explanations.append(element_explanation)
        
        # Add to results
        if element_explanations:
            results_with_reasoning['element_reasoning'] = [
                reasoning_result_to_dict(ReasoningResult(
                    reasoning_type=ReasoningType.FAILURE_ANALYSIS,
                    element_explanations=[exp],
                    total_failures_analyzed=exp.total_failures
                ))
                for exp in element_explanations
            ]
        
        return results_with_reasoning
    
    def get_rule_count_by_standard(self) -> Dict[str, int]:
        """Get count of rules by regulatory standard."""
        counts = {}
        for rule_key, rule_value in self.rules.items():
            # Handle both cases: rule_value is a dict or rule_key is the rule dict
            rule = rule_value if isinstance(rule_value, dict) else rule_key
            if not isinstance(rule, dict):
                continue
            provenance = rule.get('provenance', {})
            standard = provenance.get('regulation', 'Unknown')
            counts[standard] = counts.get(standard, 0) + 1
        return counts
    
    def get_rules_by_element_type(self, element_type: str) -> List[Dict]:
        """Get all rules applicable to an element type."""
        applicable = []
        for rule_key, rule_value in self.rules.items():
            # Handle both cases
            rule = rule_value if isinstance(rule_value, dict) else rule_key
            if not isinstance(rule, dict):
                continue
            
            # Handle different target formats
            target = rule.get('target', '')
            if isinstance(target, dict):
                # New format: {"ifc_class": "IfcDoor", ...}
                target_class = target.get('ifc_class', '')
                if element_type in target_class or target_class == 'all':
                    applicable.append(rule)
            else:
                # Old format: "IfcDoor" or similar
                if element_type in str(target) or str(target).lower() == 'all':
                    applicable.append(rule)
        
        return applicable
    
    def validate_reasoning_layer(self) -> Dict[str, Any]:
        """Validate reasoning layer configuration."""
        validation = {
            "rules_loaded": len(self.rules) > 0,
            "total_rules": len(self.rules),
            "standards": self.get_rule_count_by_standard(),
            "components": {
                "justifier": self.justifier is not None,
                "analyzer": self.analyzer is not None,
                "generator": self.generator is not None
            }
        }
        return validation
