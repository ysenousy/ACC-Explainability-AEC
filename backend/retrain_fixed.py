#!/usr/bin/env python
"""
Clear old checkpoints and retrain with fixed feature extraction.
"""

import os
import shutil
import json
import sys

# Fix imports
sys.path.insert(0, '.')

def clear_checkpoints():
    """Clear old model checkpoints to force fresh training."""
    checkpoint_dir = "checkpoints/trm"
    if os.path.exists(checkpoint_dir):
        shutil.rmtree(checkpoint_dir)
        os.makedirs(checkpoint_dir)
        print(f"[OK] Cleared checkpoints directory: {checkpoint_dir}")

def verify_training_data():
    """Verify training data is valid."""
    training_file = "data/trm_incremental_data.json"
    
    if not os.path.exists(training_file):
        print(f"[ERROR] Training file not found: {training_file}")
        return False
    
    with open(training_file, 'r') as f:
        data = json.load(f)
    
    samples = data.get("samples", [])
    print(f"\n[INFO] Training data stats:")
    print(f"  - Total samples: {len(samples)}")
    
    if len(samples) == 0:
        print(f"[ERROR] No training samples found!")
        return False
    
    # Check feature dimensions
    first_sample = samples[0]
    element_features = first_sample.get("element_features", [])
    rule_features = first_sample.get("rule_features", [])
    context_features = first_sample.get("context_features", [])
    total_dim = len(element_features) + len(rule_features) + len(context_features)
    
    print(f"  - Element features dim: {len(element_features)}")
    print(f"  - Rule features dim: {len(rule_features)}")
    print(f"  - Context features dim: {len(context_features)}")
    print(f"  - Total feature dim: {total_dim}")
    
    # Check labels
    labels = [s.get("label", -1) for s in samples]
    unique_labels = set(labels)
    print(f"  - Unique labels: {sorted(unique_labels)}")
    print(f"  - PASS count: {labels.count(1)}")
    print(f"  - FAIL count: {labels.count(0)}")
    
    # Check feature variation
    if total_dim > 0:
        # Sample first element feature
        first_element_features = [s["element_features"][0] for s in samples if len(s.get("element_features", [])) > 0]
        unique_values = len(set(first_element_features))
        print(f"  - Element feature[0] unique values: {unique_values}/{len(first_element_features)}")
        if unique_values > 1:
            print(f"    [OK] Good variation detected!")
        else:
            print(f"    [WARN] Low variation in element features")
    
    return True

def start_training():
    """Start TRM model training."""
    print("\nStarting TRM model training...")
    print("=" * 60)
    
    try:
        from trm_trainer import TRMTrainer, TrainingConfig
        from reasoning_layer.tiny_recursive_reasoner import TinyComplianceNetwork
        import json
        
        # Load training data
        print("Loading training data...")
        with open("data/trm_incremental_data.json", "r") as f:
            data = json.load(f)
        
        samples = data.get("samples", [])
        
        # Prepare train/val splits
        train_samples = []
        train_labels = []
        val_samples = []
        val_labels = []
        
        # Split data (80/20)
        split_idx = int(len(samples) * 0.8)
        for i, sample in enumerate(samples):
            # Convert features back to tensors format
            sample_dict = {
                "element_features": sample.get("element_features", []),
                "rule_features": sample.get("rule_features", []),
                "context_features": sample.get("context_features", [])
            }
            label = sample.get("label", 0)
            
            if i < split_idx:
                train_samples.append(sample_dict)
                train_labels.append(label)
            else:
                val_samples.append(sample_dict)
                val_labels.append(label)
        
        print(f"  Train samples: {len(train_samples)}, Val samples: {len(val_samples)}")
        
        # Create model
        model = TinyComplianceNetwork(
            input_dim=320,
            hidden_dim_1=1024,
            hidden_dim_2=512,
            num_attention_heads=8,
            dropout_rate=0.2
        )
        
        # Create config
        config = TrainingConfig()
        config.batch_size = 16
        config.learning_rate = 0.001
        config.num_epochs = 50
        config.early_stopping_patience = 10
        config.validation_split = 0.2
        config.device = "cpu"
        
        # Create trainer
        trainer = TRMTrainer(model=model, config=config)
        
        # Train
        print("Training model...")
        history = trainer.train(
            train_samples=train_samples,
            train_labels=train_labels,
            val_samples=val_samples,
            val_labels=val_labels
        )
        
        # Print results
        print("\n" + "=" * 60)
        print("[OK] Training complete!")
        if history:
            print(f"  - Final loss: {history[-1].loss:.4f}")
            print(f"  - Final accuracy: {history[-1].accuracy:.4f}")
            print(f"  - Epochs completed: {len(history)}")
            # Show some sample predictions
            print(f"  - Val accuracy: {history[-1].val_accuracy:.4f}" if history[-1].val_accuracy else "")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("[RETRAIN] TRM Model Retraining (with Fixed Features)")
    print("=" * 60)
    
    # Step 1: Clear checkpoints
    clear_checkpoints()
    
    # Step 2: Verify training data
    if not verify_training_data():
        sys.exit(1)
    
    # Step 3: Train
    if not start_training():
        sys.exit(1)
    
    print("\n[OK] All steps completed successfully!")
