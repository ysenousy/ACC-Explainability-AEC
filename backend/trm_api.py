"""
Phase 4: TRM Backend API Endpoints
Integrates Phase 1 (data extraction), Phase 2 (model inference), and Phase 3 (training)
into REST API endpoints for the compliance reasoning system.

Endpoints:
    POST /api/trm/add-sample - Add a single training sample
    POST /api/trm/analyze - Run inference on a single sample
    POST /api/trm/batch-analyze - Run inference on multiple samples
    POST /api/trm/train - Train model on accumulated samples
    GET  /api/trm/models - Get model information
    POST /api/trm/models/reset - Reset model to initial state
    GET  /api/trm/dataset/stats - Get dataset statistics
"""

from flask import Flask, request, jsonify, Blueprint
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
import torch

from backend.trm_data_extractor import ComplianceResultToTRMSample, IncrementalDatasetManager
from backend.trm_trainer import TRMTrainer, TrainingConfig, create_trainer
from reasoning_layer.tiny_recursive_reasoner import TinyComplianceNetwork, TRMResult

logger = logging.getLogger(__name__)

# Create Blueprint for TRM endpoints
trm_bp = Blueprint('trm', __name__, url_prefix='/api/trm')

# Global variable to hold version manager (set by register function)
_version_manager = None

# Global state for TRM system
class TRMSystem:
    """Singleton to manage TRM model and training state"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TRMSystem, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize TRM system"""
        self.model = TinyComplianceNetwork()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()
        
        self.trainer = None
        self.data_extractor = ComplianceResultToTRMSample()
        self.dataset_manager = IncrementalDatasetManager()
        
        self.dataset_path = Path("data/trm_incremental_data.json")
        self.model_checkpoint_dir = Path("checkpoints/trm")
        
        logger.info(f"TRM System initialized on device: {self.device}")
    
    def reset_model(self):
        """Reset model to initial state"""
        self.model = TinyComplianceNetwork()
        self.model.to(self.device)
        self.model.eval()
        self.trainer = None
        logger.info("Model reset to initial state")


# Initialize TRM system
trm_system = TRMSystem()


# ===== Helper Functions =====

def _extract_features_from_result(compliance_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract and convert compliance result to TRM sample
    
    Args:
        compliance_result: Compliance check result
    
    Returns:
        TRM sample dict or None if extraction fails
    """
    try:
        sample = trm_system.data_extractor.convert(compliance_result)
        return sample
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        return None


def _prepare_inference_input(sample: Dict[str, Any]) -> Optional[torch.Tensor]:
    """
    Prepare sample for inference
    
    Args:
        sample: TRM sample dict
    
    Returns:
        Torch tensor or None if preparation fails
    """
    try:
        # Extract feature vector (should be 320-dim)
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
        
        # Ensure 320 features
        features = features[:320]
        features.extend([0.0] * (320 - len(features)))
        
        x = torch.tensor(features, dtype=torch.float32, device=trm_system.device)
        return x
    
    except Exception as e:
        logger.error(f"Input preparation failed: {e}")
        return None


# ===== API Endpoints =====

@trm_bp.route('/add-sample', methods=['POST'])
def add_training_sample():
    """
    Add a single training sample to the dataset
    
    Request body:
    {
        "compliance_result": {compliance check result},
        "ifc_file": "filename.ifc" (optional, for tracking)
    }
    
    Response:
    {
        "success": bool,
        "sample_added": bool,
        "metadata": {dataset statistics}
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        compliance_result = data.get("compliance_result")
        ifc_file = data.get("ifc_file", "unknown.ifc")
        
        # Validate inputs
        if compliance_result is None:
            return jsonify({"error": "compliance_result required"}), 400
        
        # Extract features
        sample = _extract_features_from_result(compliance_result)
        if sample is None:
            return jsonify({"error": "Feature extraction failed"}), 400
        
        # Determine label from compliance result (PASS=1, FAIL=0)
        # Check for multiple possible formats
        compliance_status = compliance_result.get("compliance_result", {})
        
        # Try different field names
        if isinstance(compliance_status, dict):
            # Check for "passed" boolean field
            if "passed" in compliance_status:
                label = 1 if compliance_status.get("passed", False) else 0
            # Check for "result" string field
            elif "result" in compliance_status:
                label = 1 if compliance_status.get("result", "FAIL").upper() == "PASS" else 0
            else:
                # Default to FAIL if no clear status
                label = 0
        else:
            # Fallback to top-level "result" field
            label = 1 if compliance_result.get("result", "FAIL").upper() == "PASS" else 0
        
        # Add label to sample
        sample["label"] = label
        
        # Ensure dataset directory exists
        dataset_file = Path(trm_system.dataset_path)
        dataset_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing dataset to check for duplicates
        existing_samples = []
        existing_guids = set()
        if dataset_file.exists():
            try:
                with open(dataset_file, 'r') as f:
                    existing_data = json.load(f)
                    existing_samples = existing_data.get("samples", [])
                    # Build set of existing element GUIDs for fast lookup
                    existing_guids = {s.get("element_guid", "") for s in existing_samples}
            except Exception as e:
                logger.warning(f"Could not load existing dataset: {e}")
        
        # Check if this element already exists in the dataset
        element_guid = sample.get("element_guid", "")
        if element_guid and element_guid in existing_guids:
            logger.info(f"Sample for element {element_guid} already exists, skipping duplicate")
            return jsonify({
                "success": True,
                "sample_added": False,
                "reason": "Duplicate - element already in dataset",
                "metadata": {
                    "total_samples": len(existing_samples),
                    "duplicates_skipped": 1
                }
            }), 200
        
        # Add to dataset
        result = trm_system.dataset_manager.add_sample(
            file_path=str(trm_system.dataset_path),
            sample=sample,
            ifc_file=ifc_file
        )
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Error adding sample: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/analyze', methods=['POST'])
def analyze_single():
    """
    Run inference on a single compliance sample
    
    Request body:
    {
        "compliance_result": {compliance check result}
    }
    
    Response:
    {
        "prediction": 0 or 1,
        "confidence": float,
        "reasoning_trace": [list of explanations],
        "total_steps": int,
        "converged": bool,
        "error": optional error message
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        compliance_result = data.get("compliance_result")
        
        if compliance_result is None:
            return jsonify({"error": "compliance_result required"}), 400
        
        # Extract features
        sample = _extract_features_from_result(compliance_result)
        if sample is None:
            return jsonify({"error": "Feature extraction failed"}), 400
        
        # Prepare input
        x = _prepare_inference_input(sample)
        if x is None:
            return jsonify({"error": "Input preparation failed"}), 400
        
        # Run inference using the model directly
        with torch.no_grad():
            # Use TinyRecursiveReasoner with proper initialization
            from reasoning_layer.tiny_recursive_reasoner import TinyRecursiveReasoner
            
            # Create reasoner with same architecture as trm_system.model
            reasoner = TinyRecursiveReasoner(
                input_dim=320,
                hidden_dim_1=1024,
                hidden_dim_2=512,
                num_attention_heads=8,
                device=trm_system.device
            )
            
            # Copy weights from trm_system.model if it exists
            if hasattr(trm_system.model, 'state_dict'):
                reasoner.network.load_state_dict(trm_system.model.state_dict())
            
            result = reasoner.infer(x)
        
        # Return result
        return jsonify(result.to_dict()), 200
    
    except Exception as e:
        logger.error(f"Error analyzing sample: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/batch-analyze', methods=['POST'])
def analyze_batch():
    """
    Run inference on multiple compliance samples
    
    Request body:
    {
        "samples": [list of compliance results]
    }
    
    Response:
    {
        "results": [list of predictions],
        "count": int,
        "summary": {
            "avg_confidence": float,
            "pass_count": int,
            "fail_count": int
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        samples = data.get("samples", [])
        
        if not samples:
            return jsonify({"error": "samples array required"}), 400
        
        if not isinstance(samples, list):
            return jsonify({"error": "samples must be a list"}), 400
        
        # Process each sample
        results = []
        confidences = []
        pass_count = 0
        fail_count = 0
        
        from reasoning_layer.tiny_recursive_reasoner import TinyRecursiveReasoner
        
        reasoner = TinyRecursiveReasoner(
            input_dim=320,
            hidden_dim_1=1024,
            hidden_dim_2=512,
            num_attention_heads=8,
            device=trm_system.device
        )
        
        # Copy weights from trm_system.model
        if hasattr(trm_system.model, 'state_dict'):
            reasoner.network.load_state_dict(trm_system.model.state_dict())
        
        with torch.no_grad():
            for sample_data in samples:
                # Extract features
                sample = _extract_features_from_result(sample_data)
                if sample is None:
                    results.append({"error": "Feature extraction failed"})
                    continue
                
                # Prepare input
                x = _prepare_inference_input(sample)
                if x is None:
                    results.append({"error": "Input preparation failed"})
                    continue
                
                # Run inference
                result = reasoner.infer(x)
                results.append(result.to_dict())
                
                confidences.append(result.confidence)
                if result.prediction == 1:
                    pass_count += 1
                else:
                    fail_count += 1
        
        # Compute summary
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return jsonify({
            "results": results,
            "count": len(results),
            "summary": {
                "avg_confidence": round(avg_confidence, 4),
                "pass_count": pass_count,
                "fail_count": fail_count
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error batch analyzing: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/train', methods=['POST'])
def train_model():
    """
    Train model on accumulated dataset samples
    
    Request body:
    {
        "epochs": int (optional, default 100),
        "learning_rate": float (optional, default 0.001),
        "batch_size": int (optional, default 32),
        "resume": bool (optional, default false)
    }
    
    Response:
    {
        "success": bool,
        "epochs_trained": int,
        "best_loss": float,
        "metrics": {summary metrics}
    }
    """
    try:
        data = request.get_json() or {}
        
        # Get training parameters
        num_epochs = data.get("epochs", 100)
        learning_rate = data.get("learning_rate", 0.001)
        batch_size = data.get("batch_size", 32)
        resume = data.get("resume", False)
        
        # Validate parameters
        if num_epochs < 1 or num_epochs > 1000:
            return jsonify({"error": "epochs must be between 1 and 1000"}), 400
        
        if learning_rate <= 0 or learning_rate > 1.0:
            return jsonify({"error": "learning_rate must be between 0 and 1"}), 400
        
        if batch_size < 1 or batch_size > 1024:
            return jsonify({"error": "batch_size must be between 1 and 1024"}), 400
        
        # Load raw dataset
        try:
            from pathlib import Path
            import json
            dataset_file = Path(str(trm_system.dataset_path))
            if not dataset_file.exists():
                return jsonify({"error": "No training data available"}), 400
            
            with open(dataset_file, 'r') as f:
                data = json.load(f)
            
            samples = data.get("samples", [])
            if len(samples) == 0:
                return jsonify({"error": "No training data available"}), 400
            
            # Calculate 80/10/10 split
            total = len(samples)
            train_count = int(total * 0.8)
            val_count = int(total * 0.1)
            
            train_samples = samples[:train_count]
            val_samples = samples[train_count:train_count + val_count]
            test_samples = samples[train_count + val_count:]
            
            # Extract labels (1 for PASS, 0 for FAIL)
            train_labels = [s.get("label", 0) for s in train_samples]
            val_labels = [s.get("label", 0) for s in val_samples]
            
            if len(train_samples) == 0:
                return jsonify({"error": "No training samples available"}), 400
            
        except Exception as e:
            logger.error(f"Error loading dataset: {str(e)}")
            return jsonify({"error": f"Failed to load dataset: {str(e)}"}), 400
        
        # Create trainer
        config = TrainingConfig(
            learning_rate=learning_rate,
            batch_size=batch_size,
            num_epochs=num_epochs,
            device=trm_system.device,
            checkpoint_dir=str(trm_system.model_checkpoint_dir),
            verbose=False
        )
        
        trm_system.trainer = TRMTrainer(trm_system.model, config)
        
        # Resume from checkpoint if requested
        resume_from = None
        if resume:
            best_checkpoint = Path(trm_system.model_checkpoint_dir) / "checkpoint_best.pt"
            if best_checkpoint.exists():
                resume_from = str(best_checkpoint)
        
        # Train
        history = trm_system.trainer.train(
            train_samples,
            train_labels,
            val_samples=val_samples if len(val_samples) > 0 else None,
            val_labels=val_labels if len(val_labels) > 0 else None,
            resume_from=resume_from
        )
        
        # Get summary
        summary = trm_system.trainer.get_training_summary()
        
        # Register version in ModelVersionManager if available
        version_id = None
        logger.info(f"DEBUG: _version_manager is {_version_manager}")
        if _version_manager:
            try:
                best_checkpoint = Path(trm_system.model_checkpoint_dir) / "checkpoint_best.pt"
                logger.info(f"DEBUG: Registering version with checkpoint: {best_checkpoint}")
                
                # Get dataset stats
                with open(Path(str(trm_system.dataset_path)), 'r') as f:
                    dataset_info = json.load(f)
                
                dataset_stats = {
                    "total_samples": len(dataset_info.get("samples", [])),
                    "train_samples": len(train_samples),
                    "val_samples": len(val_samples) if val_samples else 0,
                    "test_samples": len(test_samples) if test_samples else 0
                }
                
                version_id = _version_manager.register_version(
                    checkpoint_path=str(best_checkpoint),
                    training_config={
                        "epochs": num_epochs,
                        "learning_rate": learning_rate,
                        "batch_size": batch_size,
                        "resume": resume
                    },
                    performance_metrics={
                        "best_val_loss": summary.get("best_val_loss", 0.0),
                        "best_val_accuracy": summary.get("best_val_accuracy", 0.0)
                    },
                    dataset_stats=dataset_stats,
                    training_duration=0.0,  # We don't track this yet
                    description=f"Training with {len(train_samples)} samples, {num_epochs} epochs"
                )
                logger.info(f"✅ Registered new model version: {version_id}")
            except Exception as e:
                logger.error(f"❌ Failed to register version: {str(e)}", exc_info=True)
        else:
            logger.error("❌ _version_manager is None - version will NOT be registered")
        
        return jsonify({
            "success": True,
            "epochs_trained": len(history),
            "best_loss": summary.get("best_val_loss", 0.0),
            "metrics": summary,
            "version_id": version_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/models', methods=['GET'])
def get_model_info():
    """
    Get information about current model
    
    Response:
    {
        "model_type": "TinyComplianceNetwork",
        "parameters": int,
        "device": str,
        "trained": bool,
        "checkpoint_dir": str
    }
    """
    try:
        param_count = trm_system.model.get_parameter_count()
        
        best_checkpoint = Path(trm_system.model_checkpoint_dir) / "checkpoint_best.pt"
        is_trained = best_checkpoint.exists()
        
        return jsonify({
            "model_type": "TinyComplianceNetwork",
            "parameters": param_count,
            "device": trm_system.device,
            "trained": is_trained,
            "checkpoint_dir": str(trm_system.model_checkpoint_dir)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/models/reset', methods=['POST'])
def reset_model():
    """
    Reset model to initial untrained state
    
    Response:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        trm_system.reset_model()
        return jsonify({
            "success": True,
            "message": "Model reset to initial state"
        }), 200
    
    except Exception as e:
        logger.error(f"Error resetting model: {e}")
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/models/load-best', methods=['POST'])
def load_best_model():
    """
    Load best trained model from checkpoint
    
    Response:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        if trm_system.trainer is not None:
            trm_system.trainer.load_best_model()
            return jsonify({
                "success": True,
                "message": "Best model loaded from checkpoint"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No trained model available"
            }), 400
    
    except Exception as e:
        logger.error(f"Error loading best model: {e}")
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/dataset/stats', methods=['GET'])
def get_dataset_stats():
    """
    Get dataset statistics
    
    Response:
    {
        "total_samples": int,
        "train_samples": int,
        "val_samples": int,
        "test_samples": int,
        "pass_count": int,
        "fail_count": int,
        "files_processed": [list of IFC files]
    }
    """
    try:
        dataset_path = str(trm_system.dataset_path)
        
        # Try to load statistics
        try:
            stats = trm_system.dataset_manager.get_statistics(dataset_path)
            # stats is a dict with total_samples, train_samples, etc.
            return jsonify(stats or {
                "total_samples": 0,
                "train_samples": 0,
                "val_samples": 0,
                "test_samples": 0,
                "pass_count": 0,
                "fail_count": 0,
                "files_processed": []
            }), 200
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return jsonify({
                "total_samples": 0,
                "train_samples": 0,
                "val_samples": 0,
                "test_samples": 0,
                "pass_count": 0,
                "fail_count": 0,
                "files_processed": []
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting dataset stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/dataset/clear', methods=['POST'])
def clear_dataset():
    """
    Clear all training data
    
    Response:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        dataset_path = Path(trm_system.dataset_path)
        if dataset_path.exists():
            dataset_path.unlink()
        
        return jsonify({
            "success": True,
            "message": "Dataset cleared"
        }), 200
    
    except Exception as e:
        logger.error(f"Error clearing dataset: {e}")
        return jsonify({"error": str(e)}), 500


def register_trm_endpoints(app: Flask, version_manager=None):
    """
    Register TRM API endpoints to Flask app
    
    Args:
        app: Flask application instance
        version_manager: ModelVersionManager instance (optional)
    """
    global _version_manager
    _version_manager = version_manager
    
    app.register_blueprint(trm_bp)
    logger.info("TRM API endpoints registered")
