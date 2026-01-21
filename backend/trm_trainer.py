"""
Phase 3: Incremental TRM Training
Trains the Tiny Recursive Model on compliance data from Phase 1

Features:
    - PyTorch Dataset interface for Phase 1 data
    - Incremental learning (add samples, retrain)
    - SGD with momentum training
    - Early stopping on validation loss
    - Model checkpointing (best + latest)
    - Training metrics (loss, accuracy, F1)
    - Resume training from checkpoint

Classes:
    - TRMDataset: PyTorch Dataset for Phase 1 data
    - TRMTrainer: Training orchestrator with incremental support
    - TrainingConfig: Configuration dataclass
    - TrainingMetrics: Metrics tracking
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from reasoning_layer.tiny_recursive_reasoner import TinyComplianceNetwork, TRMResult
from backend.trm_data_extractor import IncrementalDatasetManager

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration"""
    learning_rate: float = 0.001
    momentum: float = 0.9
    weight_decay: float = 1e-5
    batch_size: int = 32
    num_epochs: int = 100
    validation_split: float = 0.2
    early_stopping_patience: int = 10
    early_stopping_min_delta: float = 0.001
    device: str = "cpu"
    checkpoint_dir: str = "checkpoints/trm"
    verbose: bool = True
    test_split: float = 0.1
    use_weighted_loss: bool = True
    min_samples_warning: int = 300
    
    def __post_init__(self):
        """Create checkpoint directory if it doesn't exist"""
        Path(self.checkpoint_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class TrainingMetrics:
    """Metrics for a single epoch"""
    epoch: int
    loss: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    val_loss: Optional[float] = None
    val_accuracy: Optional[float] = None
    val_f1: Optional[float] = None
    learning_rate: float = 0.001
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "epoch": self.epoch,
            "loss": round(self.loss, 4),
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "val_loss": round(self.val_loss, 4) if self.val_loss else None,
            "val_accuracy": round(self.val_accuracy, 4) if self.val_accuracy else None,
            "val_f1": round(self.val_f1, 4) if self.val_f1 else None,
            "learning_rate": round(self.learning_rate, 6)
        }


class TRMDataset(Dataset):
    """PyTorch Dataset for TRM training from Phase 1 data"""
    
    def __init__(self, 
                 samples: List[Dict[str, Any]],
                 labels: List[int],
                 device: str = "cpu"):
        """
        Initialize dataset
        
        Args:
            samples: List of 320-dim feature dicts (from Phase 1)
            labels: List of binary labels (0 or 1)
            device: Device to load tensors on
        """
        self.samples = samples
        self.labels = labels
        self.device = device
        
        assert len(samples) == len(labels), "Samples and labels must have same length"
        logger.info(f"Initialized TRMDataset with {len(samples)} samples")
    
    def __len__(self) -> int:
        """Get dataset size"""
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """Get single sample"""
        sample = self.samples[idx]
        label = self.labels[idx]
        
        # Extract feature values (concatenate element, rule, context features)
        features = []
        if "element_features" in sample:
            features.extend(sample["element_features"][:128])
        else:
            features.extend([0.0] * 128)
        
        if "rule_features" in sample:
            features.extend(sample["rule_features"][:128])
        else:
            features.extend([0.0] * 128)
        
        if "context_features" in sample:
            features.extend(sample["context_features"][:64])
        else:
            features.extend([0.0] * 64)
        
        # Ensure exactly 320 features
        features = features[:320]
        features.extend([0.0] * (320 - len(features)))
        
        x = torch.tensor(features, dtype=torch.float32, device=self.device)
        y = torch.tensor(label, dtype=torch.long, device=self.device)
        
        return x, y


class TRMTrainer:
    """Trainer for Tiny Recursive Model with incremental learning support"""
    
    def __init__(self,
                 model: TinyComplianceNetwork,
                 config: TrainingConfig = None):
        """
        Initialize trainer
        
        Args:
            model: TinyComplianceNetwork instance
            config: TrainingConfig object
        """
        self.model = model
        self.config = config or TrainingConfig()
        self.device = torch.device(self.config.device)
        self.model.to(self.device)
        
        self.optimizer = None
        self.scheduler = None
        self.loss_fn = nn.CrossEntropyLoss()
        self.class_weights = None
        
        self.training_history: List[TrainingMetrics] = []
        self.best_val_loss = float('inf')
        self.epochs_without_improvement = 0
        self.training_duration_seconds = 0.0
        
        # Track best metrics for performance summary
        self.best_train_accuracy = 0.0
        self.best_precision = 0.0
        self.best_recall = 0.0
        self.best_val_accuracy = 0.0
        self.train_fail_count = 0
        self.train_pass_count = 0
        
        logger.info(f"Initialized TRMTrainer on device: {self.device}")
    
    def _setup_optimizer(self):
        """Initialize optimizer and scheduler"""
        self.optimizer = optim.SGD(
            self.model.parameters(),
            lr=self.config.learning_rate,
            momentum=self.config.momentum,
            weight_decay=self.config.weight_decay
        )
        
        # Learning rate scheduler: reduce on plateau
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )
    
    def _compute_class_weights(self, labels: List[int]):
        """Compute class weights for imbalanced data"""
        if not self.config.use_weighted_loss:
            return None
        
        unique, counts = np.unique(labels, return_counts=True)
        total = len(labels)
        weights = {}
        for cls, count in zip(unique, counts):
            weight = total / (len(unique) * count)
            weights[cls] = weight
        
        class_weights = torch.zeros(2)
        for cls in [0, 1]:
            class_weights[cls] = weights.get(cls, 1.0)
        
        logger.info(f"Class weights: {class_weights.tolist()}")
        return class_weights.to(self.device)
    
    def _train_epoch(self, train_loader: DataLoader) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Train for one epoch
        
        Returns:
            (loss, predictions, labels)
        """
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_labels = []
        
        for batch_idx, (x, y) in enumerate(train_loader):
            x, y = x.to(self.device), y.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            logits, _ = self.model(x)
            
            # Use weighted loss for class imbalance
            if self.class_weights is not None:
                weighted_loss_fn = nn.CrossEntropyLoss(weight=self.class_weights)
                loss = weighted_loss_fn(logits, y)
            else:
                loss = self.loss_fn(logits, y)
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            # Track metrics
            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().detach().numpy())
            all_labels.extend(y.cpu().detach().numpy())
            
            if (batch_idx + 1) % max(1, len(train_loader) // 3) == 0 and self.config.verbose:
                logger.info(f"  Batch {batch_idx+1}/{len(train_loader)}, Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / len(train_loader)
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        
        return avg_loss, all_preds, all_labels
    
    def _validate_epoch(self, val_loader: DataLoader) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Validate for one epoch
        
        Returns:
            (loss, predictions, labels)
        """
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(self.device), y.to(self.device)
                
                logits, _ = self.model(x)
                loss = self.loss_fn(logits, y)
                
                total_loss += loss.item()
                preds = torch.argmax(logits, dim=1)
                all_preds.extend(preds.cpu().detach().numpy())
                all_labels.extend(y.cpu().detach().numpy())
        
        avg_loss = total_loss / len(val_loader)
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        
        return avg_loss, all_preds, all_labels
    
    def _compute_metrics(self, preds: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """Compute classification metrics"""
        metrics = {}
        
        # Handle edge cases
        if len(np.unique(labels)) < 2:
            # If only one class in batch, set metrics to 0 or 1
            metrics['accuracy'] = float(np.mean(preds == labels))
            metrics['precision'] = 0.0
            metrics['recall'] = 0.0
            metrics['f1'] = 0.0
        else:
            metrics['accuracy'] = float(accuracy_score(labels, preds))
            metrics['precision'] = float(precision_score(labels, preds, zero_division=0))
            metrics['recall'] = float(recall_score(labels, preds, zero_division=0))
            metrics['f1'] = float(f1_score(labels, preds, zero_division=0))
        
        return metrics
    
    def _save_checkpoint(self, 
                        epoch: int, 
                        metrics: TrainingMetrics, 
                        is_best: bool = False):
        """Save model checkpoint"""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'metrics': asdict(metrics),
            'training_history': [asdict(m) for m in self.training_history],
            'timestamp': datetime.now().isoformat()
        }
        
        # Save latest checkpoint
        latest_path = checkpoint_dir / "checkpoint_latest.pt"
        torch.save(checkpoint, latest_path)
        
        # Save best checkpoint if applicable
        if is_best:
            best_path = checkpoint_dir / "checkpoint_best.pt"
            torch.save(checkpoint, best_path)
            logger.info(f"Saved best checkpoint at epoch {epoch}")
    
    def _load_checkpoint(self, checkpoint_path: str) -> int:
        """
        Load model from checkpoint
        
        Returns:
            Starting epoch
        """
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.training_history = [
            TrainingMetrics(**m) for m in checkpoint.get('training_history', [])
        ]
        
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
        return checkpoint.get('epoch', 0)
    
    def train(self,
              train_samples: List[Dict[str, Any]],
              train_labels: List[int],
              val_samples: Optional[List[Dict[str, Any]]] = None,
              val_labels: Optional[List[int]] = None,
              resume_from: Optional[str] = None) -> List[TrainingMetrics]:
        """
        Train model on provided data
        
        Args:
            train_samples: Training feature dicts
            train_labels: Training labels
            val_samples: Validation feature dicts (if None, will be sampled from train)
            val_labels: Validation labels
            resume_from: Path to checkpoint to resume from
        
        Returns:
            List of TrainingMetrics for each epoch
        """
        if self.optimizer is None:
            self._setup_optimizer()
        
        # Check dataset size and class balance
        total_samples = len(train_samples)
        if val_samples:
            total_samples += len(val_samples)
        
        if total_samples < self.config.min_samples_warning:
            logger.warning(
                f"⚠️  WARNING: Only {total_samples} samples (recommended minimum: {self.config.min_samples_warning}). "
                f"Model will likely overfit. Add more IFC files and run compliance checks."
            )
        
        # Check class balance
        label_counts = np.bincount(np.array(train_labels))
        if len(label_counts) == 1:
            logger.error(
                f"❌ CRITICAL: All {len(train_labels)} samples are class {np.argmax(label_counts)}! "
                f"Model will achieve 100% by predicting this class. Need BOTH pass and fail cases."
            )
        else:
            logger.info(f"✅ Class distribution: {label_counts[0]} fails, {label_counts[1]} passes")
        
        # Store class counts for metrics
        self.train_fail_count = int(label_counts[0]) if len(label_counts) > 0 else 0
        self.train_pass_count = int(label_counts[1]) if len(label_counts) > 1 else 0
        
        # Compute class weights for imbalanced data
        self.class_weights = self._compute_class_weights(train_labels)
        
        # If validation data not provided, use validation_split
        if val_samples is None:
            split_idx = int(len(train_samples) * (1 - self.config.validation_split))
            val_samples = train_samples[split_idx:]
            val_labels = train_labels[split_idx:]
            train_samples = train_samples[:split_idx]
            train_labels = train_labels[:split_idx]
        
        # Create datasets and loaders
        train_dataset = TRMDataset(train_samples, train_labels, device=self.device)
        val_dataset = TRMDataset(val_samples, val_labels, device=self.device)
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=0
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=0
        )
        
        start_epoch = 0
        if resume_from:
            start_epoch = self._load_checkpoint(resume_from)
        
        logger.info(f"Training for {self.config.num_epochs} epochs (resume from epoch {start_epoch})")
        logger.info(f"Train size: {len(train_dataset)}, Val size: {len(val_dataset)}")
        
        # Record training start time
        training_start_time = time.time()
        
        # Training loop
        for epoch in range(start_epoch, self.config.num_epochs):
            logger.info(f"\nEpoch {epoch+1}/{self.config.num_epochs}")
            
            # Train
            train_loss, train_preds, train_labels_np = self._train_epoch(train_loader)
            train_metrics = self._compute_metrics(train_preds, train_labels_np)
            
            # Validate
            val_loss, val_preds, val_labels_np = self._validate_epoch(val_loader)
            val_metrics = self._compute_metrics(val_preds, val_labels_np)
            
            # DEBUG: Check predictions distribution
            unique_train_preds, train_pred_counts = np.unique(train_preds, return_counts=True)
            unique_val_preds, val_pred_counts = np.unique(val_preds, return_counts=True)
            logger.debug(f"Train predictions distribution: {dict(zip(unique_train_preds, train_pred_counts))}")
            logger.debug(f"Val predictions distribution: {dict(zip(unique_val_preds, val_pred_counts))}")
            
            # Track best metrics
            if train_metrics['accuracy'] > self.best_train_accuracy:
                self.best_train_accuracy = train_metrics['accuracy']
            
            if val_metrics['accuracy'] > self.best_val_accuracy:
                self.best_val_accuracy = val_metrics['accuracy']
                self.best_precision = val_metrics['precision']
                self.best_recall = val_metrics['recall']
            
            # Create metrics object
            metrics = TrainingMetrics(
                epoch=epoch + 1,
                loss=train_loss,
                accuracy=train_metrics['accuracy'],
                precision=train_metrics['precision'],
                recall=train_metrics['recall'],
                f1=train_metrics['f1'],
                val_loss=val_loss,
                val_accuracy=val_metrics['accuracy'],
                val_f1=val_metrics['f1'],
                learning_rate=self.optimizer.param_groups[0]['lr']
            )
            
            self.training_history.append(metrics)
            
            # Logging
            if self.config.verbose:
                logger.info(
                    f"Train Loss: {train_loss:.4f}, Acc: {train_metrics['accuracy']:.4f}, "
                    f"Precision: {train_metrics['precision']:.4f}, Recall: {train_metrics['recall']:.4f}, "
                    f"F1: {train_metrics['f1']:.4f} | "
                    f"Val Loss: {val_loss:.4f}, Acc: {val_metrics['accuracy']:.4f}, "
                    f"F1: {val_metrics['f1']:.4f}"
                )
            else:
                logger.info(
                    f"Train Loss: {train_loss:.4f}, Acc: {train_metrics['accuracy']:.4f}, "
                    f"F1: {train_metrics['f1']:.4f} | "
                    f"Val Loss: {val_loss:.4f}, Acc: {val_metrics['accuracy']:.4f}, "
                    f"F1: {val_metrics['f1']:.4f}"
                )
            
            # Learning rate scheduling
            self.scheduler.step(val_loss)
            
            # Early stopping logic
            is_best = val_loss < (self.best_val_loss - self.config.early_stopping_min_delta)
            if is_best:
                self.best_val_loss = val_loss
                self.epochs_without_improvement = 0
            else:
                self.epochs_without_improvement += 1
            
            # Save checkpoints
            self._save_checkpoint(epoch + 1, metrics, is_best=is_best)
            
            # Early stopping
            if self.epochs_without_improvement >= self.config.early_stopping_patience:
                logger.info(
                    f"Early stopping triggered after {epoch + 1} epochs "
                    f"({self.epochs_without_improvement} epochs without improvement)"
                )
                break
        
        # Record training end time
        training_end_time = time.time()
        self.training_duration_seconds = training_end_time - training_start_time
        
        logger.info(f"Training completed. Best val loss: {self.best_val_loss:.4f}")
        logger.info(f"Total training time: {self.training_duration_seconds:.2f} seconds ({self.training_duration_seconds/60:.2f} minutes)")
        return self.training_history
    
    def save_metrics_to_file(self, filepath: str):
        """Save training history to JSON file"""
        metrics_list = [asdict(m) for m in self.training_history]
        with open(filepath, 'w') as f:
            json.dump(metrics_list, f, indent=2)
        logger.info(f"Saved training metrics to {filepath}")
    
    def load_best_model(self):
        """Load best model from checkpoint"""
        best_path = Path(self.config.checkpoint_dir) / "checkpoint_best.pt"
        if best_path.exists():
            self._load_checkpoint(str(best_path))
            logger.info("Loaded best model from checkpoint")
        else:
            logger.warning("No best checkpoint found")
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Get summary of training with performance metrics"""
        if not self.training_history:
            return {"error": "No training history"}
        
        best_epoch = min(
            self.training_history,
            key=lambda m: m.val_loss if m.val_loss else float('inf')
        )
        
        # Calculate overfitting indicator
        overfitting_indicator = round(self.best_train_accuracy - self.best_val_accuracy, 4)
        
        # Calculate class balance ratio
        if self.train_fail_count > 0:
            balance_ratio = round(self.train_pass_count / self.train_fail_count, 2)
        else:
            balance_ratio = 0
        
        # Early stopping info
        early_stopping_triggered = self.epochs_without_improvement > 0
        
        return {
            # Basic training info
            "total_epochs": len(self.training_history),
            "best_epoch": best_epoch.epoch,
            
            # Loss metrics
            "best_val_loss": round(best_epoch.val_loss, 4) if best_epoch.val_loss else None,
            "final_train_loss": round(self.training_history[-1].loss, 4),
            "final_val_loss": round(self.training_history[-1].val_loss, 4) if self.training_history[-1].val_loss else None,
            
            # Accuracy metrics (5 essential metrics)
            "best_train_accuracy": round(self.best_train_accuracy, 4),  # Essential metric #4
            "best_val_accuracy": round(self.best_val_accuracy, 4),
            "overfitting_indicator": overfitting_indicator,  # Essential metric #1
            
            # Precision & Recall (Essential metric #3)
            "best_precision": round(self.best_precision, 4),
            "best_recall": round(self.best_recall, 4),
            "best_val_f1": round(best_epoch.val_f1, 4) if best_epoch.val_f1 else None,
            
            # Class distribution (Essential metric #2)
            "train_fail_count": self.train_fail_count,
            "train_pass_count": self.train_pass_count,
            "balance_ratio": balance_ratio,
            
            # Early stopping info (Essential metric #5)
            "early_stopping_triggered": early_stopping_triggered,
            "epochs_without_improvement": self.epochs_without_improvement,
            
            # Training duration
            "training_duration_seconds": round(self.training_duration_seconds, 2),
            "training_duration_minutes": round(self.training_duration_seconds / 60, 2),
            
            "timestamp": datetime.now().isoformat()
        }


def create_trainer(
    checkpoint_dir: str = "checkpoints/trm",
    learning_rate: float = 0.001,
    device: str = "cpu"
) -> TRMTrainer:
    """
    Convenience function to create trainer with model
    
    Args:
        checkpoint_dir: Directory for saving checkpoints
        learning_rate: Learning rate for optimizer
        device: Device to use (cpu or cuda)
    
    Returns:
        TRMTrainer instance with initialized model
    """
    model = TinyComplianceNetwork()
    config = TrainingConfig(
        learning_rate=learning_rate,
        checkpoint_dir=checkpoint_dir,
        device=device
    )
    return TRMTrainer(model, config)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create trainer
    trainer = create_trainer(device="cpu")
    
    # Example: Create dummy training data
    num_samples = 100
    train_samples = [
        {
            "element_features": list(np.random.randn(128)),
            "rule_features": list(np.random.randn(128)),
            "context_features": list(np.random.randn(64))
        }
        for _ in range(num_samples)
    ]
    train_labels = list(np.random.randint(0, 2, num_samples))
    
    # Train
    history = trainer.train(train_samples, train_labels, resume_from=None)
    
    # Print summary
    print("\n" + "="*50)
    print("Training Summary")
    print("="*50)
    summary = trainer.get_training_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
