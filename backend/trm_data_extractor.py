"""
TRM Data Extractor - Phase 1: Backend Data Pipeline (Incremental)

Converts compliance check results into incremental training samples.
Supports one-at-a-time sample addition with duplicate detection.

Classes:
    - ComplianceResultToTRMSample: Converts compliance check → training sample
    - IncrementalDatasetManager: Manages append-only training data file
"""

import json
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ComplianceResultToTRMSample:
    """
    Converts a single compliance check result into a TRM training sample.
    
    Input: element + rule + compliance result
    Output: 320-dimensional training sample (128 + 128 + 64)
    """
    
    def __init__(self):
        """Initialize the converter"""
        self.element_type_mapping = {
            "IfcDoor": [1.0, 0.0, 0.0, 0.0, 0.0],
            "IfcWindow": [0.0, 1.0, 0.0, 0.0, 0.0],
            "IfcRoom": [0.0, 0.0, 1.0, 0.0, 0.0],
            "IfcWall": [0.0, 0.0, 0.0, 1.0, 0.0],
            "IfcSpace": [0.0, 0.0, 0.0, 0.0, 1.0],
        }
        
        self.material_mapping = {
            "wood": [1.0, 0.0, 0.0, 0.0, 0.0],
            "concrete": [0.0, 1.0, 0.0, 0.0, 0.0],
            "steel": [0.0, 0.0, 1.0, 0.0, 0.0],
            "glass": [0.0, 0.0, 0.0, 1.0, 0.0],
            "other": [0.0, 0.0, 0.0, 0.0, 1.0],
        }
        
        self.severity_mapping = {
            "ERROR": [1.0, 0.0, 0.0],
            "WARNING": [0.0, 1.0, 0.0],
            "INFO": [0.0, 0.0, 1.0],
        }
        
        self.regulation_mapping = {
            "ADA Standards": [1.0, 0.0, 0.0],
            "IBC": [0.0, 1.0, 0.0],
            "Custom": [0.0, 0.0, 1.0],
        }

    def extract_element_features(self, element_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract element properties into 128-dimensional feature vector.
        
        Components:
        - Numeric features (normalized): width, height, area, perimeter
        - Element type encoding: one-hot vector
        - Material encoding: one-hot vector
        - Other properties: fire rating, status, etc.
        
        Args:
            element_data: dict with element properties
        
        Returns:
            128-dimensional numpy array
        """
        features = []
        
        # 1. Normalize numeric features (positions 0-19)
        numeric_features = [
            element_data.get("width_mm", 0) / 1000.0,  # normalize to 0-1
            element_data.get("height_mm", 0) / 10000.0,
            element_data.get("clear_width_mm", 0) / 1000.0,
            element_data.get("area_m2", 0) / 100.0,
            element_data.get("perimeter_m", 0) / 100.0,
            1.0 if element_data.get("fire_rating") else 0.0,
            1.0 if element_data.get("acoustic") else 0.0,
            0.5,  # placeholder features
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
        ]
        features.extend(numeric_features)
        
        # 2. Element type encoding (positions 20-24, one-hot)
        element_type = element_data.get("type", "IfcDoor")
        type_encoding = self.element_type_mapping.get(element_type, [0.0, 0.0, 0.0, 0.0, 1.0])
        features.extend(type_encoding)
        
        # 3. Material encoding (positions 25-29, one-hot)
        material = element_data.get("material", "other").lower()
        material_encoding = self.material_mapping.get(material, [0.0, 0.0, 0.0, 0.0, 1.0])
        features.extend(material_encoding)
        
        # 4. Status and approval flags (positions 30-34)
        status_encoding = [
            1.0 if element_data.get("status") == "approved" else 0.0,
            1.0 if element_data.get("status") == "pending" else 0.0,
            1.0 if element_data.get("status") == "rejected" else 0.0,
            0.5,  # placeholder
            0.5,
        ]
        features.extend(status_encoding)
        
        # 5. Fill remaining to reach 128 dimensions
        while len(features) < 128:
            features.append(0.5)
        
        # Trim to exactly 128
        features = features[:128]
        
        return np.array(features, dtype=np.float32)

    def extract_rule_features(self, rule_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract rule properties into 128-dimensional feature vector.
        
        Components:
        - Severity encoding: one-hot vector
        - Regulation encoding: one-hot vector
        - Parameter values (normalized)
        - Rule type and complexity
        
        Args:
            rule_data: dict with rule definition
        
        Returns:
            128-dimensional numpy array
        """
        features = []
        
        # 1. Severity encoding (positions 0-2)
        severity = rule_data.get("severity", "INFO")
        severity_encoding = self.severity_mapping.get(severity, [0.0, 0.0, 1.0])
        features.extend(severity_encoding)
        
        # 2. Regulation encoding (positions 3-5)
        regulation = rule_data.get("regulation", "Custom")
        regulation_encoding = self.regulation_mapping.get(regulation, [0.0, 0.0, 1.0])
        features.extend(regulation_encoding)
        
        # 3. Rule name hashing (positions 6-15) - simple hash encoding
        rule_name = rule_data.get("name", "")
        name_hash = hash(rule_name) % 1000
        name_features = [(name_hash >> i) & 1 for i in range(10)]
        features.extend([float(x) for x in name_features])
        
        # 4. Parameter values (positions 16-35, normalized)
        parameters = rule_data.get("parameters", {})
        param_features = []
        for param_key in list(parameters.keys())[:20]:
            param_value = parameters.get(param_key, 0)
            if isinstance(param_value, (int, float)):
                # Normalize to 0-1 range
                normalized = min(float(param_value) / 1000.0, 1.0)
                param_features.append(normalized)
            else:
                param_features.append(0.5)
        
        # Pad to 20 parameters
        while len(param_features) < 20:
            param_features.append(0.5)
        features.extend(param_features[:20])
        
        # 5. Rule complexity indicators (positions 36-45)
        num_params = len(parameters)
        complexity_features = [
            min(num_params / 10.0, 1.0),  # parameter count normalized
            1.0 if "min" in rule_name.lower() else 0.0,
            1.0 if "max" in rule_name.lower() else 0.0,
            1.0 if "range" in rule_name.lower() else 0.0,
            1.0 if "equals" in rule_name.lower() else 0.0,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
        ]
        features.extend(complexity_features)
        
        # 6. Fill remaining to reach 128 dimensions
        while len(features) < 128:
            features.append(0.5)
        
        # Trim to exactly 128
        features = features[:128]
        
        return np.array(features, dtype=np.float32)

    def extract_context(self, element_data: Dict[str, Any], rule_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract context embedding combining element and rule information.
        
        Components:
        - Element-rule affinity score
        - Compliance difficulty indicator
        - Safety criticality
        - Regulatory relevance
        
        Args:
            element_data: element properties
            rule_data: rule definition
        
        Returns:
            64-dimensional numpy array
        """
        features = []
        
        # 1. Element-rule affinity (how relevant is this rule to this element?)
        element_type = element_data.get("type", "IfcDoor")
        rule_targets = rule_data.get("target", {})
        target_type = rule_targets.get("ifc_class", "IfcDoor")
        
        affinity = 1.0 if element_type == target_type else 0.5
        features.append(affinity)
        
        # 2. Compliance difficulty (based on rule severity)
        severity = rule_data.get("severity", "INFO")
        difficulty_map = {"ERROR": 0.9, "WARNING": 0.5, "INFO": 0.1}
        difficulty = difficulty_map.get(severity, 0.5)
        features.append(difficulty)
        
        # 3. Safety criticality
        is_safety_critical = 1.0 if "fire" in rule_data.get("name", "").lower() else 0.0
        is_safety_critical = max(is_safety_critical, 1.0 if "structural" in rule_data.get("name", "").lower() else 0.0)
        features.append(is_safety_critical)
        
        # 4. Regulatory importance (ADA > IBC > Custom)
        regulation = rule_data.get("regulation", "Custom")
        reg_importance = {"ADA Standards": 0.9, "IBC": 0.7, "Custom": 0.3}.get(regulation, 0.3)
        features.append(reg_importance)
        
        # 5. Element completeness (does element have required data?)
        required_fields = ["type", "width_mm", "height_mm"]
        completeness = sum(1.0 for field in required_fields if element_data.get(field)) / len(required_fields)
        features.append(completeness)
        
        # 6-64: Additional context features
        for i in range(59):
            features.append(0.5)
        
        return np.array(features[:64], dtype=np.float32)

    def convert(self, compliance_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert compliance check result to training sample.
        
        Args:
            compliance_result: dict with element, rule, and compliance data
            
        Returns:
            dict with training sample (features + label + metadata)
        """
        element_data = compliance_result.get("element_data", {})
        rule_data = compliance_result.get("rule_data", {})
        check_result = compliance_result.get("compliance_result", {})
        
        # Extract features
        element_features = self.extract_element_features(element_data)
        rule_context = self.extract_rule_features(rule_data)
        context_embedding = self.extract_context(element_data, rule_data)
        
        # Create label
        label = 1 if check_result.get("passed", False) else 0
        
        # Get rule_id from either rule_data or compliance_result
        rule_id = compliance_result.get("rule_id") or rule_data.get("id") or rule_data.get("name", "unknown")
        
        # Return training sample - convert numpy arrays to lists for JSON serialization
        return {
            "element_guid": compliance_result.get("element_guid", "unknown"),
            "element_features": element_features.tolist(),  # Convert to list for JSON
            "rule_context": rule_context.tolist(),  # Convert to list for JSON
            "context_embedding": context_embedding.tolist(),  # Convert to list for JSON
            "label": int(label),  # Ensure it's a Python int, not numpy int
            "metadata": {
                "element_guid": compliance_result.get("element_guid", "unknown"),
                "ifc_file": element_data.get("ifc_file", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "rule_id": rule_id,
                "element_type": element_data.get("type", "unknown"),
                "rule_severity": rule_data.get("severity", "INFO"),
                "passed": check_result.get("passed", False),
            }
        }


class IncrementalDatasetManager:
    """
    Manages incremental training data file with append-only semantics.
    
    Features:
    - Load/create JSON file for training samples
    - Add samples one at a time with duplicate detection
    - Track which IFC files have been processed
    - Maintain 80/10/10 train/val/test split
    - Export data as numpy arrays for training
    """
    
    def __init__(self):
        """Initialize the dataset manager"""
        self.logger = logging.getLogger(__name__)

    def load_or_create(self, file_path: str) -> Dict[str, Any]:
        """
        Load existing dataset or create empty structure.
        
        Args:
            file_path: path to trm_incremental_data.json
        
        Returns:
            dict with samples and metadata
        """
        file_path = Path(file_path)
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded existing dataset: {len(data.get('samples', []))} samples")
                    return data
            except Exception as e:
                self.logger.warning(f"Error loading dataset: {e}. Creating new.")
        
        # Create new structure
        return {
            "samples": [],
            "metadata": {
                "total_samples": 0,
                "train_samples": 0,
                "val_samples": 0,
                "test_samples": 0,
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "ifc_files_processed": []
            }
        }

    def _sample_exists(self, data: Dict[str, Any], new_sample: Dict[str, Any]) -> bool:
        """
        Check if sample already exists (duplicate detection).
        
        Compares: element_guid + rule_id + label (pass/fail)
        
        Args:
            data: existing dataset
            new_sample: sample to check
        
        Returns:
            True if duplicate found, False otherwise
        """
        element_guid = new_sample.get("element_guid")
        rule_id = new_sample.get("metadata", {}).get("rule_id")
        label = new_sample.get("label")
        
        for existing_sample in data.get("samples", []):
            if (existing_sample.get("element_guid") == element_guid and
                existing_sample.get("metadata", {}).get("rule_id") == rule_id and
                existing_sample.get("label") == label):
                return True
        
        return False

    def add_sample(self, file_path: str, sample: Dict[str, Any], ifc_file: str) -> Dict[str, Any]:
        """
        Add ONE training sample to incremental dataset.
        
        Validates:
        - Sample is not a duplicate
        - element_guid exists
        - rule_id exists
        
        Args:
            file_path: path to trm_incremental_data.json
            sample: training sample from ComplianceResultToTRMSample
            ifc_file: name of IFC file (for tracking)
        
        Returns:
            dict with result (success/error) and metadata
        """
        file_path = Path(file_path)
        
        # Load existing data
        data = self.load_or_create(str(file_path))
        
        # VALIDATION 1: Check required fields
        if not sample.get("element_guid"):
            self.logger.warning("Sample missing element_guid")
            return {
                "success": False,
                "error": "Invalid sample",
                "reason": "element_guid is required"
            }
        
        if not sample.get("metadata", {}).get("rule_id"):
            self.logger.warning("Sample missing rule_id")
            return {
                "success": False,
                "error": "Invalid sample",
                "reason": "rule_id is required"
            }
        
        # VALIDATION 2: Check for duplicates
        if self._sample_exists(data, sample):
            self.logger.warning(f"Duplicate sample detected: {sample.get('element_guid')} + {sample.get('metadata', {}).get('rule_id')}")
            return {
                "success": False,
                "error": "Duplicate sample",
                "reason": f"Sample for {sample.get('element_guid')} + {sample.get('metadata', {}).get('rule_id')} already exists",
                "total_samples": len(data["samples"])
            }
        
        # All validations passed → Add sample
        data["samples"].append(sample)
        
        # Update metadata
        total = len(data["samples"])
        data["metadata"]["total_samples"] = total
        data["metadata"]["last_updated"] = datetime.utcnow().isoformat()
        
        # Track IFC files
        if ifc_file not in data["metadata"]["ifc_files_processed"]:
            data["metadata"]["ifc_files_processed"].append(ifc_file)
        
        # Re-split data (80/10/10)
        train_count = int(total * 0.8)
        val_count = int(total * 0.1)
        test_count = total - train_count - val_count
        
        data["metadata"]["train_samples"] = train_count
        data["metadata"]["val_samples"] = val_count
        data["metadata"]["test_samples"] = test_count
        
        # Save to file
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Sample added. Total: {total} (train: {train_count}, val: {val_count}, test: {test_count})")
        except Exception as e:
            self.logger.error(f"Error saving dataset: {e}")
            return {
                "success": False,
                "error": "Save failed",
                "reason": str(e)
            }
        
        return {
            "success": True,
            "sample_added": True,
            "metadata": data["metadata"]
        }

    def get_statistics(self, file_path: str) -> Dict[str, Any]:
        """
        Get current dataset statistics.
        
        Args:
            file_path: path to trm_incremental_data.json
        
        Returns:
            dict with dataset statistics
        """
        data = self.load_or_create(file_path)
        return data.get("metadata", {})

    def get_training_data_arrays(self, file_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Export training data as numpy arrays.
        
        Returns train/val/test split ready for Phase 3 training.
        
        Args:
            file_path: path to trm_incremental_data.json
        
        Returns:
            tuple: (X_train, y_train, X_val, y_val, X_test, y_test)
        """
        data = self.load_or_create(file_path)
        samples = data.get("samples", [])
        total = len(samples)
        
        if total == 0:
            self.logger.warning("No training samples available")
            # Return properly shaped empty arrays
            return (np.empty((0, 320), dtype=np.float32), 
                    np.empty((0,), dtype=np.int32),
                    np.empty((0, 320), dtype=np.float32), 
                    np.empty((0,), dtype=np.int32),
                    np.empty((0, 320), dtype=np.float32), 
                    np.empty((0,), dtype=np.int32))
        
        train_count = int(total * 0.8)
        val_count = int(total * 0.1)
        
        # Split samples
        train_samples = samples[:train_count]
        val_samples = samples[train_count:train_count + val_count]
        test_samples = samples[train_count + val_count:]
        
        def _samples_to_arrays(sample_list):
            """Convert sample list to X, y arrays"""
            if not sample_list:
                return np.empty((0, 320), dtype=np.float32), np.empty((0,), dtype=np.int32)
            
            X = []
            y = []
            for sample in sample_list:
                # Handle both numpy arrays and lists
                elem_feat = sample.get("element_features", [0]*128)
                rule_ctx = sample.get("rule_context", [0]*128)
                ctx_embed = sample.get("context_embedding", [0]*64)
                
                # Convert to numpy arrays if they're lists
                if isinstance(elem_feat, list):
                    elem_feat = np.array(elem_feat, dtype=np.float32)
                elif isinstance(elem_feat, np.ndarray):
                    elem_feat = elem_feat.astype(np.float32)
                
                if isinstance(rule_ctx, list):
                    rule_ctx = np.array(rule_ctx, dtype=np.float32)
                elif isinstance(rule_ctx, np.ndarray):
                    rule_ctx = rule_ctx.astype(np.float32)
                
                if isinstance(ctx_embed, list):
                    ctx_embed = np.array(ctx_embed, dtype=np.float32)
                elif isinstance(ctx_embed, np.ndarray):
                    ctx_embed = ctx_embed.astype(np.float32)
                
                # Concatenate: element (128) + rule (128) + context (64) = 320-dim
                features = np.concatenate([elem_feat, rule_ctx, ctx_embed])
                X.append(features)
                y.append(sample.get("label", 0))
            
            return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)
        
        X_train, y_train = _samples_to_arrays(train_samples)
        X_val, y_val = _samples_to_arrays(val_samples)
        X_test, y_test = _samples_to_arrays(test_samples)
        
        self.logger.info(f"Exported arrays: train={X_train.shape}, val={X_val.shape}, test={X_test.shape}")
        
        return X_train, y_train, X_val, y_val, X_test, y_test


# Convenience functions for API usage
def convert_compliance_result_to_sample(compliance_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to convert compliance result to training sample.
    
    Args:
        compliance_result: dict with element, rule, compliance data
    
    Returns:
        training sample dict
    """
    converter = ComplianceResultToTRMSample()
    return converter.convert(compliance_result)


def add_training_sample(file_path: str, sample: Dict[str, Any], ifc_file: str) -> Dict[str, Any]:
    """
    Convenience function to add sample to dataset.
    
    Args:
        file_path: path to trm_incremental_data.json
        sample: training sample
        ifc_file: IFC file name
    
    Returns:
        result dict (success/error)
    """
    manager = IncrementalDatasetManager()
    return manager.add_sample(file_path, sample, ifc_file)


def get_dataset_statistics(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to get dataset statistics.
    
    Args:
        file_path: path to trm_incremental_data.json
    
    Returns:
        statistics dict
    """
    manager = IncrementalDatasetManager()
    return manager.get_statistics(file_path)


def get_training_arrays(file_path: str) -> Tuple:
    """
    Convenience function to get training arrays.
    
    Args:
        file_path: path to trm_incremental_data.json
    
    Returns:
        tuple of numpy arrays
    """
    manager = IncrementalDatasetManager()
    return manager.get_training_data_arrays(file_path)
