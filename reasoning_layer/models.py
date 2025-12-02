"""
Data models for the Reasoning Layer.

Provides structured representations for reasoning results, failure analysis,
impact metrics, and recommendations.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional
from enum import Enum
import json


class SeverityLevel(str, Enum):
    """Severity levels for compliance failures."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RecommendationEffort(str, Enum):
    """Effort levels for implementing recommendations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class RegulatoryReference:
    """Reference to regulatory source."""
    regulation: str
    section: str
    jurisdiction: str
    source_link: Optional[str] = None


@dataclass
class FailureContext:
    """Context information about a failure."""
    element_id: str
    element_type: str
    element_name: str
    actual_value: Any
    required_value: Any
    unit: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureExplanation:
    """Explanation of why a rule failed."""
    rule_id: str
    rule_name: str
    failure_type: str  # e.g., "dimension_violation", "missing_property", "invalid_configuration"
    short_explanation: str
    detailed_explanation: str
    context: FailureContext
    regulatory_reference: RegulatoryReference
    affected_property: str
    severity: SeverityLevel


@dataclass
class ImpactMetrics:
    """Metrics about the impact of failures."""
    total_affected_elements: int
    affected_by_type: Dict[str, int]  # e.g., {"IfcDoor": 5, "IfcWindow": 3}
    percentage_of_building: float
    failure_distribution: Dict[str, int]  # By severity
    cost_estimate_range: Optional[str] = None  # e.g., "$10,000 - $50,000"
    implementation_timeline: Optional[str] = None  # e.g., "1-2 weeks"


@dataclass
class Recommendation:
    """A single recommendation for fixing failures."""
    title: str
    description: str
    implementation_steps: List[str]
    estimated_effort: RecommendationEffort
    estimated_cost: Optional[str] = None
    affected_elements: int = 0
    regulatory_pathway: Optional[str] = None


@dataclass
class RecommendationSet:
    """Set of tiered recommendations."""
    quick_fixes: List[Recommendation] = field(default_factory=list)
    medium_fixes: List[Recommendation] = field(default_factory=list)
    comprehensive_fixes: List[Recommendation] = field(default_factory=list)
    systemic_fixes: List[Recommendation] = field(default_factory=list)


@dataclass
class RootCause:
    """Root cause analysis result."""
    cause_id: str
    description: str
    affected_elements: int
    affected_rules: List[str]
    systemic: bool  # Whether this is a systemic issue affecting multiple elements


@dataclass
class ReasoningTab:
    """Tab result for a reasoning layer view."""
    tab_name: str  # "Why It Failed", "Impact Assessment", "How to Fix", etc.
    content: Dict[str, Any]
    data: Any


@dataclass
class ReasoningResult:
    """Complete reasoning analysis result."""
    element_id: str
    element_type: str
    element_name: str
    
    # Why it failed
    failure_explanations: List[FailureExplanation] = field(default_factory=list)
    
    # Impact
    impact_metrics: Optional[ImpactMetrics] = None
    
    # How to fix
    recommendations: Optional[RecommendationSet] = None
    
    # Root causes
    root_causes: List[RootCause] = field(default_factory=list)
    
    # Metadata
    analysis_timestamp: str = ""
    total_failed_rules: int = 0
    

def reasoning_result_to_dict(result: ReasoningResult) -> Dict[str, Any]:
    """Convert ReasoningResult to dictionary for JSON serialization."""
    return asdict(result)
