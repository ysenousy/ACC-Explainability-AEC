"""
AI Assistant - Integrated into Reasoning Layer
Uses TRM (TinyRecursiveReasoner) to generate AI-powered explanations for compliance failures.

This module provides AI-powered explanations using the trained TRM model,
allowing users to see confidence scores and step-by-step reasoning.
"""

import logging
from typing import Dict, Any, Optional
from reasoning_layer.tiny_recursive_reasoner import TinyRecursiveReasoner

logger = logging.getLogger(__name__)


class AIAssistant:
    """
    AI-powered explanation system using TinyRecursiveReasoner (TRM).
    
    Generates explanations for compliance failures using the trained TRM model.
    Provides confidence scores and step-by-step reasoning traces.
    """
    
    def __init__(self):
        """Initialize AI Assistant with TRM model."""
        try:
            self.trm = TinyRecursiveReasoner()
            self.logger = logging.getLogger(__name__)
            self.logger.info("AI Assistant initialized with TRM model")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Assistant: {e}")
            raise
    
    def explain_with_ai(self, 
                       element: Dict[str, Any], 
                       failure: Dict[str, Any], 
                       rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered explanation for a compliance failure.
        
        Uses the TRM model to analyze the failure and provide:
        - Prediction (PASS/FAIL)
        - Confidence score
        - Human-readable explanation
        - Step-by-step reasoning trace
        
        Args:
            element: Element data from the building model
            failure: Failure data from compliance check
            rule: Rule that was violated
            
        Returns:
            Dictionary with:
                - success: bool
                - prediction: str (PASS or FAIL)
                - confidence: float (0-1)
                - explanation: str (human-readable)
                - reasoning_steps: list[str] (16-step trace)
                - steps_taken: int (actual steps used, may be <16)
                - converged: bool (whether early stopping triggered)
                - model_version: str
        """
        try:
            # Extract features for TRM
            features = self._extract_features(element, failure, rule)
            
            if features is None:
                return {
                    "success": False,
                    "error": "Failed to extract features from failure data"
                }
            
            # Run TRM inference
            trm_result = self.trm.infer(features)
            
            # Convert TRM output to user-friendly explanation
            explanation = self._format_explanation(
                trm_result=trm_result,
                failure=failure,
                rule=rule
            )
            
            return {
                "success": True,
                "prediction": "PASS" if trm_result.prediction == 1 else "FAIL",
                "confidence": round(trm_result.confidence, 3),
                "explanation": explanation,
                "reasoning_steps": trm_result.reasoning_trace,
                "steps_taken": trm_result.total_steps,
                "converged": trm_result.converged,
                "model_version": "TRM-v1"
            }
            
        except Exception as e:
            self.logger.error(f"AI Assistant error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_features(self, 
                         element: Dict[str, Any], 
                         failure: Dict[str, Any], 
                         rule: Dict[str, Any]) -> Optional[object]:
        """
        Extract 320-dimensional feature vector for TRM.
        
        Combines element properties, failure characteristics, and rule requirements
        into a normalized feature vector that TRM can process.
        
        Args:
            element: Element data
            failure: Failure data
            rule: Rule data
            
        Returns:
            Feature tensor or None if extraction fails
        """
        try:
            # Reuse existing feature extraction from trm_data_extractor
            from backend.trm_data_extractor import TRMDataExtractor
            
            extractor = TRMDataExtractor()
            features = extractor.extract_features(element, failure, rule)
            
            return features
            
        except ImportError:
            self.logger.warning("TRMDataExtractor not available, using fallback feature extraction")
            return self._fallback_extract_features(element, failure, rule)
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            return None
    
    def _fallback_extract_features(self,
                                   element: Dict[str, Any],
                                   failure: Dict[str, Any],
                                   rule: Dict[str, Any]) -> Optional[object]:
        """
        Fallback feature extraction if TRMDataExtractor is unavailable.
        
        Creates a basic 320-dimensional feature vector from available data.
        """
        try:
            import torch
            import numpy as np
            
            # Initialize 320-dim feature vector
            features = np.zeros(320, dtype=np.float32)
            
            # Extract numeric features from element
            idx = 0
            element_properties = element.get('properties', {})
            for key, value in element_properties.items():
                if isinstance(value, (int, float)) and idx < 100:
                    features[idx] = float(value)
                    idx += 1
            
            # Extract numeric features from failure
            idx = 100
            if failure.get('actual_value'):
                features[idx] = float(failure.get('actual_value', 0))
                idx += 1
            if failure.get('required_value'):
                features[idx] = float(failure.get('required_value', 0))
                idx += 1
            
            # Extract rule features
            idx = 150
            rule_properties = rule.get('condition', {})
            if isinstance(rule_properties, dict):
                for key, value in rule_properties.items():
                    if isinstance(value, (int, float)) and idx < 320:
                        features[idx] = float(value)
                        idx += 1
            
            # Normalize features to [-1, 1] range
            max_val = np.max(np.abs(features))
            if max_val > 0:
                features = features / max_val
            
            return torch.from_numpy(features).float()
            
        except Exception as e:
            self.logger.error(f"Fallback feature extraction failed: {e}")
            return None
    
    def _format_explanation(self,
                           trm_result: Any,
                           failure: Dict[str, Any],
                           rule: Dict[str, Any]) -> str:
        """
        Convert TRM output to human-readable explanation.
        
        Takes the TRM model's prediction and reasoning trace,
        then formats it into clear, actionable explanation text.
        
        Args:
            trm_result: TRM inference result with prediction, confidence, trace
            failure: Failure data (for context)
            rule: Rule data (for context)
            
        Returns:
            Human-readable explanation string
        """
        try:
            # Determine prediction text
            pred_text = "PASS" if trm_result.prediction == 1 else "FAIL"
            
            # Build steps summary
            steps_info = f"Analyzed in {trm_result.total_steps} step(s)"
            if trm_result.converged:
                steps_info += " (converged early)"
            
            # Build explanation narrative
            explanation = (
                f"AI Model Prediction: {pred_text}\n"
                f"Confidence Level: {trm_result.confidence:.0%}\n"
                f"Analysis: {steps_info}\n\n"
            )
            
            # Add context from failure
            if failure.get('element_type'):
                explanation += f"Element Type: {failure.get('element_type')}\n"
            if failure.get('actual_value') is not None:
                explanation += f"Actual Value: {failure.get('actual_value')}\n"
            if failure.get('required_value') is not None:
                explanation += f"Required Value: {failure.get('required_value')}\n"
            
            explanation += "\n"
            
            # Add reasoning summary
            if trm_result.reasoning_trace:
                explanation += "Reasoning Summary:\n"
                
                # Add first step
                explanation += f"• Initial Assessment: {trm_result.reasoning_trace[0]}\n"
                
                # Add middle step if available
                if len(trm_result.reasoning_trace) > 2:
                    mid_idx = len(trm_result.reasoning_trace) // 2
                    explanation += f"• Mid-Analysis: {trm_result.reasoning_trace[mid_idx]}\n"
                
                # Add final step
                if len(trm_result.reasoning_trace) > 1:
                    explanation += f"• Final Conclusion: {trm_result.reasoning_trace[-1]}"
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"Explanation formatting error: {e}")
            return f"AI Model predicts: {pred_text} (Confidence: {trm_result.confidence:.0%})"


# Module-level initialization (lazy loading)
_ai_assistant_instance = None


def get_ai_assistant() -> AIAssistant:
    """
    Get or create singleton instance of AI Assistant.
    
    Returns:
        AIAssistant instance
    """
    global _ai_assistant_instance
    if _ai_assistant_instance is None:
        _ai_assistant_instance = AIAssistant()
    return _ai_assistant_instance
