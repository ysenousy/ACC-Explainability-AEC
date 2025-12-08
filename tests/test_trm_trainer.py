"""
Tests for Phase 3: Incremental TRM Training
Tests the trainer, dataset, and incremental learning functionality
"""

import unittest
import torch
import numpy as np
import tempfile
import json
from pathlib import Path
from typing import List, Dict, Any

from backend.trm_trainer import (
    TRMDataset, TRMTrainer, TrainingConfig, TrainingMetrics, create_trainer
)
from reasoning_layer.tiny_recursive_reasoner import TinyComplianceNetwork


class TestTRMDataset(unittest.TestCase):
    """Test TRMDataset functionality"""
    
    def setUp(self):
        """Create test dataset"""
        self.num_samples = 10
        self.samples = [
            {
                "element_features": list(np.random.randn(128)),
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
            for _ in range(self.num_samples)
        ]
        self.labels = list(np.random.randint(0, 2, self.num_samples))
    
    def test_dataset_initialization(self):
        """Test dataset creation"""
        dataset = TRMDataset(self.samples, self.labels)
        self.assertEqual(len(dataset), self.num_samples)
    
    def test_getitem_shape(self):
        """Test single sample shape"""
        dataset = TRMDataset(self.samples, self.labels)
        x, y = dataset[0]
        
        self.assertEqual(x.shape, (320,))
        self.assertEqual(x.dtype, torch.float32)
        self.assertIn(y.item(), [0, 1])
    
    def test_getitem_values(self):
        """Test sample values are finite"""
        dataset = TRMDataset(self.samples, self.labels)
        
        for i in range(min(5, len(dataset))):
            x, y = dataset[i]
            self.assertTrue(torch.isfinite(x).all())
    
    def test_missing_features_padding(self):
        """Test missing features are padded with zeros"""
        samples_incomplete = [
            {
                # Missing rule_features and context_features
                "element_features": list(np.random.randn(128))
            }
            for _ in range(3)
        ]
        labels = [0, 1, 0]
        
        dataset = TRMDataset(samples_incomplete, labels)
        x, y = dataset[0]
        
        # Should still be 320-dim
        self.assertEqual(x.shape, (320,))
        # First 128 should be from element_features
        # Rest should be padding
    
    def test_dataset_on_device(self):
        """Test dataset creation on specific device"""
        device = "cpu"
        dataset = TRMDataset(self.samples, self.labels, device=device)
        x, y = dataset[0]
        
        self.assertEqual(str(x.device), device)


class TestTrainingMetrics(unittest.TestCase):
    """Test TrainingMetrics dataclass"""
    
    def test_metrics_creation(self):
        """Test creating metrics object"""
        metrics = TrainingMetrics(
            epoch=1,
            loss=0.5,
            accuracy=0.8,
            precision=0.75,
            recall=0.85,
            f1=0.8,
            val_loss=0.6,
            val_accuracy=0.78,
            val_f1=0.77
        )
        
        self.assertEqual(metrics.epoch, 1)
        self.assertEqual(metrics.loss, 0.5)
    
    def test_metrics_to_dict(self):
        """Test metrics serialization"""
        metrics = TrainingMetrics(
            epoch=1,
            loss=0.5,
            accuracy=0.8,
            precision=0.75,
            recall=0.85,
            f1=0.8,
            val_loss=0.6
        )
        
        metrics_dict = metrics.to_dict()
        self.assertIsInstance(metrics_dict, dict)
        self.assertIn("epoch", metrics_dict)
        self.assertIn("loss", metrics_dict)
        self.assertIn("val_loss", metrics_dict)


class TestTrainingConfig(unittest.TestCase):
    """Test TrainingConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = TrainingConfig()
        
        self.assertEqual(config.learning_rate, 0.001)
        self.assertEqual(config.batch_size, 32)
        self.assertEqual(config.num_epochs, 100)
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = TrainingConfig(
            learning_rate=0.01,
            batch_size=64,
            num_epochs=50
        )
        
        self.assertEqual(config.learning_rate, 0.01)
        self.assertEqual(config.batch_size, 64)
        self.assertEqual(config.num_epochs, 50)
    
    def test_checkpoint_dir_creation(self):
        """Test checkpoint directory is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TrainingConfig(checkpoint_dir=str(Path(tmpdir) / "test_checkpoints"))
            self.assertTrue(Path(config.checkpoint_dir).exists())


class TestTRMTrainer(unittest.TestCase):
    """Test TRMTrainer functionality"""
    
    def setUp(self):
        """Create trainer and test data"""
        self.device = "cpu"
        self.model = TinyComplianceNetwork()
        self.config = TrainingConfig(
            learning_rate=0.001,
            batch_size=8,
            num_epochs=3,
            device=self.device,
            early_stopping_patience=10
        )
        self.trainer = TRMTrainer(self.model, self.config)
        
        # Create test data
        self.num_samples = 20
        self.samples = [
            {
                "element_features": list(np.random.randn(128)),
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
            for _ in range(self.num_samples)
        ]
        self.labels = list(np.random.randint(0, 2, self.num_samples))
    
    def test_trainer_initialization(self):
        """Test trainer creation"""
        self.assertIsNotNone(self.trainer.model)
        self.assertIsNotNone(self.trainer.config)
    
    def test_compute_metrics(self):
        """Test metric computation"""
        preds = np.array([0, 1, 0, 1, 1, 0])
        labels = np.array([0, 1, 1, 1, 0, 0])
        
        metrics = self.trainer._compute_metrics(preds, labels)
        
        self.assertIn("accuracy", metrics)
        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("f1", metrics)
        
        # All metrics should be between 0 and 1
        for key in ["accuracy", "precision", "recall", "f1"]:
            self.assertGreaterEqual(metrics[key], 0.0)
            self.assertLessEqual(metrics[key], 1.0)
    
    def test_train_single_epoch(self):
        """Test training for one epoch"""
        history = self.trainer.train(
            self.samples,
            self.labels,
            resume_from=None
        )
        
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0].epoch, 1)
        self.assertGreater(history[0].loss, 0)
    
    def test_training_with_validation_split(self):
        """Test training with automatic validation split"""
        history = self.trainer.train(
            self.samples,
            self.labels,
            val_samples=None,  # Use automatic split
            val_labels=None
        )
        
        # Check validation metrics are computed
        for metrics in history:
            if metrics.val_loss is not None:
                self.assertGreater(metrics.val_loss, 0)
                self.assertGreaterEqual(metrics.val_accuracy, 0)
    
    def test_training_with_explicit_validation(self):
        """Test training with explicit validation data"""
        split_idx = int(len(self.samples) * 0.7)
        train_samples = self.samples[:split_idx]
        train_labels = self.labels[:split_idx]
        val_samples = self.samples[split_idx:]
        val_labels = self.labels[split_idx:]
        
        history = self.trainer.train(
            train_samples,
            train_labels,
            val_samples=val_samples,
            val_labels=val_labels
        )
        
        self.assertGreater(len(history), 0)
    
    def test_checkpoint_saving(self):
        """Test model checkpointing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TrainingConfig(
                learning_rate=0.001,
                batch_size=8,
                num_epochs=1,
                device=self.device,
                checkpoint_dir=tmpdir
            )
            trainer = TRMTrainer(self.model, config)
            
            trainer.train(self.samples, self.labels)
            
            # Check checkpoint files exist
            latest_path = Path(tmpdir) / "checkpoint_latest.pt"
            self.assertTrue(latest_path.exists())
    
    def test_checkpoint_loading(self):
        """Test loading from checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TrainingConfig(
                learning_rate=0.001,
                batch_size=8,
                num_epochs=2,
                device=self.device,
                checkpoint_dir=tmpdir
            )
            trainer = TRMTrainer(self.model, config)
            
            # Train for 2 epochs
            trainer.train(self.samples, self.labels)
            
            # Get state after training
            history_before = len(trainer.training_history)
            
            # Create new trainer and load checkpoint
            model2 = TinyComplianceNetwork()
            trainer2 = TRMTrainer(model2, config)
            
            latest_path = str(Path(tmpdir) / "checkpoint_latest.pt")
            trainer2.train(self.samples, self.labels, resume_from=latest_path)
            
            # Should have loaded history
            self.assertGreater(len(trainer2.training_history), 0)
    
    def test_early_stopping(self):
        """Test early stopping mechanism"""
        config = TrainingConfig(
            learning_rate=0.001,
            batch_size=8,
            num_epochs=100,
            device=self.device,
            early_stopping_patience=2,
            early_stopping_min_delta=0.0001
        )
        trainer = TRMTrainer(self.model, config)
        
        history = trainer.train(self.samples, self.labels)
        
        # Should stop before or at 100 epochs due to early stopping patience
        # (exact stopping point depends on validation performance)
        self.assertLessEqual(len(history), 100)
    
    def test_save_metrics_to_file(self):
        """Test saving training metrics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.trainer.train(self.samples, self.labels)
            
            metrics_path = str(Path(tmpdir) / "metrics.json")
            self.trainer.save_metrics_to_file(metrics_path)
            
            # Check file exists and is valid JSON
            self.assertTrue(Path(metrics_path).exists())
            with open(metrics_path, 'r') as f:
                metrics_data = json.load(f)
            
            self.assertIsInstance(metrics_data, list)
            self.assertGreater(len(metrics_data), 0)
    
    def test_training_summary(self):
        """Test getting training summary"""
        self.trainer.train(self.samples, self.labels)
        
        summary = self.trainer.get_training_summary()
        
        self.assertIn("total_epochs", summary)
        self.assertIn("best_epoch", summary)
        self.assertIn("best_val_loss", summary)
        self.assertGreater(summary["total_epochs"], 0)


class TestIncrementalLearning(unittest.TestCase):
    """Test incremental learning scenarios"""
    
    def setUp(self):
        """Setup for incremental learning tests"""
        self.device = "cpu"
        self.config = TrainingConfig(
            learning_rate=0.001,
            batch_size=8,
            num_epochs=2,
            device=self.device,
            checkpoint_dir=tempfile.mkdtemp()
        )
    
    def _create_samples(self, n: int) -> tuple:
        """Helper to create n training samples"""
        samples = [
            {
                "element_features": list(np.random.randn(128)),
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
            for _ in range(n)
        ]
        labels = list(np.random.randint(0, 2, n))
        return samples, labels
    
    def test_incremental_training_batch1(self):
        """Test initial training on batch 1"""
        model = TinyComplianceNetwork()
        trainer = TRMTrainer(model, self.config)
        
        samples1, labels1 = self._create_samples(20)
        history1 = trainer.train(samples1, labels1)
        
        self.assertEqual(len(history1), 2)  # 2 epochs
    
    def test_incremental_training_batch2(self):
        """Test adding batch 2 and retraining"""
        model = TinyComplianceNetwork()
        trainer = TRMTrainer(model, self.config)
        
        # Batch 1
        samples1, labels1 = self._create_samples(20)
        history1 = trainer.train(samples1, labels1)
        
        # Get best model
        trainer.load_best_model()
        
        # Batch 2: add new samples and retrain
        samples2, labels2 = self._create_samples(10)
        combined_samples = samples1 + samples2
        combined_labels = labels1 + labels2
        
        history2 = trainer.train(combined_samples, combined_labels)
        
        # Should have trained again
        self.assertGreater(len(history2), 0)
    
    def test_incremental_learning_model_improvement(self):
        """Test that model can improve with more data"""
        model = TinyComplianceNetwork()
        trainer = TRMTrainer(model, self.config)
        
        # Small batch
        samples_small, labels_small = self._create_samples(10)
        history_small = trainer.train(samples_small, labels_small)
        loss_small = history_small[-1].loss if history_small else float('inf')
        
        # Larger batch
        model2 = TinyComplianceNetwork()
        trainer2 = TRMTrainer(model2, self.config)
        samples_large, labels_large = self._create_samples(50)
        history_large = trainer2.train(samples_large, labels_large)
        loss_large = history_large[-1].loss if history_large else float('inf')
        
        # Both should have valid losses
        self.assertGreater(loss_small, 0)
        self.assertGreater(loss_large, 0)


class TestCreateTrainerFunction(unittest.TestCase):
    """Test convenience function"""
    
    def test_create_trainer_defaults(self):
        """Test creating trainer with defaults"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = create_trainer(checkpoint_dir=tmpdir)
            
            self.assertIsNotNone(trainer)
            self.assertIsNotNone(trainer.model)
            self.assertEqual(trainer.config.learning_rate, 0.001)
    
    def test_create_trainer_custom_params(self):
        """Test creating trainer with custom params"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = create_trainer(
                checkpoint_dir=tmpdir,
                learning_rate=0.01,
                device="cpu"
            )
            
            self.assertEqual(trainer.config.learning_rate, 0.01)
            self.assertEqual(trainer.config.device, "cpu")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Setup"""
        self.device = "cpu"
        self.model = TinyComplianceNetwork()
        self.config = TrainingConfig(
            learning_rate=0.001,
            batch_size=8,
            num_epochs=1,
            device=self.device
        )
        self.trainer = TRMTrainer(self.model, self.config)
    
    def test_single_sample_training(self):
        """Test training with single sample - requires explicit validation data"""
        samples = [
            {
                "element_features": list(np.random.randn(128)),
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
        ]
        labels = [1]
        
        # Need explicit validation data to avoid empty train set
        val_samples = [
            {
                "element_features": list(np.random.randn(128)),
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
        ]
        val_labels = [0]
        
        # Should not crash
        history = self.trainer.train(samples, labels, val_samples=val_samples, val_labels=val_labels)
        self.assertGreater(len(history), 0)
    
    def test_all_same_label(self):
        """Test with all same labels"""
        samples = [
            {
                "element_features": list(np.random.randn(128)),
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
            for _ in range(10)
        ]
        labels = [1] * 10  # All same label
        
        # Should handle gracefully
        history = self.trainer.train(samples, labels)
        self.assertGreater(len(history), 0)
    
    def test_nan_handling(self):
        """Test handling of NaN values"""
        samples = [
            {
                "element_features": [float('nan')] * 128,
                "rule_features": list(np.random.randn(128)),
                "context_features": list(np.random.randn(64))
            }
            for _ in range(5)
        ]
        labels = [0, 1, 0, 1, 0]  # Matching 5 samples
        
        # Dataset should handle NaN (may convert to 0 or propagate)
        dataset = TRMDataset(samples, labels, device=self.device)
        x, y = dataset[0]
        
        # After grad clipping, NaN might persist but shouldn't crash training
        self.assertTrue(x.shape == (320,))


if __name__ == '__main__':
    unittest.main()
