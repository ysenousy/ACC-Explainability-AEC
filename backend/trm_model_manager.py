"""
Phase 5: Model Versioning and Management System

Tracks model versions, training history, performance metrics, and enables
rollback to previous versions. Provides model comparison and lineage tracking.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import shutil

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    """Metadata for a model version"""
    version_id: str  # e.g., "v1.0", "v1.1", etc.
    created_at: str  # ISO timestamp
    training_config: Dict[str, Any]  # epochs, lr, batch_size, etc.
    performance_metrics: Dict[str, float]  # loss, accuracy, f1, etc.
    dataset_stats: Dict[str, int]  # train/val/test counts
    training_duration_seconds: float
    is_best: bool = False
    description: str = ""
    checkpoint_path: str = ""
    parent_version: Optional[str] = None  # For tracking lineage


class ModelVersionManager:
    """Manages model versions, training history, and comparisons"""
    
    def __init__(self, model_dir: Path):
        """
        Initialize model manager
        
        Args:
            model_dir: Directory containing model checkpoints
        """
        self.model_dir = Path(model_dir)
        self.versions_file = self.model_dir / "versions_manifest.json"
        self.history_file = self.model_dir / "training_history.json"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ModelVersionManager initialized at {self.model_dir}")
    
    def register_version(self,
                        checkpoint_path: str,
                        training_config: Dict[str, Any],
                        performance_metrics: Dict[str, float],
                        dataset_stats: Dict[str, int],
                        training_duration: float,
                        description: str = "",
                        parent_version: Optional[str] = None) -> str:
        """
        Register a new model version
        
        Args:
            checkpoint_path: Path to model checkpoint
            training_config: Training parameters
            performance_metrics: Model performance metrics
            dataset_stats: Dataset split statistics
            training_duration: Training time in seconds
            description: Version description
            parent_version: ID of parent version (for lineage)
        
        Returns:
            version_id: Unique identifier for this version
        """
        versions = self._load_versions()
        
        # Generate version ID
        version_num = len(versions) + 1
        version_id = f"v{version_num}.0"
        
        # Create version metadata
        version = ModelVersion(
            version_id=version_id,
            created_at=datetime.utcnow().isoformat(),
            training_config=training_config,
            performance_metrics=performance_metrics,
            dataset_stats=dataset_stats,
            training_duration_seconds=training_duration,
            description=description,
            checkpoint_path=checkpoint_path,
            parent_version=parent_version
        )
        
        # Store version
        versions[version_id] = asdict(version)
        self._save_versions(versions)
        
        logger.info(f"Registered model version {version_id}")
        return version_id
    
    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific version"""
        versions = self._load_versions()
        return versions.get(version_id)
    
    def list_versions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List all versions sorted by creation time (newest first)
        
        Args:
            limit: Max number of versions to return
        
        Returns:
            List of version metadata dicts
        """
        versions = self._load_versions()
        sorted_versions = sorted(
            versions.values(),
            key=lambda v: v['created_at'],
            reverse=True
        )
        return sorted_versions[:limit]
    
    def get_best_version(self) -> Optional[Dict[str, Any]]:
        """Get the best performing version"""
        versions = self._load_versions()
        best_versions = [v for v in versions.values() if v.get('is_best')]
        if best_versions:
            return best_versions[0]
        
        # If no explicit best, return highest accuracy
        if versions:
            return max(
                versions.values(),
                key=lambda v: v.get('performance_metrics', {}).get('best_val_accuracy', 0)
            )
        return None
    
    def mark_best_version(self, version_id: str) -> bool:
        """Mark a version as the best performing"""
        versions = self._load_versions()
        
        if version_id not in versions:
            logger.warning(f"Version {version_id} not found")
            return False
        
        # Unmark all others
        for v in versions.values():
            v['is_best'] = False
        
        # Mark this one as best
        versions[version_id]['is_best'] = True
        self._save_versions(versions)
        
        logger.info(f"Marked {version_id} as best")
        return True
    
    def compare_versions(self, version_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple versions side-by-side
        
        Args:
            version_ids: List of version IDs to compare
        
        Returns:
            Comparison dict with metrics and config differences
        """
        versions = self._load_versions()
        comparison = {
            "versions": [],
            "metric_differences": {},
            "config_differences": {}
        }
        
        selected_versions = []
        for vid in version_ids:
            if vid in versions:
                selected_versions.append(versions[vid])
        
        if not selected_versions:
            return comparison
        
        # Add version summaries
        for v in selected_versions:
            comparison["versions"].append({
                "id": v['version_id'],
                "created_at": v['created_at'],
                "best_val_accuracy": v.get('performance_metrics', {}).get('best_val_accuracy', 0),
                "best_val_loss": v.get('performance_metrics', {}).get('best_val_loss', 0)
            })
        
        # Find metric differences
        if len(selected_versions) > 1:
            metrics_list = [v.get('performance_metrics', {}) for v in selected_versions]
            all_keys = set()
            for m in metrics_list:
                all_keys.update(m.keys())
            
            for key in all_keys:
                values = [m.get(key, None) for m in metrics_list]
                if len(set(str(v) for v in values)) > 1:  # Values differ
                    comparison["metric_differences"][key] = values
        
        # Find config differences
        if len(selected_versions) > 1:
            config_list = [v.get('training_config', {}) for v in selected_versions]
            all_keys = set()
            for c in config_list:
                all_keys.update(c.keys())
            
            for key in all_keys:
                values = [c.get(key, None) for c in config_list]
                if len(set(str(v) for v in values)) > 1:  # Values differ
                    comparison["config_differences"][key] = values
        
        return comparison
    
    def get_version_lineage(self, version_id: str) -> List[str]:
        """Get the lineage (ancestry) of a version"""
        versions = self._load_versions()
        lineage = [version_id]
        
        current_id = version_id
        while current_id:
            v = versions.get(current_id)
            if not v or not v.get('parent_version'):
                break
            current_id = v['parent_version']
            lineage.append(current_id)
        
        return lineage
    
    def add_training_history_entry(self,
                                   version_id: str,
                                   epoch: int,
                                   train_loss: float,
                                   val_loss: float,
                                   val_accuracy: Optional[float] = None) -> None:
        """
        Log a training epoch to history
        
        Args:
            version_id: Model version ID
            epoch: Epoch number
            train_loss: Training loss
            val_loss: Validation loss
            val_accuracy: Validation accuracy (optional)
        """
        history = self._load_history()
        
        if version_id not in history:
            history[version_id] = []
        
        entry = {
            "epoch": epoch,
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
            "val_accuracy": float(val_accuracy) if val_accuracy is not None else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        history[version_id].append(entry)
        self._save_history(history)
    
    def get_training_history(self, version_id: str) -> List[Dict[str, Any]]:
        """Get training history for a version"""
        history = self._load_history()
        return history.get(version_id, [])
    
    def delete_version(self, version_id: str) -> bool:
        """
        Delete a version and its checkpoint
        
        Args:
            version_id: Version to delete
        
        Returns:
            True if successful
        """
        versions = self._load_versions()
        
        if version_id not in versions:
            logger.warning(f"Version {version_id} not found")
            return False
        
        version = versions[version_id]
        checkpoint_path = Path(version.get('checkpoint_path', ''))
        
        # Delete checkpoint file if it exists
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
                logger.info(f"Deleted checkpoint {checkpoint_path}")
            except Exception as e:
                logger.error(f"Failed to delete checkpoint: {e}")
        
        # Remove version metadata
        del versions[version_id]
        self._save_versions(versions)
        
        # Remove history
        history = self._load_history()
        if version_id in history:
            del history[version_id]
            self._save_history(history)
        
        logger.info(f"Deleted version {version_id}")
        return True
    
    def export_version_report(self, version_id: str) -> Dict[str, Any]:
        """Export a comprehensive report for a version"""
        version = self.get_version(version_id)
        if not version:
            return {}
        
        history = self.get_training_history(version_id)
        lineage = self.get_version_lineage(version_id)
        
        return {
            "version": version,
            "training_history": history,
            "lineage": lineage,
            "exported_at": datetime.utcnow().isoformat()
        }
    
    def get_all_versions(self) -> List[Dict[str, Any]]:
        """
        Get all available versions (alias for list_versions with no limit)
        
        Returns:
            List of all version metadata dicts
        """
        versions = self._load_versions()
        return sorted(
            versions.values(),
            key=lambda v: v['created_at'],
            reverse=True
        )
    
    def activate_version(self, version_id: str) -> bool:
        """
        Activate a specific model version (mark as active for inference)
        
        Args:
            version_id: Version ID to activate
        
        Returns:
            Success boolean
        """
        versions = self._load_versions()
        
        if version_id not in versions:
            logger.warning(f"Version {version_id} not found")
            return False
        
        # Mark this version as active
        versions[version_id]['is_active'] = True
        
        # Deactivate others
        for v in versions.values():
            if v['version_id'] != version_id:
                v['is_active'] = False
        
        self._save_versions(versions)
        logger.info(f"Activated version {version_id}")
        return True
    
    def _load_versions(self) -> Dict[str, Any]:
        """Load versions manifest"""
        if not self.versions_file.exists():
            return {}
        
        try:
            with open(self.versions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading versions: {e}")
            return {}
    
    def _save_versions(self, versions: Dict[str, Any]) -> None:
        """Save versions manifest"""
        try:
            with open(self.versions_file, 'w') as f:
                json.dump(versions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving versions: {e}")
    
    def _load_history(self) -> Dict[str, List]:
        """Load training history"""
        if not self.history_file.exists():
            return {}
        
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return {}
    
    def _save_history(self, history: Dict[str, List]) -> None:
        """Save training history"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
