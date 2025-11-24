"""
Element Failure Analyzer Module

Explains WHY specific elements failed rules.
Answers: "Why did this element fail?"
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from reasoning_layer.models import (
    FailureAnalysis, FailureMetrics, SeverityLevel,
    ElementFailureExplanation
)

logger = logging.getLogger(__name__)


class ElementFailureAnalyzer:
    """Analyzes why elements fail rules and generates detailed failure explanations."""
    
    def analyze_failure(self, 
                       element_id: str,
                       element_type: str,
                       element_name: Optional[str],
                       rule_id: str,
                       rule_name: str,
                       rule: Dict,
                       actual_value: Any,
                       required_value: Any,
                       unit: str = "",
                       location: Optional[str] = None,
                       related_elements: Optional[List[str]] = None) -> FailureAnalysis:
        """
        Create a detailed failure analysis for why an element failed a rule.
        
        Args:
            element_id: IFC element identifier
            element_type: Type like "IfcDoor", "IfcStair"
            element_name: Name of element in model
            rule_id: Which rule failed
            rule_name: Rule name
            rule: Full rule dict with properties, comparison, etc.
            actual_value: What element actually has
            required_value: What it should have
            unit: Measurement unit (mm, degrees, etc.)
            location: Where in building
            related_elements: Other affected elements
            
        Returns:
            FailureAnalysis with detailed explanation
        """
        # Calculate metrics
        metrics = self._calculate_metrics(actual_value, required_value, unit)
        
        # Determine why it failed
        failure_reason = self._determine_failure_reason(
            element_type, rule, actual_value, required_value, metrics
        )
        
        # Infer design intent
        design_intent = self._infer_design_intent(element_type, actual_value, metrics)
        
        # Identify root cause
        root_cause = self._identify_root_cause(
            element_type, failure_reason, metrics
        )
        
        # Determine severity
        severity = self._determine_failure_severity(
            rule, actual_value, required_value, metrics
        )
        
        # Assess impact on users
        impact = self._assess_user_impact(
            element_type, rule_name, severity, metrics
        )
        
        return FailureAnalysis(
            element_id=element_id,
            element_type=element_type,
            element_name=element_name,
            rule_id=rule_id,
            rule_name=rule_name,
            failure_reason=failure_reason,
            design_intent=design_intent,
            root_cause=root_cause,
            metrics=metrics,
            severity=severity,
            impact_on_users=impact,
            location=location,
            related_elements=related_elements or []
        )
    
    def _calculate_metrics(self, actual_value: Any, required_value: Any, 
                          unit: str = "") -> FailureMetrics:
        """Calculate metrics showing how the failure deviates from requirement."""
        metrics = FailureMetrics(
            actual_value=actual_value,
            required_value=required_value,
            unit=unit
        )
        
        # Calculate numeric deviation if applicable
        try:
            if isinstance(actual_value, (int, float)) and isinstance(required_value, (int, float)):
                metrics.deviation = float(actual_value) - float(required_value)
                
                if required_value != 0:
                    metrics.deviation_percent = (metrics.deviation / float(required_value)) * 100
        except (TypeError, ValueError):
            pass
        
        # Handle categorical/string mismatches
        if isinstance(actual_value, str) and isinstance(required_value, str):
            metrics.mismatch_detail = f"Is '{actual_value}' but should be '{required_value}'"
        elif isinstance(actual_value, bool):
            metrics.mismatch_detail = f"Is '{actual_value}' but should be '{required_value}'"
        
        return metrics
    
    def _determine_failure_reason(self, element_type: str, rule: Dict, 
                                 actual_value: Any, required_value: Any,
                                 metrics: FailureMetrics) -> str:
        """Determine the specific reason for failure."""
        rule_name = rule.get('name', 'Rule')
        property_name = rule.get('property', 'property')
        comparison = rule.get('comparison', '==')
        
        # Handle cases where values are None or missing
        if actual_value is None or required_value is None:
            if actual_value is None and required_value is None:
                return (f"{element_type} {property_name} is not available in the model "
                       f"and cannot be verified against the requirement")
            elif actual_value is None:
                return (f"{element_type} {property_name} is missing from the model "
                       f"(required: {required_value})")
            else:
                return (f"{element_type} {property_name} is {actual_value} "
                       f"but the requirement specification is incomplete")
        
        # Build reason string based on comparison type
        if comparison == '>=':
            return (f"{element_type} {property_name} is {actual_value}{metrics.unit} "
                   f"but must be at least {required_value}{metrics.unit} "
                   f"(shortfall: {abs(metrics.deviation) if metrics.deviation else '?'}{metrics.unit})")
        
        elif comparison == '<=':
            return (f"{element_type} {property_name} is {actual_value}{metrics.unit} "
                   f"but must not exceed {required_value}{metrics.unit} "
                   f"(excess: {abs(metrics.deviation) if metrics.deviation else '?'}{metrics.unit})")
        
        elif comparison == '>':
            return (f"{element_type} {property_name} is {actual_value}{metrics.unit} "
                   f"but must be greater than {required_value}{metrics.unit}")
        
        elif comparison == '<':
            return (f"{element_type} {property_name} is {actual_value}{metrics.unit} "
                   f"but must be less than {required_value}{metrics.unit}")
        
        elif comparison == '==':
            if isinstance(actual_value, str):
                return (f"{element_type} {property_name} is '{actual_value}' "
                       f"but must be '{required_value}'")
            else:
                return (f"{element_type} {property_name} is {actual_value} "
                       f"but must be {required_value}")
        
        else:
            return f"{element_type} does not meet {rule_name} requirement"
    
    def _infer_design_intent(self, element_type: str, actual_value: Any,
                            metrics: FailureMetrics) -> Optional[str]:
        """Infer what the designer may have intended."""
        if element_type.lower() == 'ifcdoor':
            if hasattr(metrics, 'deviation') and metrics.deviation:
                if metrics.deviation < 0:  # Door too narrow
                    return "Designer may have prioritized minimizing wall thickness or maximizing floor space over accessibility"
                elif metrics.deviation > 0:  # Door too wide (rare)
                    return "Designer may have accommodated specific equipment or furnishings"
            return "Designer may not have been aware of accessibility requirements"
        
        elif element_type.lower() == 'ifcstair':
            if 'height' in str(actual_value).lower() or metrics.unit in ['mm', 'cm', 'm']:
                if hasattr(metrics, 'deviation') and metrics.deviation and metrics.deviation > 0:
                    return "Designer may have used tread/riser dimensions from existing stock or convenience"
                return "Designer may have optimized for standard construction practices"
            return "Designer may not have considered accessibility requirements"
        
        elif element_type.lower() == 'ifcramp':
            if hasattr(metrics, 'deviation_percent') and metrics.deviation_percent and metrics.deviation_percent > 0:
                return "Designer may have maximized slope for compact design or drainage"
            return "Designer may not have planned for accessible route"
        
        elif element_type.lower() == 'ifcwindow':
            return "Designer may have prioritized architectural aesthetics or structural considerations"
        
        return "Designer may not have considered regulatory requirements"
    
    def _identify_root_cause(self, element_type: str, failure_reason: str,
                            metrics: FailureMetrics) -> str:
        """Identify the root cause of the failure."""
        # Numeric deviations suggest design oversight or constraint
        if hasattr(metrics, 'deviation') and metrics.deviation:
            if abs(metrics.deviation) < 10:  # Small deviation
                return ("Minor design oversight - small dimensional inconsistency, possibly due to "
                       "rounding, standard material sizes, or incremental design changes")
            else:  # Large deviation
                return ("Design constraint or deliberate choice - significant dimensional difference "
                       "suggests designer prioritized other factors (aesthetics, cost, space, etc.)")
        
        # Categorical mismatches suggest missing requirements
        if 'is' in failure_reason and 'must be' in failure_reason:
            return "Missing or incorrect specification in design - requirement not properly implemented"
        
        # Type-specific causes
        if 'door' in element_type.lower():
            if 'width' in failure_reason.lower():
                return "Door opening too narrow - wall thickness, structural constraints, or oversight"
            elif 'pressure' in failure_reason.lower():
                return "Door handle force requirement not met - hardware selection issue"
            return "Door specification incomplete or non-compliant"
        
        elif 'stair' in element_type.lower():
            if 'height' in failure_reason.lower():
                return "Tread/riser proportions incorrect - standard vs accessibility mismatch"
            elif 'width' in failure_reason.lower():
                return "Stairway width insufficient - space constraint or oversight"
            return "Stair specification incomplete or non-compliant"
        
        else:
            return "Specification does not meet regulatory requirement"
    
    def _determine_failure_severity(self, rule: Dict, actual_value: Any,
                                   required_value: Any, metrics: FailureMetrics) -> SeverityLevel:
        """Determine severity of the failure."""
        rule_name = rule.get('name', '').lower()
        severity_level = rule.get('severity', 'medium').lower()
        
        # Rule severity
        if severity_level == 'critical' or any(word in rule_name for word in ['fire', 'exit', 'emergency', 'safe']):
            return SeverityLevel.CRITICAL
        
        # Check magnitude of deviation
        if hasattr(metrics, 'deviation_percent') and metrics.deviation_percent:
            if abs(metrics.deviation_percent) > 50:  # >50% deviation
                return SeverityLevel.CRITICAL
            elif abs(metrics.deviation_percent) > 25:  # >25% deviation
                return SeverityLevel.HIGH
            elif abs(metrics.deviation_percent) > 10:  # >10% deviation
                return SeverityLevel.MEDIUM
            else:  # <10% deviation
                return SeverityLevel.LOW
        
        # Default based on rule severity
        if severity_level in ['critical', 'high']:
            return SeverityLevel.HIGH
        elif severity_level in ['medium']:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _assess_user_impact(self, element_type: str, rule_name: str,
                           severity: SeverityLevel, metrics: FailureMetrics) -> str:
        """Assess how this failure impacts building users."""
        impacts = []
        
        if severity == SeverityLevel.CRITICAL:
            impacts.append("CRITICAL: This failure poses a significant safety or accessibility risk")
        elif severity == SeverityLevel.HIGH:
            impacts.append("Substantial accessibility or safety impact")
        else:
            impacts.append("Minor compliance issue")
        
        # Element-specific impacts
        if 'door' in element_type.lower():
            if 'width' in rule_name.lower():
                impacts.append("Users with mobility devices (wheelchairs, walkers) cannot pass through")
            elif 'pressure' in rule_name.lower():
                impacts.append("Users with limited hand strength cannot operate door independently")
            else:
                impacts.append("Impacts door usability for people with disabilities")
        
        elif 'stair' in element_type.lower():
            impacts.append("Stair proportions make ascent/descent difficult or dangerous for users with mobility limitations")
            impacts.append("Elderly or disabled occupants at increased fall risk")
        
        elif 'ramp' in element_type.lower():
            impacts.append("Wheelchair users cannot ascend safely - slope too steep")
            impacts.append("Increased fatigue and risk of tipping or losing control")
        
        elif 'window' in element_type.lower():
            impacts.append("Reduced daylighting affects occupant well-being and visibility")
        
        # Numeric impact
        if hasattr(metrics, 'deviation_percent') and metrics.deviation_percent:
            impacts.append(f"Deviation: {abs(metrics.deviation_percent):.1f}% from requirement")
        
        return " | ".join(impacts)
    
    def generate_element_explanation(self,
                                    element_id: str,
                                    element_type: str,
                                    element_name: Optional[str],
                                    failed_rule_results: List[Dict]) -> ElementFailureExplanation:
        """
        Generate complete explanation for why an element failed multiple rules.
        
        Args:
            element_id: IFC element identifier
            element_type: Element type
            element_name: Element name
            failed_rule_results: List of dicts with:
                - rule: Rule dict
                - actual_value: What element has
                - required_value: What it should have
                - location: Optional location
                
        Returns:
            ElementFailureExplanation with all analyses
        """
        analyses = []
        failed_rules = []
        
        for result in failed_rule_results:
            rule = result.get('rule', {})
            
            # Handle case where rule is None or empty
            if not rule or not isinstance(rule, dict):
                logger.warning(f"Invalid rule object in failed_rule_results: {rule}")
                continue
            
            # Extract rule metadata with fallbacks
            rule_id = rule.get('id')
            rule_name = rule.get('name', 'Unknown Rule')
            
            # If rule_id is missing, skip this rule (invalid entry)
            if not rule_id:
                logger.warning(f"Rule missing 'id' field: {rule}")
                continue
            
            failed_rules.append(rule_id)
            
            analysis = self.analyze_failure(
                element_id=element_id,
                element_type=element_type,
                element_name=element_name,
                rule_id=rule_id,
                rule_name=rule_name,
                rule=rule,
                actual_value=result.get('actual_value'),
                required_value=result.get('required_value'),
                unit=result.get('unit', ''),
                location=result.get('location'),
                related_elements=result.get('related_elements', [])
            )
            analyses.append(analysis)
        
        # Calculate statistics
        total_failures = len(analyses)
        critical = sum(1 for a in analyses if a.severity == SeverityLevel.CRITICAL)
        high = sum(1 for a in analyses if a.severity == SeverityLevel.HIGH)
        
        # Determine compliance impact
        if critical > 0:
            compliance_impact = f"CRITICAL: {critical} critical failure(s) must be resolved before approval"
        elif high > 0:
            compliance_impact = f"NON-COMPLIANT: {high} significant failure(s) requiring remediation"
        else:
            compliance_impact = "MINOR: Failures with low severity but should be addressed"
        
        return ElementFailureExplanation(
            element_id=element_id,
            element_type=element_type,
            element_name=element_name,
            failed_rules=failed_rules,
            analyses=analyses,
            solutions=[],  # To be populated by SolutionGenerator
            total_failures=total_failures,
            critical_failures=critical,
            high_severity_failures=high,
            compliance_impact=compliance_impact
        )
