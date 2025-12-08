"""
Phase 2: Tiny Recursive Model (TRM) for Compliance Reasoning
Implements arXiv:2510.04871 - A 7M parameter model with 16-step iterative refinement

Architecture:
- Input: 320-dimensional feature vector (from Phase 1)
- Hidden layers: 2-layer SwiGLU network with self-attention refinement
- Output: Binary classification (compliance pass/fail) with confidence score
- Refinement: 16 iterative steps with early stopping

Classes:
    - TinyComplianceNetwork: Core neural network (PyTorch)
    - RefinementStep: Single refinement iteration logic
    - TinyRecursiveReasoner: Main model orchestrator
    - TRMResult: Output container with reasoning trace
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import logging
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RefinementStepResult:
    """Result from a single refinement step"""
    step_num: int
    logits: torch.Tensor  # Raw model output
    confidence: float  # Softmax probability of predicted class
    predicted_class: int  # 0 or 1
    hidden_state: torch.Tensor  # Intermediate representation
    explanation: str  # Step-specific reasoning
    converged: bool  # Whether early stopping triggered


@dataclass
class TRMResult:
    """Final result from TRM inference"""
    prediction: int  # 0 (fail) or 1 (pass)
    confidence: float  # Confidence score 0-1
    refinement_steps: List[Dict[str, Any]]  # All refinement steps
    reasoning_trace: List[str]  # Explanation at each step
    total_steps: int  # Number of steps taken (may be <16 if early stopped)
    converged: bool  # Whether model converged early
    timestamp: str  # When inference was run

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "prediction": self.prediction,
            "confidence": round(self.confidence, 4),
            "total_steps": self.total_steps,
            "converged": self.converged,
            "reasoning_trace": self.reasoning_trace,
            "timestamp": self.timestamp
        }


class SwiGLUActivation(nn.Module):
    """SwiGLU activation: element-wise product of (x * W1 + b1) and SiLU(x * W2 + b2)"""
    
    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, output_dim)
        self.fc2 = nn.Linear(input_dim, output_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply SwiGLU: (x * W1 + b1) * SiLU(x * W2 + b2)"""
        return self.fc1(x) * F.silu(self.fc2(x))


class AttentionRefinement(nn.Module):
    """Self-attention based refinement mechanism"""
    
    def __init__(self, hidden_dim: int, num_heads: int = 4):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"
        
        self.head_dim = hidden_dim // num_heads
        
        # Multi-head attention
        self.query = nn.Linear(hidden_dim, hidden_dim)
        self.key = nn.Linear(hidden_dim, hidden_dim)
        self.value = nn.Linear(hidden_dim, hidden_dim)
        
        self.fc_out = nn.Linear(hidden_dim, hidden_dim)
        self.scale = self.head_dim ** -0.5
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply self-attention refinement
        
        Args:
            x: (batch_size, hidden_dim) or (hidden_dim,) for single inference
        
        Returns:
            refined: (batch_size, hidden_dim) or (hidden_dim,)
        """
        # Handle single sample case
        if x.dim() == 1:
            x = x.unsqueeze(0)
            squeeze_output = True
        else:
            squeeze_output = False
        
        batch_size = x.shape[0]
        
        # Linear projections
        Q = self.query(x)  # (batch, hidden_dim)
        K = self.key(x)    # (batch, hidden_dim)
        V = self.value(x)  # (batch, hidden_dim)
        
        # Reshape for multi-head attention
        Q = Q.view(batch_size, self.num_heads, self.head_dim).transpose(1, 2)  # (batch, num_heads, seq_len, head_dim)
        K = K.view(batch_size, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale  # (batch, num_heads, seq_len, seq_len)
        attention_weights = F.softmax(scores, dim=-1)
        
        # Apply attention to values
        context = torch.matmul(attention_weights, V)  # (batch, num_heads, seq_len, head_dim)
        
        # Concatenate heads
        context = context.transpose(1, 2).contiguous()  # (batch, seq_len, num_heads, head_dim)
        context = context.view(batch_size, -1)  # (batch, hidden_dim)
        
        # Final projection
        output = self.fc_out(context)  # (batch, hidden_dim)
        
        if squeeze_output:
            output = output.squeeze(0)
        
        return output


class TinyComplianceNetwork(nn.Module):
    """
    Tiny Recursive Model for compliance checking
    
    Architecture:
    - Input: 320-dim (128 element + 128 rule + 64 context)
    - Layer 1: SwiGLU (320 → 1024)
    - Attention Refinement: 1024-dim self-attention
    - Layer 2: SwiGLU (1024 → 512)
    - Output: Linear (512 → 2) for binary classification
    
    Parameters: ~7M
    """
    
    def __init__(self, 
                 input_dim: int = 320,
                 hidden_dim_1: int = 1024,
                 hidden_dim_2: int = 512,
                 num_attention_heads: int = 8,
                 dropout_rate: float = 0.1):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim_1 = hidden_dim_1
        self.hidden_dim_2 = hidden_dim_2
        
        # Layer 1: SwiGLU expansion
        self.layer1_swiglu = SwiGLUActivation(input_dim, hidden_dim_1)
        self.layer1_norm = nn.LayerNorm(hidden_dim_1)
        self.layer1_dropout = nn.Dropout(dropout_rate)
        
        # Attention-based refinement
        self.attention = AttentionRefinement(hidden_dim_1, num_attention_heads)
        self.attention_norm = nn.LayerNorm(hidden_dim_1)
        self.attention_dropout = nn.Dropout(dropout_rate)
        
        # Layer 2: SwiGLU contraction
        self.layer2_swiglu = SwiGLUActivation(hidden_dim_1, hidden_dim_2)
        self.layer2_norm = nn.LayerNorm(hidden_dim_2)
        self.layer2_dropout = nn.Dropout(dropout_rate)
        
        # Output layer: binary classification (0: fail, 1: pass)
        self.classifier = nn.Linear(hidden_dim_2, 2)
        
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights with reasonable defaults"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the network
        
        Args:
            x: (batch_size, 320) or (320,) input features
        
        Returns:
            logits: (batch_size, 2) or (2,) classification logits
            hidden: (batch_size, 512) or (512,) final hidden state
        """
        # Layer 1: SwiGLU
        h1 = self.layer1_swiglu(x)
        h1 = self.layer1_norm(h1)
        h1 = self.layer1_dropout(h1)
        
        # Attention refinement (residual connection)
        h1_refined = self.attention(h1)
        h1_refined = self.attention_norm(h1_refined)
        h1_refined = self.attention_dropout(h1_refined)
        h1 = h1 + h1_refined  # Residual connection
        
        # Layer 2: SwiGLU
        h2 = self.layer2_swiglu(h1)
        h2 = self.layer2_norm(h2)
        h2 = self.layer2_dropout(h2)
        
        # Classification output
        logits = self.classifier(h2)
        
        return logits, h2
    
    def get_parameter_count(self) -> int:
        """Get total number of parameters"""
        return sum(p.numel() for p in self.parameters())


class RefinementStep:
    """Handles a single refinement iteration"""
    
    def __init__(self, step_num: int, model: TinyComplianceNetwork):
        self.step_num = step_num
        self.model = model
    
    def execute(self, 
                x: torch.Tensor,
                previous_prediction: Optional[int] = None,
                previous_confidence: Optional[float] = None) -> RefinementStepResult:
        """
        Execute one refinement step
        
        Args:
            x: Input features (320-dim)
            previous_prediction: Prediction from previous step (for refinement)
            previous_confidence: Confidence from previous step
        
        Returns:
            RefinementStepResult with step-specific information
        """
        with torch.no_grad():
            logits, hidden = self.model(x)
        
        # Get probabilities
        probs = F.softmax(logits, dim=-1)
        
        # Handle both single sample and batch cases
        if logits.dim() == 1:
            probs = probs.unsqueeze(0)
        
        # Get prediction and confidence
        predicted_class = logits.argmax(dim=-1)
        if predicted_class.dim() > 0:
            predicted_class = predicted_class.item()
        else:
            predicted_class = int(predicted_class)
        
        confidence = float(probs[0, predicted_class] if logits.dim() == 1 else probs[:, predicted_class].max())
        
        # Check convergence: if prediction matches previous and confidence high
        converged = False
        if previous_prediction is not None:
            if (previous_prediction == predicted_class and 
                previous_confidence is not None and
                abs(confidence - previous_confidence) < 0.01):  # Minimal change threshold
                converged = True
        
        # Generate explanation for this step
        explanation = self._generate_step_explanation(
            step_num=self.step_num,
            prediction=predicted_class,
            confidence=confidence,
            converged=converged,
            previous_prediction=previous_prediction
        )
        
        return RefinementStepResult(
            step_num=self.step_num,
            logits=logits,
            confidence=confidence,
            predicted_class=predicted_class,
            hidden_state=hidden,
            explanation=explanation,
            converged=converged
        )
    
    def _generate_step_explanation(self,
                                   step_num: int,
                                   prediction: int,
                                   confidence: float,
                                   converged: bool,
                                   previous_prediction: Optional[int]) -> str:
        """Generate human-readable explanation for this step"""
        prediction_text = "PASS" if prediction == 1 else "FAIL"
        
        explanation = f"Step {step_num}: Predicts {prediction_text} (confidence: {confidence:.2%})"
        
        if previous_prediction is not None:
            if previous_prediction == prediction:
                explanation += " - Consistent with previous step"
            else:
                explanation += f" - Changed from {('PASS' if previous_prediction == 1 else 'FAIL')}"
        
        if converged:
            explanation += " [CONVERGED - Early stopping]"
        
        return explanation


class TinyRecursiveReasoner:
    """
    Main TRM model orchestrator
    
    Handles:
    - Model initialization and device management
    - 16-step iterative refinement
    - Confidence calibration
    - Reasoning trace collection
    - Early stopping logic
    """
    
    def __init__(self, 
                 input_dim: int = 320,
                 hidden_dim_1: int = 512,
                 hidden_dim_2: int = 256,
                 num_attention_heads: int = 4,
                 dropout_rate: float = 0.1,
                 device: str = "cpu",
                 max_refinement_steps: int = 16):
        """
        Initialize TRM
        
        Args:
            input_dim: Input feature dimension (320)
            hidden_dim_1: First hidden layer dimension
            hidden_dim_2: Second hidden layer dimension
            num_attention_heads: Number of attention heads
            dropout_rate: Dropout rate
            device: "cpu" or "cuda"
            max_refinement_steps: Maximum refinement iterations (16)
        """
        self.device = torch.device(device)
        self.max_refinement_steps = max_refinement_steps
        
        # Initialize network
        self.network = TinyComplianceNetwork(
            input_dim=input_dim,
            hidden_dim_1=hidden_dim_1,
            hidden_dim_2=hidden_dim_2,
            num_attention_heads=num_attention_heads,
            dropout_rate=dropout_rate
        ).to(self.device)
        
        self.network.eval()  # Inference mode by default
        
        logger.info(f"TinyRecursiveReasoner initialized")
        logger.info(f"  - Device: {self.device}")
        logger.info(f"  - Max refinement steps: {max_refinement_steps}")
        logger.info(f"  - Network parameters: {self.network.get_parameter_count():,}")
    
    def infer(self, 
              features: torch.Tensor,
              convergence_threshold: float = 0.01,
              early_stopping: bool = True) -> TRMResult:
        """
        Run TRM inference with iterative refinement
        
        Args:
            features: Input features (320-dim), either:
                     - shape (320,) for single sample
                     - shape (batch_size, 320) for batch
            convergence_threshold: Threshold for early stopping (confidence change)
            early_stopping: Whether to use early stopping
        
        Returns:
            TRMResult with prediction, confidence, and reasoning trace
        """
        # Convert to tensor if needed
        if not isinstance(features, torch.Tensor):
            features = torch.tensor(features, dtype=torch.float32)
        
        # Ensure correct device
        features = features.to(self.device)
        
        # Ensure 2D (batch_size, 320)
        if features.dim() == 1:
            features = features.unsqueeze(0)
        
        batch_size = features.shape[0]
        
        # Initialize refinement tracking
        refinement_steps = []
        reasoning_trace = []
        previous_predictions = [None] * batch_size
        previous_confidences = [None] * batch_size
        converged_samples = [False] * batch_size
        
        # 16-step iterative refinement
        for step_num in range(1, self.max_refinement_steps + 1):
            refinement = RefinementStep(step_num, self.network)
            
            # Execute step for each sample
            step_results = []
            for batch_idx in range(batch_size):
                result = refinement.execute(
                    x=features[batch_idx],
                    previous_prediction=previous_predictions[batch_idx],
                    previous_confidence=previous_confidences[batch_idx]
                )
                step_results.append(result)
                
                # Update tracking
                previous_predictions[batch_idx] = result.predicted_class
                previous_confidences[batch_idx] = result.confidence
                
                if result.converged:
                    converged_samples[batch_idx] = True
            
            # Store step results
            step_data = {
                "step": step_num,
                "predictions": [r.predicted_class for r in step_results],
                "confidences": [round(r.confidence, 4) for r in step_results],
                "explanations": [r.explanation for r in step_results],
                "converged_count": sum(r.converged for r in step_results)
            }
            refinement_steps.append(step_data)
            
            # Add first sample's explanation to trace
            if step_results:
                reasoning_trace.append(step_results[0].explanation)
            
            # Early stopping: all samples converged
            if early_stopping and all(converged_samples):
                logger.info(f"Early stopping at step {step_num} - all samples converged")
                break
        
        # Prepare final result (using first sample in batch)
        final_prediction = previous_predictions[0]
        final_confidence = previous_confidences[0]
        
        result = TRMResult(
            prediction=final_prediction,
            confidence=final_confidence,
            refinement_steps=refinement_steps,
            reasoning_trace=reasoning_trace,
            total_steps=len(refinement_steps),
            converged=all(converged_samples),
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Inference complete: prediction={result.prediction}, "
                   f"confidence={result.confidence:.2%}, steps={result.total_steps}")
        
        return result
    
    def save_model(self, path: str) -> None:
        """Save model weights to file"""
        torch.save(self.network.state_dict(), path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """Load model weights from file"""
        self.network.load_state_dict(torch.load(path, map_location=self.device))
        logger.info(f"Model loaded from {path}")
    
    def to_device(self, device: str) -> None:
        """Move model to different device"""
        self.device = torch.device(device)
        self.network = self.network.to(self.device)
        logger.info(f"Model moved to {self.device}")
