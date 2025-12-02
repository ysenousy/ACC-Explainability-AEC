"""
Failure Explainer - Explains why compliance rules failed.

Provides detailed, human-readable explanations of compliance failures
with context from both the rule definition and the actual element data.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from reasoning_layer.models import (
    FailureExplanation, 
    FailureContext,
    RegulatoryReference,
    SeverityLevel
)
from reasoning_layer.config import BaseReasoningEngine

logger = logging.getLogger(__name__)


class FailureExplainer(BaseReasoningEngine):
    """Explains why elements failed compliance checks."""
    
    def explain_failure(self, 
                       failure: Dict[str, Any],
                       rule: Dict[str, Any]) -> FailureExplanation:
        """
        Generate detailed explanation for a compliance failure.
        
        Args:
            failure: Failure data from compliance check
            rule: Rule definition that was violated
            
        Returns:
            FailureExplanation with detailed analysis
        """
        # Extract failure context
        context = FailureContext(
            element_id=failure.get('element_id', failure.get('element_guid', 'unknown')),
            element_type=failure.get('element_type', 'unknown'),
            element_name=failure.get('element_name', failure.get('element_id', 'unknown')),
            actual_value=failure.get('actual_value'),
            required_value=failure.get('required_value'),
            unit=failure.get('unit', ''),
            properties=failure.get('properties', {})
        )
        
        # Extract regulatory reference
        provenance = rule.get('provenance', {})
        ref = RegulatoryReference(
            regulation=provenance.get('regulation', 'Unknown'),
            section=provenance.get('section', 'Unknown'),
            jurisdiction=provenance.get('jurisdiction', 'Unknown'),
            source_link=provenance.get('source_link')
        )
        
        # Determine failure type
        failure_type = self._classify_failure(failure, rule)
        
        # Generate explanations
        short_exp = self._generate_short_explanation(failure, rule, context, failure_type)
        detailed_exp = self._generate_detailed_explanation(failure, rule, context, failure_type)
        
        # Affected property
        affected_prop = self._identify_affected_property(failure, rule)
        
        # Severity
        severity = SeverityLevel(failure.get('severity', 'WARNING'))
        
        return FailureExplanation(
            rule_id=rule.get('id', 'unknown'),
            rule_name=rule.get('name', 'Unknown Rule'),
            failure_type=failure_type,
            short_explanation=short_exp,
            detailed_explanation=detailed_exp,
            context=context,
            regulatory_reference=ref,
            affected_property=affected_prop,
            severity=severity
        )
    
    def _classify_failure(self, failure: Dict[str, Any], rule: Dict[str, Any]) -> str:
        """Classify the type of failure."""
        # Check if it's a missing property
        if failure.get('actual_value') is None:
            return "missing_property"
        
        # Check if it's a dimensional violation
        if 'width' in str(rule.get('condition', '')).lower() or \
           'height' in str(rule.get('condition', '')).lower() or \
           'area' in str(rule.get('condition', '')).lower():
            return "dimension_violation"
        
        # Check if it's a value out of range
        if 'range' in str(rule.get('condition', '')).lower():
            return "range_violation"
        
        # Default to value violation
        return "value_violation"
    
    def _generate_short_explanation(self, failure: Dict[str, Any], 
                                    rule: Dict[str, Any],
                                    context: FailureContext,
                                    failure_type: str) -> str:
        """Generate concise explanation."""
        template_map = {
            'missing_property': f"{context.element_name} ({context.element_type}) is missing required property: {context.affected_property}",
            'dimension_violation': f"{context.element_name} has insufficient dimension. Found: {context.actual_value}{context.unit}, Required: {context.required_value}{context.unit}",
            'range_violation': f"{context.element_name} value is outside acceptable range. Found: {context.actual_value}, Required: {context.required_value}",
            'value_violation': f"{context.element_name} does not meet rule: {rule.get('name', 'Unknown Rule')}"
        }
        
        return template_map.get(failure_type, 
                              f"{context.element_name} failed rule: {rule.get('name')}")
    
    def _generate_detailed_explanation(self, failure: Dict[str, Any],
                                       rule: Dict[str, Any],
                                       context: FailureContext,
                                       failure_type: str) -> str:
        """Generate detailed explanation with context."""
        explanation = rule.get('explanation', {})
        rule_description = explanation.get('long', explanation.get('short', rule.get('description', '')))
        
        # Build detailed explanation
        parts = [
            f"Rule: {rule.get('name', 'Unknown')}",
            f"Regulation: {rule.get('provenance', {}).get('regulation', 'Unknown')}",
            f"",
            f"Element: {context.element_name} ({context.element_type})",
            f"Element ID: {context.element_id}",
            f"",
            f"Description: {rule_description}",
            f"",
        ]
        
        # Add failure-specific details
        if context.actual_value is not None and context.required_value is not None:
            if isinstance(context.actual_value, (int, float)) and isinstance(context.required_value, (int, float)):
                difference = context.required_value - context.actual_value
                parts.append(f"Current Value: {context.actual_value}{context.unit}")
                parts.append(f"Required Value: {context.required_value}{context.unit}")
                parts.append(f"Shortfall: {difference}{context.unit}")
            else:
                parts.append(f"Current Value: {context.actual_value}")
                parts.append(f"Required Value: {context.required_value}")
        
        return "\n".join(parts)
    
    def _identify_affected_property(self, failure: Dict[str, Any], 
                                   rule: Dict[str, Any]) -> str:
        """Identify which property is affected."""
        # Check failure explanation
        if 'property' in failure:
            return failure['property']
        
        # Check rule parameters
        params = rule.get('parameters', {})
        if params and isinstance(params, dict):
            # Return first parameter as affected property
            for param_key in params.keys():
                if param_key not in ['min', 'max', 'threshold']:
                    return param_key
        
        # Check condition for clues
        condition = rule.get('condition', '')
        if 'width' in condition.lower():
            return 'width'
        elif 'height' in condition.lower():
            return 'height'
        elif 'area' in condition.lower():
            return 'area'
        
        return 'unknown'
    
    def explain_failures(self, failures: List[Dict[str, Any]], 
                        rules: Dict[str, Dict[str, Any]]) -> List[FailureExplanation]:
        """Explain multiple failures."""
        explanations = []
        
        for failure in failures:
            rule_id = failure.get('rule_id', 'unknown')
            rule = rules.get(rule_id, {})
            
            if not rule:
                logger.warning(f"Rule {rule_id} not found in rules database")
                continue
            
            explanation = self.explain_failure(failure, rule)
            explanations.append(explanation)
        
        return explanations
