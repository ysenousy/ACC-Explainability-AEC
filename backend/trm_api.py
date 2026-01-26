"""
Phase 4: TRM Backend API Endpoints
Integrates Phase 1 (data extraction), Phase 2 (model inference), and Phase 3 (training)
into REST API endpoints for the compliance reasoning system.

Endpoints:
    POST /api/trm/add-sample - Add a single training sample
    POST /api/trm/add-samples-from-compliance - Bulk add samples from compliance check results
    POST /api/trm/analyze - Run inference on a single sample
    POST /api/trm/batch-analyze - Run inference on multiple samples
    POST /api/trm/train - Train model on accumulated samples
    GET  /api/trm/models - Get model information
    POST /api/trm/models/reset - Reset model to initial state
    GET  /api/trm/dataset/stats - Get dataset statistics
    GET  /api/trm/versions - Get all model versions
    GET  /api/trm/versions/<version_id> - Get details for a specific version
    POST /api/trm/versions/<version_id>/activate - Activate a version for inference
"""

from flask import Flask, request, jsonify, Blueprint
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
import torch

from backend.trm_data_extractor import ComplianceResultToTRMSample, IncrementalDatasetManager
from backend.trm_trainer import TRMTrainer, TrainingConfig, create_trainer
from backend.guid_fragility_fix import TrainingDataQualityError
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
        
        # Load trained checkpoint if it exists
        best_checkpoint = self.model_checkpoint_dir / "checkpoint_best.pt"
        if best_checkpoint.exists():
            try:
                checkpoint = torch.load(best_checkpoint, map_location=self.device)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                logger.info(f"Loaded trained model from {best_checkpoint}")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}. Using fresh model.")
        else:
            logger.info("No trained checkpoint found. Using fresh model.")
        
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

def _get_element_data_from_graph(graph: Dict[str, Any], element_guid: str) -> Optional[Dict[str, Any]]:
    """
    Extract element data from graph by GUID.
    Searches through all element types (doors, windows, walls, etc.)
    
    Args:
        graph: IFC graph dict with elements section
        element_guid: GUID of element to find
    
    Returns:
        Element data dict or None if not found
    """
    if not graph or 'elements' not in graph:
        return None
    
    elements = graph.get('elements', {})
    
    # Search through all element types
    for elem_type, elem_list in elements.items():
        if isinstance(elem_list, list):
            for elem in elem_list:
                if isinstance(elem, dict):
                    # Check if this is the element we're looking for
                    if elem.get('guid') == element_guid or elem.get('id') == element_guid:
                        # Extract key properties
                        return {
                            'width_mm': elem.get('width_mm', 1200),
                            'height_mm': elem.get('height_mm', 2400),
                            'clear_width_mm': elem.get('clear_width_mm', 700),
                            'area_m2': elem.get('area_m2', 1.0),
                            'perimeter_m': elem.get('perimeter_m', 5.0),
                            'material': elem.get('material', ''),
                            'type': elem_type,
                            'ifc_type': elem.get('ifc_type', elem_type),
                        }
    
    return None


def _enrich_compliance_results_with_element_data(
    compliance_results: list,
    graph: Optional[Dict[str, Any]] = None
) -> list:
    """
    Enrich compliance results with element_data from graph.
    If graph is provided, extract element properties for each result.
    If graph is not provided, element_data must already be in results.
    
    Args:
        compliance_results: List of compliance check results
        graph: Optional IFC graph to extract element data from
    
    Returns:
        List of enriched compliance results
    """
    enriched = []
    
    for result in compliance_results:
        if not isinstance(result, dict):
            enriched.append(result)
            continue
        
        # Make a copy to avoid modifying original
        enriched_result = dict(result)
        
        # If element_data is missing, try to get it from graph
        if not enriched_result.get('element_data') and graph:
            element_guid = enriched_result.get('element_guid') or enriched_result.get('element_id')
            if element_guid:
                element_data = _get_element_data_from_graph(graph, element_guid)
                if element_data:
                    enriched_result['element_data'] = element_data
                    logger.debug(f"Enriched element {element_guid} with data from graph")
                else:
                    logger.warning(f"Could not find element {element_guid} in graph, using defaults")
                    # Use default element data
                    enriched_result['element_data'] = {
                        'width_mm': 1200,
                        'height_mm': 2400,
                        'clear_width_mm': 700,
                        'area_m2': 1.0,
                        'perimeter_m': 5.0,
                    }
            else:
                # No GUID available, use defaults
                enriched_result['element_data'] = {
                    'width_mm': 1200,
                    'height_mm': 2400,
                    'clear_width_mm': 700,
                    'area_m2': 1.0,
                    'perimeter_m': 5.0,
                }
        elif not enriched_result.get('element_data'):
            # No graph and no element_data - use defaults
            enriched_result['element_data'] = {
                'width_mm': 1200,
                'height_mm': 2400,
                'clear_width_mm': 700,
                'area_m2': 1.0,
                'perimeter_m': 5.0,
            }
        
        enriched.append(enriched_result)
    
    return enriched


def _extract_features_from_result(compliance_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract and convert compliance result to TRM sample
    
    Args:
        compliance_result: Compliance check result
    
    Returns:
        TRM sample dict or None if extraction fails
    """
    try:
        # DEBUG
        with open('data/debug_features.txt', 'a') as f:
            f.write(f"_extract_features_from_result: compliance_result keys = {list(compliance_result.keys())}\n")
            f.write(f"  element_data = {list(compliance_result.get('element_data', {}).keys()) if compliance_result.get('element_data') else 'MISSING'}\n")
        
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


@trm_bp.route('/add-samples-from-compliance', methods=['POST'])
def add_samples_from_compliance():
    """
    Add multiple training samples from compliance check results.
    This is useful when running compliance checks on a new IFC file 
    and wanting to add all results to the training dataset.
    
    Request body:
    {
        "compliance_results": [list of compliance check result objects],
        "ifc_file": "filename.ifc" (optional, for tracking),
        "graph": {IFC graph} (optional, used to recover element_data if missing)
    }
    
    IMPORTANT: If compliance_results don't include element_data (dimensions like width_mm),
    you MUST provide the 'graph' parameter so element data can be extracted.
    
    Response:
    {
        "success": bool,
        "samples_added": int,
        "duplicates_skipped": int,
        "total_samples_in_dataset": int,
        "class_distribution": {"FAIL": int, "PASS": int},
        "error": str or null
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body required"
            }), 400
        
        compliance_results = data.get("compliance_results", [])
        ifc_file = data.get("ifc_file", "unknown.ifc")
        graph = data.get("graph", None)  # Optional graph for enriching element_data
        
        # Enrich compliance results with element_data from graph if needed
        if compliance_results and (graph or any(r.get('element_data') for r in compliance_results)):
            compliance_results = _enrich_compliance_results_with_element_data(compliance_results, graph)
            if graph:
                logger.info(f"Enriched compliance results with element_data from graph")
            else:
                logger.info(f"Using element_data already present in compliance results")
        
        if not isinstance(compliance_results, list):
            return jsonify({
                "success": False,
                "error": "compliance_results must be a list"
            }), 400
        
        if len(compliance_results) == 0:
            return jsonify({
                "success": False,
                "error": "compliance_results list is empty"
            }), 400
        
        logger.info(f"Processing {len(compliance_results)} compliance results from {ifc_file}")
        
        # Load existing dataset to check for duplicates
        dataset_file = Path(trm_system.dataset_path)
        dataset_file.parent.mkdir(parents=True, exist_ok=True)
        
        existing_samples = []
        existing_guids = set()
        if dataset_file.exists():
            try:
                with open(dataset_file, 'r') as f:
                    existing_data = json.load(f)
                    existing_samples = existing_data.get("samples", [])
                    existing_guids = {s.get("element_guid", "") for s in existing_samples}
            except Exception as e:
                logger.warning(f"Could not load existing dataset: {e}")
        
        # Process each compliance result
        samples_added = 0
        duplicates_skipped = 0
        fail_count = 0
        pass_count = 0
        
        for compliance_result in compliance_results:
            try:
                # Extract features
                sample = _extract_features_from_result(compliance_result)
                if sample is None:
                    logger.warning(f"Feature extraction failed for result")
                    continue
                
                # Determine label from compliance result
                compliance_status = compliance_result.get("compliance_result", {})
                
                if isinstance(compliance_status, dict):
                    if "passed" in compliance_status:
                        label = 1 if compliance_status.get("passed", False) else 0
                    elif "result" in compliance_status:
                        label = 1 if compliance_status.get("result", "FAIL").upper() == "PASS" else 0
                    else:
                        label = 0
                else:
                    label = 1 if compliance_result.get("result", "FAIL").upper() == "PASS" else 0
                
                sample["label"] = label
                
                # Count for class distribution
                if label == 0:
                    fail_count += 1
                else:
                    pass_count += 1
                
                # Check for duplicates
                element_guid = sample.get("element_guid", "")
                if element_guid and element_guid in existing_guids:
                    duplicates_skipped += 1
                    continue
                
                # Add to dataset
                result = trm_system.dataset_manager.add_sample(
                    file_path=str(trm_system.dataset_path),
                    sample=sample,
                    ifc_file=ifc_file
                )
                
                if result.get("success"):
                    samples_added += 1
                    existing_guids.add(element_guid)
                    
            except Exception as e:
                logger.warning(f"Error processing compliance result: {e}")
                continue
        
        # Reload dataset to get updated statistics
        try:
            with open(dataset_file, 'r') as f:
                final_data = json.load(f)
                final_samples = final_data.get("samples", [])
                final_labels = [s.get("label", 0) for s in final_samples]
                from collections import Counter
                label_counts = Counter(final_labels)
        except Exception as e:
            label_counts = {}
            logger.error(f"Could not load final dataset: {e}")
        
        response = {
            "success": True,
            "samples_added": samples_added,
            "duplicates_skipped": duplicates_skipped,
            "total_samples_in_dataset": len(final_samples) if 'final_samples' in locals() else 0,
            "class_distribution": {
                "FAIL": label_counts.get(0, 0),
                "PASS": label_counts.get(1, 0)
            }
        }
        
        logger.info(f"Bulk add result: {samples_added} added, {duplicates_skipped} duplicates skipped")
        logger.info(f"Dataset now has {response['total_samples_in_dataset']} total samples")
        
        return jsonify(response), 201
        
    except Exception as e:
        logger.error(f"Error adding samples from compliance: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


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
        request_data = request.get_json() or {}
        
        # Get training parameters
        num_epochs = request_data.get("epochs", 100)
        learning_rate = request_data.get("learning_rate", 0.001)
        batch_size = request_data.get("batch_size", 32)
        resume = request_data.get("resume", False)
        
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
            import random
            dataset_file = Path(str(trm_system.dataset_path))
            if not dataset_file.exists():
                return jsonify({"error": "No training data available"}), 400
            
            with open(dataset_file, 'r') as f:
                dataset_data = json.load(f)
            
            samples = dataset_data.get("samples", [])
            if len(samples) == 0:
                return jsonify({"error": "No training data available"}), 400
            
            # Shuffle samples to ensure representative train/val/test splits
            random.seed(42)  # For reproducibility
            shuffled_samples = samples.copy()
            random.shuffle(shuffled_samples)
            
            # Calculate 80/10/10 split
            total = len(shuffled_samples)
            train_count = int(total * 0.8)
            val_count = int(total * 0.1)
            
            train_samples = shuffled_samples[:train_count]
            val_samples = shuffled_samples[train_count:train_count + val_count]
            test_samples = shuffled_samples[train_count + val_count:]
            
            # Extract labels (1 for PASS, 0 for FAIL)
            train_labels = [s.get("label", 0) for s in train_samples]
            val_labels = [s.get("label", 0) for s in val_samples]
            
            # Log class distribution
            from collections import Counter
            train_label_counts = Counter(train_labels)
            val_label_counts = Counter(val_labels)
            logger.info(f"DEBUG: Training labels - FAIL: {train_label_counts[0]}, PASS: {train_label_counts[1]}")
            logger.info(f"DEBUG: Validation labels - FAIL: {val_label_counts[0]}, PASS: {val_label_counts[1]}")
            
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
                        # Loss metrics
                        "best_val_loss": summary.get("best_val_loss", 0.0),
                        "final_train_loss": summary.get("final_train_loss", 0.0),
                        "final_val_loss": summary.get("final_val_loss", 0.0),
                        
                        # Accuracy metrics (Essential #1, #4)
                        "best_train_accuracy": summary.get("best_train_accuracy", 0.0),
                        "best_val_accuracy": summary.get("best_val_accuracy", 0.0),
                        "overfitting_indicator": summary.get("overfitting_indicator", 0.0),
                        
                        # Precision & Recall (Essential #3)
                        "best_precision": summary.get("best_precision", 0.0),
                        "best_recall": summary.get("best_recall", 0.0),
                        "best_val_f1": summary.get("best_val_f1", 0.0),
                        
                        # Class distribution (Essential #2)
                        "train_fail_count": summary.get("train_fail_count", 0),
                        "train_pass_count": summary.get("train_pass_count", 0),
                        "balance_ratio": summary.get("balance_ratio", 0.0),
                        
                        # Early stopping (Essential #5)
                        "early_stopping_triggered": summary.get("early_stopping_triggered", False),
                        "epochs_without_improvement": summary.get("epochs_without_improvement", 0),
                        
                        # Duration
                        "training_duration_seconds": summary.get("training_duration_seconds", 0.0),
                        "training_duration_minutes": summary.get("training_duration_minutes", 0.0),
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
        
        # Convert training history to JSON-serializable format
        epoch_results = [
            {
                "epoch": m.epoch,
                "train_loss": round(m.loss, 4),
                "train_accuracy": round(m.accuracy, 4),
                "train_precision": round(m.precision, 4),
                "train_recall": round(m.recall, 4),
                "train_f1": round(m.f1, 4),
                "val_loss": round(m.val_loss, 4) if m.val_loss else None,
                "val_accuracy": round(m.val_accuracy, 4) if m.val_accuracy else None,
                "val_f1": round(m.val_f1, 4) if m.val_f1 else None,
                "learning_rate": round(m.learning_rate, 6) if m.learning_rate else None,
            }
            for m in trm_system.trainer.training_history
        ]
        
        return jsonify({
            "success": True,
            "epochs_trained": len(history),
            "best_loss": summary.get("best_val_loss", 0.0),
            "metrics": summary,
            "epoch_results": epoch_results,  # Full epoch-by-epoch results
            "version_id": version_id
        }), 200
    
    except TrainingDataQualityError as e:
        # Handle GUID fragility validation failure
        logger.error(f"Training rejected due to data quality: {e}")
        
        # Extract validation metrics from the error
        validation_metrics = getattr(e, 'validation_metrics', {})
        validation_report = getattr(e, 'validation_report', {})
        
        return jsonify({
            "success": False,
            "validation_failed": True,
            "error": str(e),
            "validation_report": {
                "metrics": validation_metrics,
                "message": "Dataset contains excessive defaults which would reintroduce the 70% accuracy bug",
                "threshold_percent": 20.0
            }
        }), 400
    
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


# ===== Model Versions Endpoints =====

@trm_bp.route('/versions', methods=['GET'])
def get_versions():
    """
    Get all model versions
    
    Response:
    {
        "success": bool,
        "versions": [
            {
                "version_id": str,
                "created_at": str,
                "performance_metrics": dict,
                "training_config": dict,
                "dataset_stats": dict
            }
        ]
    }
    """
    try:
        if not _version_manager:
            return jsonify({
                "success": False,
                "error": "Version manager not available"
            }), 400
        
        versions = _version_manager.get_all_versions()
        
        return jsonify({
            "success": True,
            "versions": versions
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting versions: {e}")
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/versions/<version_id>', methods=['GET'])
def get_version_detail(version_id: str):
    """
    Get details for a specific model version
    
    Response:
    {
        "success": bool,
        "version": {
            "version_id": str,
            "created_at": str,
            "performance_metrics": dict,
            "training_config": dict,
            "dataset_stats": dict,
            "checkpoint_path": str
        }
    }
    """
    try:
        if not _version_manager:
            return jsonify({
                "success": False,
                "error": "Version manager not available"
            }), 400
        
        version = _version_manager.get_version(version_id)
        if not version:
            return jsonify({
                "success": False,
                "error": f"Version {version_id} not found"
            }), 404
        
        return jsonify({
            "success": True,
            "version": version
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting version detail: {e}")
        return jsonify({"error": str(e)}), 500


@trm_bp.route('/versions/<version_id>/activate', methods=['POST'])
def activate_version(version_id: str):
    """
    Activate a specific model version (load into memory)
    
    Response:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        if not _version_manager:
            return jsonify({
                "success": False,
                "error": "Version manager not available"
            }), 400
        
        success = _version_manager.activate_version(version_id)
        if not success:
            return jsonify({
                "success": False,
                "error": f"Failed to activate version {version_id}"
            }), 400
        
        return jsonify({
            "success": True,
            "message": f"Activated version {version_id}"
        }), 200
    
    except Exception as e:
        logger.error(f"Error activating version: {e}")
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
