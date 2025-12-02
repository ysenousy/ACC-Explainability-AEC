"""
Impact Analyzer - Quantifies the scope and severity of compliance failures.

Analyzes failure distribution, affected elements, cost estimates, and
provides metrics for understanding the breadth of compliance issues.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict

from reasoning_layer.models import ImpactMetrics, SeverityLevel
from reasoning_layer.config import BaseReasoningEngine

logger = logging.getLogger(__name__)


class ImpactAnalyzer(BaseReasoningEngine):
    """Analyzes impact of compliance failures."""
    
    def analyze_impact(self, failures: List[Dict[str, Any]], 
                      total_elements: int) -> ImpactMetrics:
        """
        Analyze the impact of failures across the building.
        
        Args:
            failures: List of compliance failures
            total_elements: Total number of elements evaluated
            
        Returns:
            ImpactMetrics with detailed impact analysis
        """
        # Count affected elements by type
        affected_elements = set()
        affected_by_type = Counter()
        failure_by_severity = Counter()
        
        for failure in failures:
            element_id = failure.get('element_id', failure.get('element_guid'))
            if element_id:
                affected_elements.add(element_id)
                element_type = failure.get('element_type', 'Unknown')
                affected_by_type[element_type] += 1
            
            severity = failure.get('severity', 'WARNING')
            failure_by_severity[severity] += 1
        
        # Calculate percentages
        total_affected = len(affected_elements)
        percentage = (total_affected / total_elements * 100) if total_elements > 0 else 0
        
        # Get cost and timeline estimates
        cost_range = self._estimate_cost(failures)
        timeline = self._estimate_timeline(failures)
        
        return ImpactMetrics(
            total_affected_elements=total_affected,
            affected_by_type=dict(affected_by_type),
            percentage_of_building=round(percentage, 2),
            failure_distribution=dict(failure_by_severity),
            cost_estimate_range=cost_range,
            implementation_timeline=timeline
        )
    
    def _estimate_cost(self, failures: List[Dict[str, Any]]) -> Optional[str]:
        """Estimate cost based on failure types and count."""
        if not failures:
            return None
        
        # Base cost multipliers per failure type
        base_cost = len(failures) * 500  # $500 per failure as baseline
        
        # Add severity multipliers
        high_severity_count = sum(1 for f in failures if f.get('severity') == 'ERROR')
        base_cost += high_severity_count * 1000  # Additional $1000 for ERROR severity
        
        # Estimate range (assume 20% variance)
        low_estimate = base_cost * 0.8
        high_estimate = base_cost * 1.2
        
        return f"${int(low_estimate):,} - ${int(high_estimate):,}"
    
    def _estimate_timeline(self, failures: List[Dict[str, Any]]) -> Optional[str]:
        """Estimate implementation timeline."""
        if not failures:
            return None
        
        total_failures = len(failures)
        
        # Timeline estimation: 2-3 failures per week typical
        weeks_per_failure = 1 / 2.5
        estimated_weeks = total_failures * weeks_per_failure
        
        if estimated_weeks < 1:
            return "< 1 week"
        elif estimated_weeks < 2:
            return "1-2 weeks"
        elif estimated_weeks < 4:
            return "2-4 weeks"
        elif estimated_weeks < 8:
            return "1-2 months"
        else:
            months = int(estimated_weeks / 4)
            return f"{months}+ months"
    
    def get_failure_distribution(self, failures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of failures by type."""
        distribution = defaultdict(int)
        
        for failure in failures:
            # Group by element type
            element_type = failure.get('element_type', 'Unknown')
            distribution[element_type] += 1
        
        return dict(distribution)
    
    def get_severity_distribution(self, failures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of failures by severity."""
        distribution = defaultdict(int)
        
        for failure in failures:
            severity = failure.get('severity', 'WARNING')
            distribution[severity] += 1
        
        return dict(distribution)
    
    def get_most_affected_elements(self, failures: List[Dict[str, Any]], 
                                   top_n: int = 10) -> List[Tuple[str, int]]:
        """Get elements with most failures."""
        element_failure_count = Counter()
        
        for failure in failures:
            element_id = failure.get('element_id', failure.get('element_guid'))
            if element_id:
                element_failure_count[element_id] += 1
        
        return element_failure_count.most_common(top_n)
    
    def get_most_common_rules(self, failures: List[Dict[str, Any]], 
                             top_n: int = 10) -> List[Tuple[str, int]]:
        """Get rules that fail most frequently."""
        rule_failure_count = Counter()
        
        for failure in failures:
            rule_id = failure.get('rule_id', 'Unknown')
            rule_failure_count[rule_id] += 1
        
        return rule_failure_count.most_common(top_n)
    
    def group_failures_by_rule(self, failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group failures by rule ID."""
        grouped = defaultdict(list)
        
        for failure in failures:
            rule_id = failure.get('rule_id', 'Unknown')
            grouped[rule_id].append(failure)
        
        return dict(grouped)
    
    def group_failures_by_element_type(self, failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group failures by element type."""
        grouped = defaultdict(list)
        
        for failure in failures:
            element_type = failure.get('element_type', 'Unknown')
            grouped[element_type].append(failure)
        
        return dict(grouped)
    
    def get_critical_failures(self, failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get only critical/error severity failures."""
        critical = [f for f in failures if f.get('severity') in ['ERROR', 'CRITICAL']]
        return critical
    
    def get_compliance_percentage(self, passed: int, failed: int) -> float:
        """Calculate compliance percentage."""
        total = passed + failed
        if total == 0:
            return 0.0
        return round((passed / total) * 100, 2)
