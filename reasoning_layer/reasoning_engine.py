"""
Reasoning Engine

Orchestrates the reasoning layer components (justifier, analyzer, solution generator)
to provide complete explanations for compliance checking.

ARCHITECTURE OVERVIEW:
======================

The ACC-Explainability system follows a three-layer architecture:

1. RULE LAYER (Foundation)
   - Loads rules from catalogue (regulatory + custom)
   - Validates rule syntax and structure
   - Stores rules in memory for reference
   - Does NOT execute compliance checks

2. COMPLIANCE CHECK LAYER (Calculation - CACHED)
   - Executes rules against IFC elements
   - Calculates pass/fail status for each rule
   - Collects metrics (passed, failed, unknown)
   - STORES RESULTS (no recalculation)
   - Location: backend/unified_compliance_engine.py

3. REASONING LAYER (Explanation - THIS MODULE)
   - READS cached compliance results (NO recalculation)
   - Explains WHY each rule passed
   - Explains WHY each rule failed
   - Provides detailed justifications
   - Generates solutions for failures
   - Enriches results with reasoning

DEPENDENCY CHAIN:
=================
Rule Layer (Foundation)
    ↓ (provides rules)
Compliance Check Layer (uses rules, CACHES results)
    ↓ (provides cached results)
Reasoning Layer (uses cached results, adds explanations)

KEY PRINCIPLE:
The Reasoning Layer is a read-only layer that:
✗ Does NOT re-execute compliance checks
✗ Does NOT modify rule definitions
✗ Does NOT recalculate pass/fail status
✓ Only adds explanations and justifications
✓ Only reads from cached compliance results
✓ Only provides "why" information

When a compliance check is performed:
1. Rule Layer provides the rules
2. Compliance Check Layer executes and caches results
3. Reasoning Layer reads cached results and adds reasoning
4. Frontend receives enriched data with full context
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
    """
    Reasoning Layer Engine - Provides Explainability WITHOUT Recalculation
    
    CRITICAL: This engine reads from cached compliance results only.
    It does NOT recalculate compliance checks or modify rule definitions.
    
    Dependencies:
    - Requires Rule Layer to provide rules (loaded in __init__)
    - Requires Compliance Check Layer to execute checks and cache results
    - Reads from cached results in explain_compliance_check()
    
    Responsibilities:
    1. Load all rules (regulatory + custom) for reference
    2. Provide rule justifications (WHY rules exist)
    3. Analyze cached compliance failures (WHY elements failed)
    4. Generate solutions (HOW to fix failures)
    5. Enrich compliance results with explanations
    """
    
    def __init__(self, rules_file: Optional[str] = None, custom_rules_file: Optional[str] = None):
        """
        Initialize reasoning engine WITHOUT loading rules at startup.
        
        Rules are loaded on-demand when user imports/selects them via load_rules_from_file().
        This allows flexible rule management with multiple JSON files and regulations.
        
        Args:
            rules_file: (Deprecated - ignored) Path to regulatory rules JSON
            custom_rules_file: (Deprecated - ignored) Path to custom rules JSON
            
        NOTE: Use load_rules_from_file() to load rules when user requests them.
        """
        self.justifier = RuleJustifier(None)  # Initialize without rules
        self.analyzer = ElementFailureAnalyzer()
        self.generator = SolutionGenerator()
        
        # Initialize empty rule storage
        self.rules = {}
        self.regulatory_rules = {}
        self.custom_rules = {}
        self.loaded_files = {}  # Track which files have been loaded
        
        logger.info("[REASONING LAYER] Initialized without rules - waiting for user to import/select rules")
    
    def load_rules_from_file(self, rules_file: str, rule_type: str = 'regulatory') -> Dict[str, Any]:
        """
        Load rules on-demand when user imports or selects them.
        
        This is called when:
        - User imports a regulation file
        - User selects a regulation to use
        - Frontend requests to load specific rules
        
        Args:
            rules_file: Path to rules JSON file
            rule_type: 'regulatory' or 'custom'
            
        Returns:
            Dict with loading status and loaded rules count
        """
        try:
            result = self._load_rules_from_file(rules_file, rule_type=rule_type)
            
            # Track loaded files
            self.loaded_files[rule_type] = {
                'path': rules_file,
                'count': result['count'],
                'samples': result['samples']
            }
            
            logger.info(f"[REASONING LAYER] User loaded {rule_type} rules from: {rules_file}")
            return {
                'success': True,
                'rule_type': rule_type,
                'rules_loaded': result['count'],
                'sample_rules': result['samples']
            }
        except Exception as e:
            logger.error(f"[REASONING LAYER] Failed to load {rule_type} rules from {rules_file}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _load_rules_from_file(self, rules_file: str, rule_type: str = 'regulatory') -> Dict[str, Any]:
        """
        Internal method to load rules from a file.
        
        Args:
            rules_file: Path to rules JSON file
            rule_type: 'regulatory' or 'custom'
            
        Returns:
            Dict with count and sample rules
        """
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
            
            samples = [r.get('id') for r in rules_list[:3]]
            logger.info(f"[REASONING LAYER] Loaded {len(rules_list)} {rule_type} rules")
            logger.info(f"[REASONING LAYER] Sample {rule_type} rules: {samples}")
            
            return {
                'count': len(rules_list),
                'samples': samples
            }
        
        except Exception as e:
            logger.error(f"[REASONING LAYER] Could not load {rule_type} rules from {rules_file}: {e}")
            raise
    
    
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
        CACHED RESULT ENRICHMENT - Add reasoning to compliance check results.
        
        CRITICAL BEHAVIOR:
        This method reads from CACHED compliance results provided by the Compliance Check Layer.
        It does NOT re-execute compliance checks or recalculate pass/fail status.
        
        Inputs (from Compliance Check Layer):
            compliance_results: Pre-calculated results from UnifiedComplianceEngine.check_graph()
            Contains:
            - results: List of individual rule check results (ALREADY CALCULATED)
            - summary: {total, passed, failed, unknown} (ALREADY CALCULATED)
            - Each result includes:
              - element_guid, element_type, element_name
              - rule_id, rule_name
              - passed: boolean (ALREADY DETERMINED)
              - explanation: string (WHY it passed/failed)
            
        Processing (This Layer Only):
        1. Read the pre-calculated results
        2. Group failures by element (organization only, no recalculation)
        3. Extract failure details from cached results
        4. Generate explanations for each failure
        5. Generate solutions for each failure
        6. Attach reasoning to results
        
        Output:
            compliance_results with added reasoning layer:
            - element_reasoning: Detailed explanations of why failures occurred
            - Each explanation includes WHY it failed and HOW to fix it
            
        Returns:
            Enriched compliance results with reasoning explanations
        """
        # Make a copy to avoid modifying the original cached results
        results_with_reasoning = compliance_results.copy()
        
        logger.info(f"[REASONING LAYER] Enriching cached compliance results with explanations")
        logger.info(f"[REASONING LAYER] Processing {len(compliance_results.get('results', []))} cached check results")
        
        # STEP 1: Group failures by element (from cached results - NO recalculation)
        # This is purely organizational - we're reading pre-calculated pass/fail status
        failures_by_element = {}
        for result in compliance_results.get('results', []):
            # Read the pre-calculated passed status
            passed = result.get('passed')
            
            # Only process failures (passed=False)
            if not passed:
                element_guid = result.get('element_guid')
                if element_guid not in failures_by_element:
                    failures_by_element[element_guid] = {
                        'element_type': result.get('element_type'),
                        'element_name': result.get('element_name'),
                        'failures': []
                    }
                
                # Collect failure information from cached result
                failures_by_element[element_guid]['failures'].append({
                    'rule_id': result.get('rule_id'),
                    'rule_name': result.get('rule_name'),
                    'explanation': result.get('explanation'),  # Already calculated
                    'status': result.get('status')  # PASSED, FAILED, or UNKNOWN
                })
        
        logger.info(f"[REASONING LAYER] Found {len(failures_by_element)} elements with failures (from cache)")
        
        # STEP 2: Generate explanations for each failure (reading only, no recalculation)
        element_explanations = []
        for element_guid, element_info in failures_by_element.items():
            failures = []
            
            # Process each failure for this element
            for failure in element_info['failures']:
                rule_id = failure['rule_id']
                
                # Look up rule definition from Rule Layer
                if rule_id in self.rules:
                    rule = self.rules[rule_id]
                    
                    # Prepare failure analysis using cached data + rule definition
                    # The actual values come from compliance check (cached)
                    failures.append({
                        'rule': rule,
                        'rule_id': rule_id,
                        'rule_name': failure['rule_name'],
                        'cached_explanation': failure['explanation'],  # Why it failed (cached)
                        'status': failure['status'],  # PASSED, FAILED, or UNKNOWN
                        # Note: actual_value/required_value come from cached explanation
                        'actual_value': 'See cached result for details',
                        'required_value': rule.get('value', 'See rule definition'),
                        'unit': rule.get('unit', ''),
                        'location': None
                    })
            
            # Generate reasoning only if there are failures
            if failures:
                logger.info(f"[REASONING LAYER] Generating explanations for element {element_guid} ({len(failures)} failures)")
                
                # Use cached failure data to generate element explanation
                element_explanation = self.analyzer.generate_element_explanation(
                    element_guid,
                    element_info['element_type'],
                    element_info.get('element_name'),
                    failures
                )
                
                # Generate solutions for each failure
                for analysis in element_explanation.analyses:
                    rule_id = analysis.rule_id
                    if rule_id in self.rules:
                        rule = self.rules[rule_id]
                        solution = self.generator.generate_solution(analysis, rule)
                        element_explanation.solutions.append(solution)
                
                element_explanations.append(element_explanation)
        
        # STEP 3: Attach reasoning to results
        if element_explanations:
            logger.info(f"[REASONING LAYER] Adding reasoning for {len(element_explanations)} elements")
            results_with_reasoning['element_reasoning'] = [
                reasoning_result_to_dict(ReasoningResult(
                    reasoning_type=ReasoningType.FAILURE_ANALYSIS,
                    element_explanations=[exp],
                    total_failures_analyzed=exp.total_failures
                ))
                for exp in element_explanations
            ]
        
        logger.info(f"[REASONING LAYER] Enrichment complete - added reasoning for {len(element_explanations)} elements")
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
