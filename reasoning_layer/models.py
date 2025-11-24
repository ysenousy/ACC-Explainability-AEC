"""
Reasoning Layer Models

Defines data structures for explaining:
1. WHY rules exist (regulatory intent, safety, accessibility)
2. WHY elements failed (design analysis, alternatives)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class SeverityLevel(Enum):
    """Severity levels for issues and solutions."""
    CRITICAL = "critical"      # Safety/compliance risk
    HIGH = "high"              # Significant violation
    MEDIUM = "medium"          # Moderate concern
    LOW = "low"                # Minor issue
    INFO = "info"              # Informational


class ReasoningType(Enum):
    """Types of reasoning provided."""
    RULE_JUSTIFICATION = "rule_justification"      # Why rule exists
    FAILURE_ANALYSIS = "failure_analysis"          # Why element failed
    SOLUTION = "solution"                          # How to fix


@dataclass
class RegulatoryReference:
    """Reference to regulation, standard, or code."""
    standard: str              # e.g., "ADA", "IBC", "DIN"
    section: str               # e.g., "203.9", "1007.1"
    jurisdiction: str          # e.g., "USA", "Germany", "International"
    title: Optional[str] = None  # e.g., "Accessible Routes"
    url: Optional[str] = None  # Link to regulation
    year: Optional[int] = None # e.g., 2010 for ADA


@dataclass
class RuleJustification:
    """Explains WHY a rule exists and its regulatory intent."""
    # Required fields
    rule_id: str                           # Reference to rule
    rule_name: str                         # Human-readable rule name
    regulatory_intent: str                 # Core reason for rule (safety, accessibility, etc.)
    target_beneficiary: str                # Who benefits (elderly, disabled, general public)
    primary_regulation: RegulatoryReference  # Primary regulation backing
    explanation: str                       # Detailed "why" in plain language
    
    # Optional fields
    safety_concern: Optional[str] = None          # Safety risk addressed
    accessibility_concern: Optional[str] = None   # Accessibility issue addressed
    historical_context: Optional[str] = None      # Why this rule was created/updated
    
    # Optional with defaults
    related_regulations: List[RegulatoryReference] = field(default_factory=list)
    severity: SeverityLevel = SeverityLevel.MEDIUM
    applicability: str = "All buildings"   # When/where rule applies
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FailureMetrics:
    """Quantifies how an element failed."""
    actual_value: Any              # What the element actually has
    required_value: Any            # What it should have
    unit: str                      # Measurement unit (mm, degrees, etc.)
    
    # For numeric values
    deviation: Optional[float] = None  # actual - required
    deviation_percent: Optional[float] = None  # (actual - required) / required * 100
    
    # For categorical values
    mismatch_detail: Optional[str] = None  # Description of mismatch


@dataclass
class FailureAnalysis:
    """Explains WHY a specific element failed a rule."""
    # Required fields
    element_id: str                       # IFC element identifier
    element_type: str                     # e.g., "IfcDoor", "IfcStair"
    rule_id: str                          # Which rule it failed
    rule_name: str                        # Human-readable rule name
    failure_reason: str                   # Why element doesn't meet rule
    root_cause: str                       # Root cause (design error, constraint, etc.)
    metrics: FailureMetrics               # Quantify the failure
    severity: SeverityLevel               # How serious is this failure
    impact_on_users: str                  # How it affects building occupants
    
    # Optional fields
    element_name: Optional[str] = None           # Name in IFC model
    design_intent: Optional[str] = None          # What designer may have intended
    location: Optional[str] = None               # Where in building (e.g., "Room 101", "Level 2")
    related_elements: List[str] = field(default_factory=list)  # Other affected elements
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Solution:
    """Suggests how to fix a failure."""
    # Required fields
    failure_id: str                       # Which failure this solves
    element_id: str                       # Which element
    recommendation: str                   # Primary fix recommendation
    description: str                      # Detailed explanation of fix
    feasibility: str                      # "easy", "moderate", "complex"
    
    # Optional fields
    estimated_cost: Optional[str] = None         # Cost range (e.g., "low", "$1000-$5000")
    estimated_effort: Optional[str] = None       # Time estimate (e.g., "1 day", "1 week")
    design_implications: Optional[str] = None    # Side effects or cascading changes
    reasoning_detail: Optional[str] = None  # Why this solution is recommended
    
    # Optional with defaults
    implementation_steps: List[str] = field(default_factory=list)  # How to implement
    alternatives: List[Dict[str, str]] = field(default_factory=list)  # List of {name, description, pros, cons}
    potential_issues: List[str] = field(default_factory=list)  # Risks or trade-offs
    confidence: float = 0.85              # 0.0-1.0, how confident is this solution
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ElementFailureExplanation:
    """Complete explanation for why an element failed (combines analysis + solutions)."""
    # Required fields
    element_id: str
    element_type: str
    failed_rules: List[str]               # Which rules failed
    analyses: List[FailureAnalysis]       # Detailed "why" for each failure
    solutions: List[Solution]             # How to fix each failure
    total_failures: int
    critical_failures: int
    high_severity_failures: int
    compliance_impact: str                # How failures affect overall compliance
    
    # Optional fields
    element_name: Optional[str] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RuleExplanationResult:
    """Complete explanation for why a rule exists."""
    # Required fields
    rule_id: str
    rule_name: str
    justification: RuleJustification
    applicable_element_types: List[str]   # Which IFC types this rule applies to
    total_elements_checked: int
    elements_passing: int
    elements_failing: int
    
    # Optional with defaults
    similar_rules: List[str] = field(default_factory=list)  # Related rules
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ReasoningResult:
    """Top-level result containing all reasoning information."""
    reasoning_type: ReasoningType
    
    # For RULE_JUSTIFICATION
    rule_explanations: List[RuleExplanationResult] = field(default_factory=list)
    
    # For FAILURE_ANALYSIS
    element_explanations: List[ElementFailureExplanation] = field(default_factory=list)
    
    # Summary statistics
    total_rules_analyzed: int = 0
    total_failures_analyzed: int = 0
    total_solutions_provided: int = 0
    
    # Metadata
    ifc_file: Optional[str] = None
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# Helper functions for JSON serialization
def reasoning_result_to_dict(result: ReasoningResult) -> Dict:
    """Convert ReasoningResult to dictionary for JSON serialization."""
    return _asdict_with_enums(result)


def _asdict_with_enums(obj) -> Any:
    """Recursively convert dataclass to dict, handling Enums."""
    if isinstance(obj, dict):
        return {k: _asdict_with_enums(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_asdict_with_enums(item) for item in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, '__dataclass_fields__'):
        return {k: _asdict_with_enums(v) for k, v in asdict(obj).items()}
    else:
        return obj
