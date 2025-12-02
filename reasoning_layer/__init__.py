"""
Reasoning Layer

Provides explainability for compliance checking by answering:
1. "Why did this fail?" - FailureExplainer
2. "What is the impact?" - ImpactAnalyzer
3. "How can we fix this?" - RecommendationEngine
"""

from reasoning_layer.models import (
    ReasoningResult,
    SeverityLevel,
    FailureExplanation,
    FailureContext,
    RegulatoryReference,
    ImpactMetrics,
    Recommendation,
    RecommendationSet,
    RecommendationEffort,
    RootCause,
    reasoning_result_to_dict
)

from reasoning_layer.config import ReasoningConfig, BaseReasoningEngine
from reasoning_layer.failure_explainer import FailureExplainer
from reasoning_layer.impact_analyzer import ImpactAnalyzer
from reasoning_layer.recommendation_engine import RecommendationEngine
from reasoning_layer.reasoning_engine import ReasoningEngine

__all__ = [
    # Models
    'ReasoningResult',
    'SeverityLevel',
    'FailureExplanation',
    'FailureContext',
    'RegulatoryReference',
    'ImpactMetrics',
    'Recommendation',
    'RecommendationSet',
    'RecommendationEffort',
    'RootCause',
    'reasoning_result_to_dict',
    
    # Configuration
    'ReasoningConfig',
    'BaseReasoningEngine',
    
    # Components
    'FailureExplainer',
    'ImpactAnalyzer',
    'RecommendationEngine',
    'ReasoningEngine',
]
