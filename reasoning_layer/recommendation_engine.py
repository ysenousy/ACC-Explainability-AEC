"""
Recommendation Engine - Configuration-driven recommendation system.

Generates actionable recommendations based on failure analysis using
template definitions from configuration files. No hard-coded logic per rule type.
"""

import logging
from typing import Dict, List, Any, Optional
import json

from reasoning_layer.models import Recommendation, RecommendationSet, RecommendationEffort
from reasoning_layer.config import BaseReasoningEngine

logger = logging.getLogger(__name__)


class RecommendationEngine(BaseReasoningEngine):
    """Generates recommendations from failure analysis using templates."""
    
    def generate_recommendations(self, failures: List[Dict[str, Any]]) -> RecommendationSet:
        """
        Generate tiered recommendations for fixing failures.
        
        Args:
            failures: List of compliance failures
            
        Returns:
            RecommendationSet with quick, medium, comprehensive, and systemic fixes
        """
        recommendation_set = RecommendationSet()
        
        # Group failures by rule for easier processing
        failures_by_rule = self._group_by_rule(failures)
        
        for rule_id, rule_failures in failures_by_rule.items():
            # Get templates for this rule
            templates = self.config.get_templates_for_rule(rule_id)
            
            if not templates:
                logger.debug(f"No templates found for rule {rule_id}, using defaults")
                templates = self._get_default_templates(rule_id, rule_failures)
            
            # Generate recommendations at each effort level
            quick = self._generate_quick_fix(rule_id, rule_failures, templates)
            medium = self._generate_medium_fix(rule_id, rule_failures, templates)
            comprehensive = self._generate_comprehensive_fix(rule_id, rule_failures, templates)
            systemic = self._generate_systemic_fix(rule_id, rule_failures, templates)
            
            # Add to appropriate lists
            if quick:
                recommendation_set.quick_fixes.append(quick)
            if medium:
                recommendation_set.medium_fixes.append(medium)
            if comprehensive:
                recommendation_set.comprehensive_fixes.append(comprehensive)
            if systemic:
                recommendation_set.systemic_fixes.append(systemic)
        
        return recommendation_set
    
    def _group_by_rule(self, failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group failures by rule ID."""
        grouped = {}
        
        for failure in failures:
            rule_id = failure.get('rule_id', 'unknown')
            if rule_id not in grouped:
                grouped[rule_id] = []
            grouped[rule_id].append(failure)
        
        return grouped
    
    def _generate_quick_fix(self, rule_id: str, failures: List[Dict[str, Any]], 
                           templates: Dict[str, Any]) -> Optional[Recommendation]:
        """Generate quick fix recommendation."""
        quick_template = templates.get('quick_fix', {})
        
        if not quick_template:
            return None
        
        # Extract context from first failure
        context = self._extract_context(failures[0]) if failures else {}
        context['failure_count'] = len(failures)
        
        # Format template with actual values
        title = self._format_template(
            quick_template.get('title', 'Quick Fix'),
            context
        )
        
        description = self._format_template(
            quick_template.get('description', ''),
            context
        )
        
        steps = quick_template.get('steps', [])
        formatted_steps = [self._format_template(step, context) for step in steps]
        
        return Recommendation(
            title=title,
            description=description,
            implementation_steps=formatted_steps,
            estimated_effort=RecommendationEffort.LOW,
            affected_elements=len(failures),
            estimated_cost=quick_template.get('cost'),
            regulatory_pathway=quick_template.get('regulatory_pathway')
        )
    
    def _generate_medium_fix(self, rule_id: str, failures: List[Dict[str, Any]],
                            templates: Dict[str, Any]) -> Optional[Recommendation]:
        """Generate medium effort recommendation."""
        medium_template = templates.get('medium_fix', {})
        
        if not medium_template:
            return None
        
        context = self._extract_context(failures[0]) if failures else {}
        context['failure_count'] = len(failures)
        
        title = self._format_template(
            medium_template.get('title', 'Standard Fix'),
            context
        )
        
        description = self._format_template(
            medium_template.get('description', ''),
            context
        )
        
        steps = medium_template.get('steps', [])
        formatted_steps = [self._format_template(step, context) for step in steps]
        
        return Recommendation(
            title=title,
            description=description,
            implementation_steps=formatted_steps,
            estimated_effort=RecommendationEffort.MEDIUM,
            affected_elements=len(failures),
            estimated_cost=medium_template.get('cost'),
            regulatory_pathway=medium_template.get('regulatory_pathway')
        )
    
    def _generate_comprehensive_fix(self, rule_id: str, failures: List[Dict[str, Any]],
                                   templates: Dict[str, Any]) -> Optional[Recommendation]:
        """Generate comprehensive solution."""
        comprehensive_template = templates.get('comprehensive_fix', {})
        
        if not comprehensive_template:
            return None
        
        context = self._extract_context(failures[0]) if failures else {}
        context['failure_count'] = len(failures)
        
        title = self._format_template(
            comprehensive_template.get('title', 'Comprehensive Solution'),
            context
        )
        
        description = self._format_template(
            comprehensive_template.get('description', ''),
            context
        )
        
        steps = comprehensive_template.get('steps', [])
        formatted_steps = [self._format_template(step, context) for step in steps]
        
        return Recommendation(
            title=title,
            description=description,
            implementation_steps=formatted_steps,
            estimated_effort=RecommendationEffort.HIGH,
            affected_elements=len(failures),
            estimated_cost=comprehensive_template.get('cost'),
            regulatory_pathway=comprehensive_template.get('regulatory_pathway')
        )
    
    def _generate_systemic_fix(self, rule_id: str, failures: List[Dict[str, Any]],
                              templates: Dict[str, Any]) -> Optional[Recommendation]:
        """Generate systemic fix for root cause."""
        systemic_template = templates.get('systemic_fix', {})
        
        if not systemic_template:
            return None
        
        context = self._extract_context(failures[0]) if failures else {}
        context['failure_count'] = len(failures)
        
        # Only show systemic fix if multiple elements affected
        if context['failure_count'] < 3:
            return None
        
        title = self._format_template(
            systemic_template.get('title', 'Systemic Solution'),
            context
        )
        
        description = self._format_template(
            systemic_template.get('description', ''),
            context
        )
        
        steps = systemic_template.get('steps', [])
        formatted_steps = [self._format_template(step, context) for step in steps]
        
        return Recommendation(
            title=title,
            description=description,
            implementation_steps=formatted_steps,
            estimated_effort=RecommendationEffort.HIGH,
            affected_elements=len(failures),
            estimated_cost=systemic_template.get('cost'),
            regulatory_pathway=systemic_template.get('regulatory_pathway')
        )
    
    def _get_default_templates(self, rule_id: str, 
                              failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate default templates for rules without specific templates."""
        context = self._extract_context(failures[0]) if failures else {}
        
        return {
            'quick_fix': {
                'title': f'Adjust {context.get("element_type", "element")}',
                'description': f'Modify {len(failures)} element(s) to meet rule requirements',
                'steps': [
                    f'Identify all {context.get("element_type", "elements")} that fail this rule',
                    f'Modify each element to meet minimum/maximum requirements',
                    f'Verify changes in model'
                ],
                'cost': '$500-$2,000'
            },
            'medium_fix': {
                'title': f'Redesign {context.get("element_type", "element")} Configuration',
                'description': f'Systematic redesign of {len(failures)} element(s)',
                'steps': [
                    'Analyze current configuration',
                    'Design compliant alternative',
                    'Implement changes across affected elements',
                    'Coordinate with related systems'
                ],
                'cost': '$2,000-$5,000'
            },
            'comprehensive_fix': {
                'title': f'Complete {context.get("element_type", "element")} Redesign',
                'description': f'Full architectural redesign to ensure compliance',
                'steps': [
                    'Conduct detailed code review',
                    'Design comprehensive solution',
                    'Implement across entire building',
                    'Perform full compliance verification'
                ],
                'cost': '$5,000-$15,000'
            }
        }
    
    def get_highest_priority_recommendations(self, 
                                            recommendation_set: RecommendationSet,
                                            max_count: int = 5) -> List[Recommendation]:
        """Get highest priority recommendations (quick fixes first, then medium)."""
        priority_recs = []
        
        # Add quick fixes (highest priority, easiest to implement)
        priority_recs.extend(recommendation_set.quick_fixes[:max_count])
        
        # Add medium fixes if space remains
        remaining = max_count - len(priority_recs)
        if remaining > 0:
            priority_recs.extend(recommendation_set.medium_fixes[:remaining])
        
        return priority_recs
