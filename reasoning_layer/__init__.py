"""
Reasoning Layer

Provides explainability for compliance checking by answering:
1. "Why is this rule required?" - RuleJustifier
2. "Why did this element fail?" - ElementFailureAnalyzer
3. "How can we fix this?" - SolutionGenerator
"""

from reasoning_layer.models import (
    ReasoningResult,
    ReasoningType,
    RuleJustification,
    RegulatoryReference,
    FailureAnalysis,
    FailureMetrics,
    Solution,
    ElementFailureExplanation,
    RuleExplanationResult,
    SeverityLevel,
    reasoning_result_to_dict
)

from reasoning_layer.reasoning_justifier import RuleJustifier
from reasoning_layer.element_analyzer import ElementFailureAnalyzer
from reasoning_layer.solution_generator import SolutionGenerator
from reasoning_layer.reasoning_engine import ReasoningEngine

__all__ = [
    # Models
    'ReasoningResult',
    'ReasoningType',
    'RuleJustification',
    'RegulatoryReference',
    'FailureAnalysis',
    'FailureMetrics',
    'Solution',
    'ElementFailureExplanation',
    'RuleExplanationResult',
    'SeverityLevel',
    'reasoning_result_to_dict',
    
    # Components
    'RuleJustifier',
    'ElementFailureAnalyzer',
    'SolutionGenerator',
    'ReasoningEngine',
]
