"""
Solution Generator Module

Generates solutions and fixes for element failures.
Answers: "How can we fix this?"
"""

from typing import Dict, List, Optional, Any
from reasoning_layer.models import (
    Solution, SeverityLevel, FailureAnalysis
)


class SolutionGenerator:
    """Generates solutions and alternatives for element failures."""
    
    def generate_solution(self,
                         failure: FailureAnalysis,
                         rule: Dict) -> Solution:
        """
        Generate a solution for a failure.
        
        Args:
            failure: FailureAnalysis describing the failure
            rule: Original rule dict with requirements
            
        Returns:
            Solution with recommendation and alternatives
        """
        element_type = failure.element_type
        metrics = failure.metrics
        
        # Generate primary recommendation
        recommendation = self._generate_recommendation(
            element_type, failure, rule, metrics
        )
        
        # Generate detailed description
        description = self._generate_description(
            element_type, failure, recommendation, metrics
        )
        
        # Generate implementation steps
        steps = self._generate_implementation_steps(
            element_type, failure, recommendation, metrics
        )
        
        # Generate alternatives
        alternatives = self._generate_alternatives(
            element_type, failure, recommendation, metrics
        )
        
        # Determine feasibility
        feasibility = self._determine_feasibility(
            element_type, failure, metrics
        )
        
        # Estimate cost
        cost = self._estimate_cost(element_type, failure, recommendation)
        
        # Estimate effort
        effort = self._estimate_effort(element_type, failure, recommendation)
        
        # Design implications
        implications = self._assess_design_implications(
            element_type, failure, recommendation, metrics
        )
        
        # Potential issues/trade-offs
        potential_issues = self._identify_potential_issues(
            element_type, failure, recommendation
        )
        
        return Solution(
            failure_id=f"{failure.element_id}_{failure.rule_id}",
            element_id=failure.element_id,
            recommendation=recommendation,
            description=description,
            implementation_steps=steps,
            alternatives=alternatives,
            feasibility=feasibility,
            estimated_cost=cost,
            estimated_effort=effort,
            design_implications=implications,
            potential_issues=potential_issues,
            confidence=self._calculate_confidence(failure, recommendation),
            reasoning_detail=self._generate_reasoning(failure, recommendation)
        )
    
    def _generate_recommendation(self, element_type: str, failure: FailureAnalysis,
                                rule: Dict, metrics) -> str:
        """Generate primary fix recommendation."""
        element_type_lower = element_type.lower()
        
        if 'door' in element_type_lower:
            return self._door_solution(failure, rule, metrics)
        elif 'stair' in element_type_lower:
            return self._stair_solution(failure, rule, metrics)
        elif 'ramp' in element_type_lower:
            return self._ramp_solution(failure, rule, metrics)
        elif 'window' in element_type_lower:
            return self._window_solution(failure, rule, metrics)
        else:
            return self._generic_solution(failure, rule, metrics)
    
    def _door_solution(self, failure: FailureAnalysis, rule: Dict, metrics) -> str:
        """Generate door-specific solutions."""
        rule_name = rule.get('name', '').lower()
        
        if 'width' in rule_name or 'opening' in rule_name:
            if hasattr(metrics, 'deviation') and metrics.deviation and metrics.deviation < 0:
                # Door too narrow
                return (f"Increase door opening width from {metrics.actual_value}{metrics.unit} "
                       f"to {metrics.required_value}{metrics.unit} "
                       f"(minimum {metrics.required_value}{metrics.unit} required)")
            else:
                return f"Widen door opening to minimum {metrics.required_value}{metrics.unit}"
        
        elif 'pressure' in rule_name or 'force' in rule_name:
            return (f"Replace door hardware to reduce opening force from "
                   f"{metrics.actual_value} to maximum {metrics.required_value}N")
        
        elif 'handle' in rule_name or 'hardware' in rule_name:
            return f"Replace lever-type door handles (required instead of knobs)"
        
        elif 'height' in rule_name:
            return f"Adjust door threshold height to maximum {metrics.required_value}{metrics.unit}"
        
        return "Modify door to meet accessibility requirements"
    
    def _stair_solution(self, failure: FailureAnalysis, rule: Dict, metrics) -> str:
        """Generate stair-specific solutions."""
        rule_name = rule.get('name', '').lower()
        
        if 'width' in rule_name:
            return (f"Increase stair width from {metrics.actual_value}{metrics.unit} "
                   f"to {metrics.required_value}{metrics.unit} minimum")
        
        elif 'height' in rule_name or 'riser' in rule_name:
            current_riser = metrics.actual_value
            max_riser = metrics.required_value
            return (f"Redesign stair - current riser height {current_riser}{metrics.unit} "
                   f"exceeds maximum {max_riser}{metrics.unit} (add more steps to reduce height)")
        
        elif 'tread' in rule_name:
            return (f"Increase stair tread depth from {metrics.actual_value}{metrics.unit} "
                   f"to {metrics.required_value}{metrics.unit} minimum")
        
        elif 'handrail' in rule_name:
            return "Add or adjust handrails on both sides of stair"
        
        elif 'landing' in rule_name:
            return f"Add landings every {metrics.required_value}{metrics.unit} of vertical rise"
        
        return "Modify stair design to meet accessibility and safety requirements"
    
    def _ramp_solution(self, failure: FailureAnalysis, rule: Dict, metrics) -> str:
        """Generate ramp-specific solutions."""
        rule_name = rule.get('name', '').lower()
        
        if 'slope' in rule_name or 'gradient' in rule_name or 'rise' in rule_name:
            if hasattr(metrics, 'deviation_percent') and metrics.deviation_percent > 0:
                return (f"Reduce ramp slope from {metrics.actual_value}% "
                       f"to {metrics.required_value}% maximum (extend horizontal length)")
            else:
                return f"Ramp slope must not exceed {metrics.required_value}%"
        
        elif 'width' in rule_name:
            return (f"Increase ramp width from {metrics.actual_value}{metrics.unit} "
                   f"to {metrics.required_value}{metrics.unit} minimum")
        
        elif 'landing' in rule_name:
            return f"Add intermediate landings - required every {metrics.required_value}{metrics.unit} of rise"
        
        elif 'handrail' in rule_name:
            return "Add handrails on both sides of ramp"
        
        return "Modify ramp to meet accessibility gradient requirements"
    
    def _window_solution(self, failure: FailureAnalysis, rule: Dict, metrics) -> str:
        """Generate window-specific solutions."""
        rule_name = rule.get('name', '').lower()
        
        if 'area' in rule_name or 'size' in rule_name:
            return (f"Increase window area from {metrics.actual_value}{metrics.unit} "
                   f"to {metrics.required_value}{metrics.unit} minimum")
        
        elif 'height' in rule_name or 'sill' in rule_name:
            return (f"Adjust window sill height from {metrics.actual_value}{metrics.unit} "
                   f"to {metrics.required_value}{metrics.unit}")
        
        elif 'daylight' in rule_name or 'light' in rule_name:
            return "Add windows or increase size to provide adequate daylighting"
        
        return "Modify window to meet building standards"
    
    def _generic_solution(self, failure: FailureAnalysis, rule: Dict, metrics) -> str:
        """Generate generic solution for unknown element types."""
        return f"Modify {failure.element_type} to meet {rule.get('name', 'requirement')}"
    
    def _generate_description(self, element_type: str, failure: FailureAnalysis,
                             recommendation: str, metrics) -> str:
        """Generate detailed description of the solution."""
        description = f"**Recommendation:** {recommendation}\n\n"
        
        description += f"**Current State:** {failure.element_type} '{failure.element_name or 'unnamed'}' "
        description += f"has {failure.metrics.actual_value}{metrics.unit}\n"
        
        description += f"**Required State:** Must have {failure.metrics.required_value}{metrics.unit}\n"
        
        if hasattr(metrics, 'deviation') and metrics.deviation:
            description += f"**Deviation:** {metrics.deviation}{metrics.unit} "
            if hasattr(metrics, 'deviation_percent'):
                description += f"({abs(metrics.deviation_percent):.1f}% shortfall)\n"
        
        description += f"\n**Rule:** {failure.rule_name}\n"
        description += f"**Severity:** {failure.severity.value}\n"
        description += f"**Impact:** {failure.impact_on_users}\n"
        
        return description
    
    def _generate_implementation_steps(self, element_type: str, failure: FailureAnalysis,
                                      recommendation: str, metrics) -> List[str]:
        """Generate step-by-step implementation instructions."""
        element_type_lower = element_type.lower()
        
        steps = ["1. Assessment and Planning:"]
        steps.append("   - Review current design and measurements")
        steps.append("   - Verify affected areas and related elements")
        steps.append("   - Assess structural and spatial constraints")
        
        if 'door' in element_type_lower:
            steps.extend([
                "2. Door Widening:",
                f"   - Increase opening width to {failure.metrics.required_value}{metrics.unit}",
                "   - Check wall structure and load-bearing capacity",
                "   - Modify surrounding elements (walls, casings, frame)",
                "3. Hardware and Accessibility:",
                "   - Install lever-type handles accessible to all users",
                "   - Reduce opening force to ≤13.4N (if required)",
                "4. Testing and Verification:",
                "   - Verify minimum clear opening width",
                "   - Test accessibility with mobility devices"
            ])
        
        elif 'stair' in element_type_lower:
            steps.extend([
                "2. Stair Reconfiguration:",
                "   - Calculate required number of steps for new riser height",
                "   - Determine new overall run/rise",
                "   - Assess impact on surrounding spaces",
                "3. Component Modifications:",
                "   - Add/modify steps as needed",
                "   - Increase width if required",
                "   - Install compliant handrails",
                "4. Verification:",
                "   - Measure tread depth and riser height",
                "   - Verify handrails are accessible"
            ])
        
        elif 'ramp' in element_type_lower:
            steps.extend([
                "2. Ramp Redesign:",
                f"   - Extend ramp length to achieve {failure.metrics.required_value}% slope maximum",
                "   - Add intermediate landings as required",
                "   - Ensure width compliance",
                "3. Safety Features:",
                "   - Install handrails on both sides",
                "   - Add edge protection",
                "4. Testing:",
                "   - Verify slope with level/transit",
                "   - Test with wheelchair access"
            ])
        
        steps.extend([
            f"{len(steps)+1}. Final Inspection:",
            "   - Verify compliance with all related rules",
            "   - Check for unintended side effects",
            "   - Document changes in as-built drawings"
        ])
        
        return steps
    
    def _generate_alternatives(self, element_type: str, failure: FailureAnalysis,
                              recommendation: str, metrics) -> List[Dict[str, str]]:
        """Generate alternative solutions with pros/cons."""
        alternatives = []
        element_type_lower = element_type.lower()
        
        if 'door' in element_type_lower:
            # Alternative 1: Pocket door
            alternatives.append({
                "name": "Pocket Door Installation",
                "description": "Install sliding pocket door for width compliance without wall removal",
                "pros": "More space-efficient; reduces wall obstruction; maintains floor space",
                "cons": "Higher cost; requires jamb modification; may not work with load-bearing walls; reduces wall cavity space"
            })
            
            # Alternative 2: Swing direction change
            alternatives.append({
                "name": "Reverse Door Swing Direction",
                "description": "Change door swing to open outward, increasing usable opening",
                "pros": "Lower cost; simpler modification; no structural work",
                "cons": "May conflict with circulation; building code restrictions; limited additional width"
            })
        
        elif 'stair' in element_type_lower:
            # Alternative 1: Replace with ramp
            alternatives.append({
                "name": "Install Accessible Ramp (instead of stairs)",
                "description": "Replace or supplement stair with compliant ramp",
                "pros": "Better accessibility; continuous slope; wheelchairs fully accessible",
                "cons": "Requires more horizontal space; slope limitations; may not suit all locations"
            })
            
            # Alternative 2: Add platform
            alternatives.append({
                "name": "Add Intermediate Landing/Platform",
                "description": "Break up long run with intermediate landing",
                "pros": "Reduces fatigue; improves accessibility; smaller incremental changes",
                "cons": "Requires more vertical space; complex construction"
            })
        
        elif 'ramp' in element_type_lower:
            # Alternative 1: Elevator
            alternatives.append({
                "name": "Install Elevator or Lift",
                "description": "Provide vertical access via mechanical means",
                "pros": "Highest accessibility; compact footprint; serves all users",
                "cons": "Highest cost; maintenance required; requires mechanical systems; building code compliance"
            })
            
            # Alternative 2: Tiered approach
            alternatives.append({
                "name": "Multi-Stage Ramp with Landings",
                "description": "Create gentler slope using multiple shorter ramps with landings",
                "pros": "Less steep overall; reduced length; safer for wheelchair users",
                "cons": "More complex design; requires more horizontal space"
            })
        
        return alternatives
    
    def _determine_feasibility(self, element_type: str, failure: FailureAnalysis,
                              metrics) -> str:
        """Determine implementation feasibility."""
        severity = failure.severity
        
        if severity == SeverityLevel.CRITICAL:
            return "complex"  # Critical issues often require major changes
        
        # Element type affects feasibility
        if 'door' in element_type.lower():
            if hasattr(metrics, 'deviation') and metrics.deviation:
                if abs(metrics.deviation) < 100:  # Small deviation
                    return "easy"
                elif abs(metrics.deviation) < 300:  # Medium deviation
                    return "moderate"
                else:  # Large deviation
                    return "complex"
            return "moderate"
        
        elif 'stair' in element_type.lower():
            return "complex"  # Stairs always complex to modify
        
        elif 'ramp' in element_type.lower():
            if hasattr(metrics, 'deviation_percent') and metrics.deviation_percent:
                if metrics.deviation_percent < 5:
                    return "moderate"
                else:
                    return "complex"
            return "moderate"
        
        elif 'window' in element_type.lower():
            return "moderate"
        
        return "moderate"
    
    def _estimate_cost(self, element_type: str, failure: FailureAnalysis,
                      recommendation: str) -> str:
        """Estimate implementation cost."""
        feasibility = self._determine_feasibility(element_type, failure, failure.metrics)
        
        if 'pocket door' in recommendation.lower():
            return "moderate ($2,000-$5,000)"
        elif 'elevator' in recommendation.lower() or 'lift' in recommendation.lower():
            return "high ($15,000-$50,000+)"
        elif 'widen' in recommendation.lower() and 'door' in element_type.lower():
            return "low-moderate ($500-$2,000)"
        elif 'stair' in element_type.lower():
            return "high ($5,000-$20,000+)"
        elif 'ramp' in element_type.lower():
            return "moderate-high ($3,000-$10,000)"
        elif 'window' in element_type.lower():
            return "moderate ($1,000-$5,000)"
        elif feasibility == "easy":
            return "low ($100-$500)"
        elif feasibility == "moderate":
            return "moderate ($500-$3,000)"
        else:
            return "high ($5,000+)"
    
    def _estimate_effort(self, element_type: str, failure: FailureAnalysis,
                        recommendation: str) -> str:
        """Estimate implementation effort/time."""
        if 'replace' in recommendation.lower() or 'install' in recommendation.lower():
            if 'hardware' in recommendation.lower():
                return "2-3 days"
            elif 'handrail' in recommendation.lower():
                return "3-5 days"
            elif 'door' in element_type.lower():
                return "5-10 days"
            elif 'window' in element_type.lower():
                return "3-7 days"
            else:
                return "1-2 weeks"
        
        if 'redesign' in recommendation.lower():
            return "2-4 weeks"
        
        if 'widen' in recommendation.lower():
            return "1-3 weeks"
        
        if 'extend' in recommendation.lower():
            return "2-3 weeks"
        
        return "1-2 weeks"
    
    def _assess_design_implications(self, element_type: str, failure: FailureAnalysis,
                                   recommendation: str, metrics) -> Optional[str]:
        """Assess cascading design implications."""
        if 'door' in element_type.lower():
            if 'widen' in recommendation.lower():
                return "Widening may require wall modification, structural changes, and impacts adjacent spaces/rooms"
            elif 'pocket' in recommendation.lower():
                return "Pocket door reduces wall cavity space, may conflict with plumbing/electrical/HVAC"
        
        elif 'stair' in element_type.lower():
            if 'redesign' in recommendation.lower() or 'add step' in recommendation.lower():
                return "Stair redesign affects floor-to-floor heights, may cascade to multiple floors, impacts vertical clearances"
        
        elif 'ramp' in element_type.lower():
            if 'extend' in recommendation.lower():
                return "Ramp extension increases footprint, may require grade changes, affects site layout and drainage"
        
        return None
    
    def _identify_potential_issues(self, element_type: str, failure: FailureAnalysis,
                                  recommendation: str) -> List[str]:
        """Identify potential issues and trade-offs."""
        issues = []
        
        if 'widen' in recommendation.lower():
            issues.append("Structural: Check if walls are load-bearing")
            issues.append("MEP: Verify no mechanical/electrical/plumbing systems in path")
            issues.append("Adjacent spaces: May reduce usable area in neighboring rooms")
        
        if 'pocket door' in recommendation.lower():
            issues.append("Cannot be used on load-bearing walls")
            issues.append("Reduces usable wall space behind door")
            issues.append("More expensive than standard doors")
        
        if 'ramp' in recommendation.lower():
            issues.append("Requires significant horizontal space")
            issues.append("May create drainage or site grading issues")
            issues.append("Safety: Handrail requirements and edge protection needed")
        
        if 'stair' in recommendation.lower() and 'modify' in recommendation.lower():
            issues.append("May affect floor-to-floor height calculations")
            issues.append("Could impact upper/lower floor layouts")
            issues.append("Structural modifications may be needed")
        
        if not issues:
            issues.append("Verify all related building code requirements")
        
        return issues
    
    def _calculate_confidence(self, failure: FailureAnalysis,
                            recommendation: str) -> float:
        """Calculate confidence level of solution (0.0-1.0)."""
        confidence = 0.85  # Base confidence
        
        # Reduce confidence for complex scenarios
        if failure.severity == SeverityLevel.CRITICAL:
            confidence -= 0.05
        
        if 'complex' in failure.root_cause.lower():
            confidence -= 0.10
        
        # Increase confidence for well-understood solutions
        if any(word in recommendation.lower() for word in ['widen', 'increase', 'extend']):
            confidence += 0.05
        
        return max(0.5, min(1.0, confidence))
    
    def _generate_reasoning(self, failure: FailureAnalysis,
                          recommendation: str) -> str:
        """Generate reasoning for why this solution is recommended."""
        reasoning = f"This solution addresses the root cause: {failure.root_cause.lower()}. "
        reasoning += f"By {recommendation.lower()}, the element will comply with {failure.rule_name}. "
        reasoning += f"This benefits {self._get_beneficiary_phrase(failure)} and addresses the {failure.severity.value} severity issue."
        return reasoning
    
    def _get_beneficiary_phrase(self, failure: FailureAnalysis) -> str:
        """Get beneficiary phrase based on rule/element type."""
        rule_name = failure.rule_name.lower()
        
        if any(word in rule_name for word in ['wheelchair', 'mobility', 'accessible']):
            return "users with mobility disabilities"
        elif any(word in rule_name for word in ['fire', 'emergency', 'exit']):
            return "all occupants during emergencies"
        elif any(word in rule_name for word in ['elderly', 'aged']):
            return "elderly and aging occupants"
        else:
            return "all building occupants"
