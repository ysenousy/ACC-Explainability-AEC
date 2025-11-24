"""
Rule Justification Module

Explains WHY rules exist - their regulatory intent, safety concerns, and accessibility goals.
Answers: "Why is this rule required?"
"""

import json
from typing import Dict, List, Optional
from reasoning_layer.models import (
    RuleJustification, RegulatoryReference, ReasoningType,
    SeverityLevel, RuleExplanationResult
)


class RuleJustifier:
    """Generates explanations for why rules exist."""
    
    def __init__(self, rule_explanations_file: Optional[str] = None):
        """
        Initialize with optional rule explanations reference data.
        
        Args:
            rule_explanations_file: Path to JSON file with detailed rule explanations
        """
        self.rule_explanations_data = {}
        if rule_explanations_file:
            try:
                with open(rule_explanations_file, 'r') as f:
                    self.rule_explanations_data = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load rule explanations: {e}")
    
    def _get_explanation_text(self, rule: Dict) -> str:
        """Extract explanation text from rule (handles both string and dict formats)."""
        explanation_raw = rule.get('explanation', '')
        if isinstance(explanation_raw, dict):
            return explanation_raw.get('short', '')
        return str(explanation_raw)
    
    def justify_rule(self, rule: Dict) -> RuleJustification:
        """
        Create a justification for why a rule exists.
        
        Args:
            rule: Rule dict from enhanced-regulation-rules.json containing:
                - id, name, explanation
                - provenance (regulation, section, jurisdiction)
                - target (IFC class)
                
        Returns:
            RuleJustification explaining why rule exists
        """
        rule_id = rule.get('id', 'unknown')
        
        # Extract regulatory reference from provenance
        provenance = rule.get('provenance', {})
        primary_regulation = RegulatoryReference(
            standard=provenance.get('regulation', 'Unknown'),
            section=provenance.get('section', 'N/A'),
            jurisdiction=provenance.get('jurisdiction', 'International'),
            title=rule.get('name')
        )
        
        # Determine regulatory intent based on rule characteristics
        regulatory_intent = self._determine_regulatory_intent(rule)
        target_beneficiary = self._determine_beneficiary(rule)
        safety_concern = self._determine_safety_concern(rule)
        accessibility_concern = self._determine_accessibility_concern(rule)
        
        # Build related regulations
        related_regulations = self._find_related_regulations(rule_id)
        
        # Get or generate detailed explanation
        detailed_explanation = self._generate_detailed_explanation(rule)
        
        # Determine severity
        severity = self._determine_severity(rule)
        applicability = self._determine_applicability(rule)
        
        return RuleJustification(
            rule_id=rule_id,
            rule_name=rule.get('name', 'Unnamed Rule'),
            regulatory_intent=regulatory_intent,
            target_beneficiary=target_beneficiary,
            safety_concern=safety_concern,
            accessibility_concern=accessibility_concern,
            primary_regulation=primary_regulation,
            related_regulations=related_regulations,
            explanation=detailed_explanation,
            historical_context=self._get_historical_context(rule),
            severity=severity,
            applicability=applicability
        )
    
    def _determine_regulatory_intent(self, rule: Dict) -> str:
        """Determine the primary regulatory intent of a rule."""
        name = rule.get('name', '').lower()
        explanation = self._get_explanation_text(rule).lower()
        text = f"{name} {explanation}"
        
        # Safety intents
        if any(word in text for word in ['fire', 'exit', 'emergency', 'escape', 'safety']):
            return "Ensure safe egress and emergency evacuation"
        if any(word in text for word in ['slip', 'fall', 'surface', 'friction']):
            return "Prevent slips, trips, and falls"
        if any(word in text for word in ['weight', 'load', 'bearing', 'structural']):
            return "Ensure structural integrity and load capacity"
        
        # Accessibility intents
        if any(word in text for word in ['accessible', 'wheelchair', 'mobility', 'disabled', 'ada']):
            return "Ensure accessibility for people with disabilities"
        if any(word in text for word in ['handrail', 'grab', 'rail']):
            return "Provide safety and accessibility support"
        if any(word in text for word in ['width', 'clear', 'space', 'passage']):
            return "Provide adequate circulation and maneuvering space"
        
        # Health/Comfort intents
        if any(word in text for word in ['ventilation', 'air', 'daylight', 'light', 'window']):
            return "Ensure adequate ventilation, lighting, and air quality"
        if any(word in text for word in ['noise', 'sound', 'acoustic']):
            return "Maintain acoustic quality and minimize noise"
        
        # Universal default
        return "Ensure compliance with building codes and accessibility standards"
    
    def _determine_beneficiary(self, rule: Dict) -> str:
        """Determine who benefits from this rule."""
        name = rule.get('name', '').lower()
        explanation = self._get_explanation_text(rule).lower()
        text = f"{name} {explanation}"
        
        if any(word in text for word in ['disabled', 'wheelchair', 'mobility', 'blind', 'deaf', 'ada']):
            return "People with disabilities (mobility, visual, hearing impairments)"
        if any(word in text for word in ['elderly', 'aged', 'senior']):
            return "Elderly and aging occupants"
        if any(word in text for word in ['child', 'children']):
            return "Children and families"
        if any(word in text for word in ['emergency', 'fire', 'exit', 'evacuation']):
            return "All building occupants in emergency situations"
        
        return "All building occupants"
    
    def _determine_safety_concern(self, rule: Dict) -> Optional[str]:
        """Identify safety concerns addressed by rule."""
        name = rule.get('name', '').lower()
        explanation = self._get_explanation_text(rule).lower()
        text = f"{name} {explanation}"
        
        concerns = []
        
        if any(word in text for word in ['fire', 'flame', 'burn']):
            concerns.append("Fire safety and evacuation")
        if any(word in text for word in ['fall', 'fall hazard', 'slip', 'trip']):
            concerns.append("Fall and slip hazards")
        if any(word in text for word in ['door', 'opening', 'collapse']):
            concerns.append("Door/opening integrity and failure")
        if any(word in text for word in ['handrail', 'guard', 'railing']):
            concerns.append("Fall protection")
        if any(word in text for word in ['width', 'height', 'space', 'clear']):
            concerns.append("Entrapment and spatial hazards")
        if any(word in text for word in ['weight', 'load', 'bearing', 'structural']):
            concerns.append("Structural failure and collapse")
        if any(word in text for word in ['step', 'stair', 'ramp']):
            concerns.append("Vertical access hazards")
        
        return concerns[0] if concerns else None
    
    def _determine_accessibility_concern(self, rule: Dict) -> Optional[str]:
        """Identify accessibility concerns addressed by rule."""
        name = rule.get('name', '').lower()
        explanation = self._get_explanation_text(rule).lower()
        text = f"{name} {explanation}"
        
        concerns = []
        
        if any(word in text for word in ['wheelchair', 'mobility', 'accessible route']):
            concerns.append("Wheelchair accessibility and maneuvering")
        if any(word in text for word in ['blind', 'visual', 'sight', 'color']):
            concerns.append("Visual accessibility")
        if any(word in text for word in ['deaf', 'hearing', 'audio']):
            concerns.append("Hearing accessibility")
        if any(word in text for word in ['grab', 'handrail', 'support', 'rail']):
            concerns.append("Physical support and stability")
        if any(word in text for word in ['width', 'clear', 'passage', 'circulation']):
            concerns.append("Space for mobility devices and maneuvering")
        if any(word in text for word in ['door', 'opening', 'pressure', 'force']):
            concerns.append("Door operation and accessibility")
        if any(word in text for word in ['surface', 'floor', 'texture', 'slip']):
            concerns.append("Floor surface accessibility")
        
        return concerns[0] if concerns else None
    
    def _find_related_regulations(self, rule_id: str) -> List[RegulatoryReference]:
        """Find related regulations for cross-reference."""
        # This could be expanded with a database of related rules
        related = []
        
        # Common relationships
        relationships = {
            'ADA_': ['IBC', 'ANSI'],
            'IBC_': ['ADA', 'NFPA'],
            'DIN_': ['EN', 'ISO'],
        }
        
        for prefix, related_standards in relationships.items():
            if rule_id.startswith(prefix):
                # Could load actual related rules from data file
                break
        
        return related
    
    def _generate_detailed_explanation(self, rule: Dict) -> str:
        """Generate a detailed plain-language explanation of the rule."""
        # Start with provided explanation
        explanation = self._get_explanation_text(rule) or "Rule requirement"
        
        # Add regulatory intent
        intent = self._determine_regulatory_intent(rule)
        
        # Add beneficiary impact
        beneficiary = self._determine_beneficiary(rule)
        
        # Combine into detailed explanation
        detailed = f"{explanation}\n\n"
        detailed += f"Regulatory Intent: {intent}\n"
        detailed += f"Benefits: {beneficiary}\n"
        
        # Add safety/accessibility concerns if present
        safety = self._determine_safety_concern(rule)
        if safety:
            detailed += f"Safety Concern: {safety}\n"
        
        accessibility = self._determine_accessibility_concern(rule)
        if accessibility:
            detailed += f"Accessibility Concern: {accessibility}\n"
        
        return detailed.strip()
    
    def _determine_severity(self, rule: Dict) -> SeverityLevel:
        """Determine severity level of rule."""
        name = rule.get('name', '').lower()
        severity = rule.get('severity', '').lower()
        
        if severity in ['critical', 'high'] or any(word in name for word in ['fire', 'exit', 'emergency']):
            return SeverityLevel.CRITICAL
        elif severity in ['medium', 'significant']:
            return SeverityLevel.HIGH
        elif severity in ['low', 'minor']:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.MEDIUM
    
    def _determine_applicability(self, rule: Dict) -> str:
        """Determine where/when rule applies."""
        applicability = rule.get('applicability', 'All buildings')
        
        if applicability:
            return applicability
        
        # Infer from target
        target = rule.get('target', 'IfcElement').lower()
        
        if 'door' in target:
            return "All buildings - applies to doors"
        elif 'stair' in target:
            return "All buildings - applies to stairs"
        elif 'ramp' in target:
            return "All buildings - applies to ramps"
        elif 'window' in target:
            return "All buildings - applies to windows"
        
        return "All buildings and occupancies"
    
    def _get_historical_context(self, rule: Dict) -> Optional[str]:
        """Get historical context for why rule was created/updated."""
        # This could be expanded with a historical database
        provenance = rule.get('provenance', {})
        
        if provenance.get('regulation') == 'ADA':
            return "Part of the Americans with Disabilities Act (1990), establishing accessibility standards for public accommodations"
        elif provenance.get('regulation') == 'IBC':
            return "Part of International Building Code, ensuring life safety and structural integrity"
        elif provenance.get('regulation') == 'DIN':
            return "German building standard established to ensure accessibility and safety for all occupants"
        
        return None
    
    def generate_rule_explanation(self, rule: Dict, 
                                 applicable_elements: List[str],
                                 elements_checked: int,
                                 elements_passing: int,
                                 elements_failing: int) -> RuleExplanationResult:
        """
        Generate complete explanation for a rule with context.
        
        Args:
            rule: The rule dictionary
            applicable_elements: List of IFC element types this rule checks
            elements_checked: Total elements checked for this rule
            elements_passing: Elements that passed
            elements_failing: Elements that failed
            
        Returns:
            RuleExplanationResult with full context
        """
        justification = self.justify_rule(rule)
        
        return RuleExplanationResult(
            rule_id=rule.get('id', 'unknown'),
            rule_name=rule.get('name', 'Unnamed'),
            justification=justification,
            applicable_element_types=applicable_elements,
            total_elements_checked=elements_checked,
            elements_passing=elements_passing,
            elements_failing=elements_failing,
            similar_rules=[]  # Could be populated from rule relationships
        )
