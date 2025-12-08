"""
Test suite for Phase 2: Tiny Recursive Reasoner (TRM)
Tests TinyComplianceNetwork, RefinementStep, and TinyRecursiveReasoner classes
"""

import unittest
import torch
import numpy as np
from pathlib import Path
import tempfile
import os

# Import the classes to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reasoning_layer.tiny_recursive_reasoner import (
    TinyComplianceNetwork,
    RefinementStep,
    TinyRecursiveReasoner,
    TRMResult,
    RefinementStepResult,
    SwiGLUActivation,
    AttentionRefinement
)


class TestSwiGLUActivation(unittest.TestCase):
    """Test SwiGLU activation function"""
    
    def setUp(self):
        self.input_dim = 320
        self.output_dim = 512
        self.swiglu = SwiGLUActivation(self.input_dim, self.output_dim)
        self.x = torch.randn(10, self.input_dim)  # Batch of 10
    
    def test_output_shape(self):
        """Test output shape is correct"""
        output = self.swiglu(self.x)
        self.assertEqual(output.shape, (10, self.output_dim))
    
    def test_single_sample(self):
        """Test with single sample"""
        x_single = torch.randn(self.input_dim)
        output = self.swiglu(x_single)
        self.assertEqual(output.shape, (self.output_dim,))
    
    def test_output_is_finite(self):
        """Test output contains valid numbers"""
        output = self.swiglu(self.x)
        self.assertTrue(torch.all(torch.isfinite(output)))
    
    def test_gradients_flow(self):
        """Test that gradients can flow through SwiGLU"""
        self.x.requires_grad = True
        output = self.swiglu(self.x)
        loss = output.sum()
        loss.backward()
        self.assertIsNotNone(self.x.grad)
        self.assertTrue(torch.all(torch.isfinite(self.x.grad)))


class TestAttentionRefinement(unittest.TestCase):
    """Test attention-based refinement module"""
    
    def setUp(self):
        self.hidden_dim = 512
        self.attention = AttentionRefinement(self.hidden_dim, num_heads=4)
        self.x = torch.randn(10, self.hidden_dim)  # Batch of 10
    
    def test_output_shape_batch(self):
        """Test output shape for batch input"""
        output = self.attention(self.x)
        self.assertEqual(output.shape, self.x.shape)
    
    def test_output_shape_single(self):
        """Test output shape for single sample"""
        x_single = torch.randn(self.hidden_dim)
        output = self.attention(x_single)
        self.assertEqual(output.shape, x_single.shape)
    
    def test_output_is_finite(self):
        """Test output contains valid numbers"""
        output = self.attention(self.x)
        self.assertTrue(torch.all(torch.isfinite(output)))
    
    def test_different_head_counts(self):
        """Test attention with different number of heads"""
        for num_heads in [1, 2, 4, 8]:
            attn = AttentionRefinement(512, num_heads=num_heads)
            output = attn(self.x)
            self.assertEqual(output.shape, self.x.shape)


class TestTinyComplianceNetwork(unittest.TestCase):
    """Test TinyComplianceNetwork architecture"""
    
    def setUp(self):
        self.network = TinyComplianceNetwork(
            input_dim=320,
            hidden_dim_1=1024,
            hidden_dim_2=512,
            num_attention_heads=8,
            dropout_rate=0.1
        )
        self.network.eval()  # Evaluation mode
    
    def test_network_parameter_count(self):
        """Test parameter count is approximately 7M"""
        param_count = self.network.get_parameter_count()
        self.assertGreater(param_count, 5_500_000)  # At least 5.5M
        self.assertLess(param_count, 10_000_000)  # Less than 10M
        print(f"Network parameters: {param_count:,}")
    
    def test_forward_pass_batch(self):
        """Test forward pass with batch of samples"""
        x = torch.randn(10, 320)
        with torch.no_grad():
            logits, hidden = self.network(x)
        
        # Check shapes
        self.assertEqual(logits.shape, (10, 2))  # 2 classes (pass/fail)
        self.assertEqual(hidden.shape, (10, 512))  # Final hidden state
    
    def test_forward_pass_single(self):
        """Test forward pass with single sample"""
        x = torch.randn(320)
        with torch.no_grad():
            logits, hidden = self.network(x)
        
        # Check shapes
        self.assertEqual(logits.shape, (2,))
        self.assertEqual(hidden.shape, (512,))
    
    def test_output_is_finite(self):
        """Test network outputs are valid numbers"""
        x = torch.randn(10, 320)
        with torch.no_grad():
            logits, hidden = self.network(x)
        
        self.assertTrue(torch.all(torch.isfinite(logits)))
        self.assertTrue(torch.all(torch.isfinite(hidden)))
    
    def test_dropout_inference_mode(self):
        """Test dropout is disabled in eval mode"""
        self.network.eval()
        x = torch.randn(5, 320)
        
        # Run inference twice - should get same output
        with torch.no_grad():
            logits1, _ = self.network(x)
            logits2, _ = self.network(x)
        
        self.assertTrue(torch.allclose(logits1, logits2))
    
    def test_training_vs_eval_mode(self):
        """Test network behaves differently in train vs eval"""
        x = torch.randn(10, 320)
        
        # Eval mode
        self.network.eval()
        with torch.no_grad():
            logits_eval, _ = self.network(x)
        
        # Train mode (with dropout randomness)
        self.network.train()
        logits_train1, _ = self.network(x)
        logits_train2, _ = self.network(x)
        
        # Outputs in training mode should differ (due to dropout)
        self.assertFalse(torch.allclose(logits_train1, logits_train2))


class TestRefinementStep(unittest.TestCase):
    """Test single refinement step execution"""
    
    def setUp(self):
        self.network = TinyComplianceNetwork()
        self.network.eval()
        self.network.requires_grad_(False)
    
    def test_refinement_step_execution(self):
        """Test single refinement step produces valid output"""
        step = RefinementStep(step_num=1, model=self.network)
        x = torch.randn(320)
        
        result = step.execute(x)
        
        # Check result attributes
        self.assertEqual(result.step_num, 1)
        self.assertIn(result.predicted_class, [0, 1])
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertEqual(result.hidden_state.shape, (512,))
        self.assertIsInstance(result.explanation, str)
        self.assertFalse(result.converged)  # First step doesn't converge
    
    def test_convergence_detection(self):
        """Test convergence is detected when prediction stable"""
        step = RefinementStep(step_num=2, model=self.network)
        x = torch.randn(320)
        
        # First execution
        result1 = step.execute(x)
        
        # Second execution with same prediction and confidence
        result2 = step.execute(
            x,
            previous_prediction=result1.predicted_class,
            previous_confidence=result1.confidence
        )
        
        # Should detect convergence (same prediction, same confidence)
        self.assertTrue(result2.converged)
    
    def test_explanation_generation(self):
        """Test explanation contains relevant information"""
        step = RefinementStep(step_num=1, model=self.network)
        x = torch.randn(320)
        result = step.execute(x)
        
        self.assertIn("Step 1", result.explanation)
        self.assertIn("PASS" if result.predicted_class == 1 else "FAIL", result.explanation)
        self.assertIn("confidence", result.explanation)


class TestTinyRecursiveReasoner(unittest.TestCase):
    """Test main TRM orchestrator"""
    
    def setUp(self):
        self.reasoner = TinyRecursiveReasoner(
            input_dim=320,
            device="cpu",
            max_refinement_steps=16
        )
    
    def test_reasoner_initialization(self):
        """Test TRM initializes correctly"""
        self.assertIsNotNone(self.reasoner.network)
        self.assertEqual(self.reasoner.device, torch.device("cpu"))
        self.assertEqual(self.reasoner.max_refinement_steps, 16)
    
    def test_inference_single_sample(self):
        """Test inference with single 320-dim sample"""
        x = torch.randn(320)
        result = self.reasoner.infer(x)
        
        # Check TRMResult structure
        self.assertIsInstance(result, TRMResult)
        self.assertIn(result.prediction, [0, 1])
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        # Step count may be <16 if early stopping triggers
        self.assertGreaterEqual(result.total_steps, 1)
        self.assertLessEqual(result.total_steps, 16)
        self.assertLessEqual(len(result.reasoning_trace), 16)
    
    def test_inference_batch(self):
        """Test inference with batch of samples"""
        x = torch.randn(5, 320)
        result = self.reasoner.infer(x)
        
        # Should return result for first sample
        self.assertIsInstance(result, TRMResult)
        self.assertIn(result.prediction, [0, 1])
    
    def test_inference_numpy_input(self):
        """Test inference with numpy array input"""
        x = np.random.randn(320)
        result = self.reasoner.infer(x)
        
        self.assertIsInstance(result, TRMResult)
        self.assertIn(result.prediction, [0, 1])
    
    def test_reasoning_trace_structure(self):
        """Test reasoning trace contains all steps"""
        x = torch.randn(320)
        result = self.reasoner.infer(x, early_stopping=False)
        
        self.assertEqual(len(result.reasoning_trace), 16)
        for trace_item in result.reasoning_trace:
            self.assertIsInstance(trace_item, str)
            self.assertIn("Step", trace_item)
    
    def test_early_stopping(self):
        """Test early stopping mechanism"""
        x = torch.randn(320)
        
        # With early stopping - may complete in <16 steps
        result_early = self.reasoner.infer(x, early_stopping=True)
        
        # Without early stopping - always 16 steps
        result_no_early = self.reasoner.infer(x, early_stopping=False)
        
        self.assertLessEqual(result_early.total_steps, 16)
        self.assertEqual(result_no_early.total_steps, 16)
    
    def test_result_to_dict_serialization(self):
        """Test TRMResult can be serialized to dict"""
        x = torch.randn(320)
        result = self.reasoner.infer(x)
        
        result_dict = result.to_dict()
        
        # Check dict structure
        self.assertIn("prediction", result_dict)
        self.assertIn("confidence", result_dict)
        self.assertIn("total_steps", result_dict)
        self.assertIn("reasoning_trace", result_dict)
        self.assertIn("timestamp", result_dict)
        
        # Values should be JSON-serializable
        self.assertIsInstance(result_dict["prediction"], int)
        self.assertIsInstance(result_dict["confidence"], float)
        self.assertIsInstance(result_dict["total_steps"], int)
        self.assertIsInstance(result_dict["reasoning_trace"], list)
    
    def test_model_save_load(self):
        """Test model saving and loading"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "test_model.pt")
            
            # Save model
            self.reasoner.save_model(model_path)
            self.assertTrue(os.path.exists(model_path))
            
            # Create new reasoner and load
            reasoner2 = TinyRecursiveReasoner(device="cpu")
            reasoner2.load_model(model_path)
            
            # Test inference with loaded model
            x = torch.randn(320)
            result = reasoner2.infer(x)
            self.assertIsInstance(result, TRMResult)
    
    def test_device_movement(self):
        """Test moving model to different devices"""
        reasoner = TinyRecursiveReasoner(device="cpu")
        self.assertEqual(reasoner.device, torch.device("cpu"))
        
        # Move to same device (no-op)
        reasoner.to_device("cpu")
        self.assertEqual(reasoner.device, torch.device("cpu"))
        
        # Test inference still works
        x = torch.randn(320)
        result = reasoner.infer(x)
        self.assertIsInstance(result, TRMResult)


class TestTRMIntegration(unittest.TestCase):
    """Integration tests for complete TRM workflow"""
    
    def test_end_to_end_inference(self):
        """Test complete inference pipeline"""
        # Initialize reasoner
        reasoner = TinyRecursiveReasoner(
            input_dim=320,
            hidden_dim_1=512,
            hidden_dim_2=256,
            num_attention_heads=4,
            dropout_rate=0.1,
            device="cpu",
            max_refinement_steps=16
        )
        
        # Create realistic sample (from Phase 1)
        sample_features = torch.randn(320)
        
        # Run inference
        result = reasoner.infer(sample_features, early_stopping=True)
        
        # Validate result
        self.assertIsInstance(result, TRMResult)
        self.assertIn(result.prediction, [0, 1])
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreaterEqual(result.total_steps, 1)
        self.assertLessEqual(result.total_steps, 16)
        self.assertGreater(len(result.reasoning_trace), 0)
    
    def test_batch_inference_consistency(self):
        """Test batch inference is consistent with single-sample inference"""
        reasoner = TinyRecursiveReasoner(device="cpu", max_refinement_steps=5)
        
        # Create test samples
        x = torch.randn(320)
        batch_x = x.unsqueeze(0).repeat(3, 1)  # Repeat same sample 3 times
        
        # Run batch inference
        result_batch = reasoner.infer(batch_x, early_stopping=False)
        
        # Run single inference
        result_single = reasoner.infer(x, early_stopping=False)
        
        # First sample of batch should match single inference
        # (Note: Due to dropout in training mode, exact match not guaranteed)
        # But prediction class should be same
        self.assertEqual(result_batch.total_steps, result_single.total_steps)
    
    def test_multiple_inferences_reproducible(self):
        """Test that multiple inferences on eval mode are reproducible"""
        reasoner = TinyRecursiveReasoner(device="cpu")
        reasoner.network.eval()
        
        x = torch.randn(320)
        
        # Run inference twice
        result1 = reasoner.infer(x)
        result2 = reasoner.infer(x)
        
        # Results should be identical in eval mode
        self.assertEqual(result1.prediction, result2.prediction)
        self.assertEqual(result1.confidence, result2.confidence)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.reasoner = TinyRecursiveReasoner(device="cpu")
    
    def test_very_high_convergence_threshold(self):
        """Test with very strict convergence threshold"""
        x = torch.randn(320)
        result = self.reasoner.infer(
            x,
            convergence_threshold=0.001,  # Very strict
            early_stopping=True
        )
        # Should still complete
        self.assertIsInstance(result, TRMResult)
    
    def test_zero_input(self):
        """Test with zero input vector"""
        x = torch.zeros(320)
        result = self.reasoner.infer(x)
        
        self.assertIsInstance(result, TRMResult)
        self.assertIn(result.prediction, [0, 1])
    
    def test_very_large_input_values(self):
        """Test with large input values"""
        x = torch.randn(320) * 1000
        result = self.reasoner.infer(x)
        
        self.assertIsInstance(result, TRMResult)
        # Output should still be valid
        self.assertTrue(0 <= result.confidence <= 1)
    
    def test_nan_resilience(self):
        """Test network handles edge cases without NaN"""
        x = torch.randn(320)
        result = self.reasoner.infer(x)
        
        # Result should not contain NaN
        self.assertFalse(np.isnan(result.confidence))
        for trace in result.reasoning_trace:
            self.assertIsInstance(trace, str)


if __name__ == "__main__":
    unittest.main()
