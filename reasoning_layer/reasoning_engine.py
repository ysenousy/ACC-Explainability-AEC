"""
Reasoning Engine - Orchestrates all reasoning layer components.

Provides unified interface to failure explanation, impact analysis,
and recommendation generation for compliance failures.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from reasoning_layer.models import ReasoningResult, SeverityLevel
from reasoning_layer.failure_explainer import FailureExplainer
from reasoning_layer.impact_analyzer import ImpactAnalyzer
from reasoning_layer.recommendation_engine import RecommendationEngine
from reasoning_layer.config import ReasoningConfig

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Main reasoning engine orchestrating all reasoning components.
    
    Coordinates:
    - FailureExplainer: Why did this fail?
    - ImpactAnalyzer: How many elements affected?
    - RecommendationEngine: What should we do?
    """
    
    def __init__(self, rules_file: Optional[str] = None,
                 custom_rules_file: Optional[str] = None,
                 load_from_version_manager: bool = False):
        """
        Initialize reasoning engine.
        
        Args:
            rules_file: Path to regulatory rules JSON file
            custom_rules_file: Path to custom rules JSON file
            load_from_version_manager: If True, load latest regulatory rules from RulesVersionManager
        """
        self.config = ReasoningConfig()
        self.failure_explainer = FailureExplainer()
        self.impact_analyzer = ImpactAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        
        # Load rules
        self.regulatory_rules = {}
        self.custom_rules = {}
        self.rules = {}
        
        # Load from version manager if requested
        if load_from_version_manager:
            self.load_rules_from_version_manager()
        
        if rules_file:
            self.load_rules_from_file(rules_file, rule_type='regulatory')
        if custom_rules_file:
            self.load_rules_from_file(custom_rules_file, rule_type='custom')
    
    def load_rules_from_version_manager(self) -> Dict[str, Any]:
        """Load latest regulatory rules from RulesVersionManager."""
        try:
            from pathlib import Path
            from backend.rules_version_manager import RulesVersionManager
            
            rules_config_dir = Path(__file__).parent.parent / "rules_config"
            version_manager = RulesVersionManager(str(rules_config_dir))
            
            rules_data, _ = version_manager.load_rules()
            rules_list = rules_data.get('rules', [])
            
            # Store rules by ID
            rules_dict = {}
            for rule in rules_list:
                rule_id = rule.get('id')
                if rule_id:
                    rules_dict[rule_id] = rule
            
            # Store as regulatory rules
            self.regulatory_rules.update(rules_dict)
            self.rules.update(rules_dict)
            
            logger.info(f"Loaded {len(rules_dict)} regulatory rules from RulesVersionManager (v{version_manager.get_current_version_id()})")
            
            return {
                'success': True,
                'rules_loaded': len(rules_dict),
                'source': 'RulesVersionManager',
                'version': version_manager.get_current_version_id()
            }
        
        except Exception as e:
            logger.error(f"Error loading rules from RulesVersionManager: {e}")
            return {
                'success': False,
                'error': str(e),
                'rules_loaded': 0
            }
    
    def load_rules_from_file(self, file_path: str, rule_type: str = 'regulatory') -> Dict[str, Any]:
        """Load rules from JSON file."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.warning(f"Rules file not found: {file_path}")
                return {'success': False, 'error': f'File not found: {file_path}', 'rules_loaded': 0}
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract rules list
            rules_list = []
            if isinstance(data, dict) and 'rules' in data:
                rules_list = data.get('rules', [])
            elif isinstance(data, list):
                rules_list = data
            
            # Store rules by ID
            rules_dict = {}
            for rule in rules_list:
                rule_id = rule.get('id')
                if rule_id:
                    rules_dict[rule_id] = rule
            
            # Store by type
            if rule_type == 'regulatory':
                self.regulatory_rules.update(rules_dict)
            elif rule_type == 'custom':
                self.custom_rules.update(rules_dict)
            
            # Update combined rules
            self.rules.update(rules_dict)
            
            logger.info(f"Loaded {len(rules_dict)} {rule_type} rules from {file_path}")
            
            return {
                'success': True,
                'rules_loaded': len(rules_dict),
                'file_path': file_path,
                'rule_type': rule_type
            }
        
        except Exception as e:
            logger.error(f"Error loading rules from {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'rules_loaded': 0
            }
    
    def analyze_failures(self, failures: List[Dict[str, Any]], 
                        total_elements: int) -> List[ReasoningResult]:
        """
        Analyze a list of compliance failures comprehensively.
        
        Args:
            failures: List of failures from compliance check
            total_elements: Total elements evaluated
            
        Returns:
            List of ReasoningResult objects with full analysis
        """
        results = []
        
        # Group failures by element
        failures_by_element = self._group_failures_by_element(failures)
        
        for element_id, element_failures in failures_by_element.items():
            # Get element info from first failure
            first_failure = element_failures[0]
            element_type = first_failure.get('element_type', 'Unknown')
            element_name = first_failure.get('element_name', element_id)
            
            # Explain failures
            explanations = []
            for failure in element_failures:
                rule_id = failure.get('rule_id')
                rule = self.rules.get(rule_id, {})
                
                if not rule:
                    logger.debug(f"Rule {rule_id} not found")
                    continue
                
                explanation = self.failure_explainer.explain_failure(failure, rule)
                explanations.append(explanation)
            
            # Analyze impact (for this element's failures)
            impact = self.impact_analyzer.analyze_impact(
                element_failures, 
                total_elements
            )
            
            # Generate recommendations (for all failures of this type)
            recommendations = self.recommendation_engine.generate_recommendations(
                element_failures
            )
            
            # Create reasoning result
            result = ReasoningResult(
                element_id=element_id,
                element_type=element_type,
                element_name=element_name,
                failure_explanations=explanations,
                impact_metrics=impact,
                recommendations=recommendations,
                analysis_timestamp=datetime.now().isoformat(),
                total_failed_rules=len(explanations)
            )
            
            results.append(result)
        
        logger.info(f"Analyzed {len(results)} elements with failures")
        return results
    
    def analyze_single_failure(self, failure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single failure in detail.
        
        Args:
            failure: Single failure data
            
        Returns:
            Dictionary with explanation, impact, and recommendations
        """
        rule_id = failure.get('rule_id')
        rule = self.rules.get(rule_id, {})
        
        if not rule:
            return {
                'success': False,
                'error': f'Rule {rule_id} not found in knowledge base'
            }
        
        # Explain
        explanation = self.failure_explainer.explain_failure(failure, rule)
        
        # Recommend (single failure)
        recommendations = self.recommendation_engine.generate_recommendations([failure])
        
        return {
            'success': True,
            'failure': failure,
            'explanation': explanation,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_failure_summary(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics of failures."""
        return {
            'total_failures': len(failures),
            'by_severity': self.impact_analyzer.get_severity_distribution(failures),
            'by_element_type': self.impact_analyzer.get_failure_distribution(failures),
            'by_rule': self._count_failures_by_rule(failures),
            'most_affected_elements': dict(
                self.impact_analyzer.get_most_affected_elements(failures, top_n=5)
            ),
            'most_common_rules': dict(
                self.impact_analyzer.get_most_common_rules(failures, top_n=5)
            )
        }
    
    def get_quick_recommendations(self, failures: List[Dict[str, Any]], 
                                 max_count: int = 5) -> List[Dict[str, Any]]:
        """Get highest priority recommendations."""
        recommendations = self.recommendation_engine.generate_recommendations(failures)
        priority_recs = self.recommendation_engine.get_highest_priority_recommendations(
            recommendations,
            max_count=max_count
        )
        
        return [
            {
                'title': rec.title,
                'description': rec.description,
                'effort': rec.estimated_effort.value,
                'cost': rec.estimated_cost,
                'steps': rec.implementation_steps,
                'affected_elements': rec.affected_elements
            }
            for rec in priority_recs
        ]
    
    def _group_failures_by_element(self, failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group failures by element ID."""
        grouped = {}
        
        for failure in failures:
            element_id = failure.get('element_id', failure.get('element_guid', 'unknown'))
            if element_id not in grouped:
                grouped[element_id] = []
            grouped[element_id].append(failure)
        
        return grouped
    
    def _count_failures_by_rule(self, failures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count failures by rule ID."""
        counts = {}
        
        for failure in failures:
            rule_id = failure.get('rule_id', 'unknown')
            counts[rule_id] = counts.get(rule_id, 0) + 1
        
        return counts
    
    def reload_configuration(self):
        """Reload configuration from disk."""
        self.config.reload()
        logger.info("Reasoning Engine configuration reloaded")
