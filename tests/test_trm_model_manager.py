"""
Tests for Phase 5: Model Management and Versioning System

Tests include:
- Version registration and tracking
- Training history logging
- Version comparison and lineage
- Best version marking
- Version deletion
- Model management API endpoints
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app
from backend.trm_model_manager import ModelVersionManager
from backend.trm_api import trm_system


class TestModelVersionManager(unittest.TestCase):
    """Test ModelVersionManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ModelVersionManager(Path(self.temp_dir))
    
    def tearDown(self):
        """Clean up test fixtures"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_register_version(self):
        """Test registering a new version"""
        version_id = self.manager.register_version(
            checkpoint_path="/path/to/checkpoint.pt",
            training_config={"epochs": 10, "lr": 0.001},
            performance_metrics={"best_val_accuracy": 0.95, "best_val_loss": 0.05},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=3600.0,
            description="First training run"
        )
        
        self.assertEqual(version_id, "v1.0")
        
        # Verify stored
        version = self.manager.get_version(version_id)
        self.assertIsNotNone(version)
        self.assertEqual(version['version_id'], "v1.0")
        self.assertEqual(version['description'], "First training run")
    
    def test_register_multiple_versions(self):
        """Test registering multiple versions increments IDs"""
        v1 = self.manager.register_version(
            checkpoint_path="/path1.pt",
            training_config={"epochs": 10},
            performance_metrics={"best_val_accuracy": 0.90},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=3600.0
        )
        
        v2 = self.manager.register_version(
            checkpoint_path="/path2.pt",
            training_config={"epochs": 20},
            performance_metrics={"best_val_accuracy": 0.95},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=7200.0
        )
        
        self.assertEqual(v1, "v1.0")
        self.assertEqual(v2, "v2.0")
    
    def test_mark_best_version(self):
        """Test marking a version as best"""
        v1 = self.manager.register_version(
            checkpoint_path="/path1.pt",
            training_config={},
            performance_metrics={"best_val_accuracy": 0.90},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=3600.0
        )
        
        v2 = self.manager.register_version(
            checkpoint_path="/path2.pt",
            training_config={},
            performance_metrics={"best_val_accuracy": 0.95},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=3600.0
        )
        
        # Mark v2 as best
        self.manager.mark_best_version(v2)
        
        # Verify
        best = self.manager.get_best_version()
        self.assertEqual(best['version_id'], v2)
        self.assertTrue(best['is_best'])
        
        # Verify v1 is not best
        v1_data = self.manager.get_version(v1)
        self.assertFalse(v1_data.get('is_best', False))
    
    def test_list_versions(self):
        """Test listing versions sorted by creation time"""
        for i in range(5):
            self.manager.register_version(
                checkpoint_path=f"/path{i}.pt",
                training_config={"epochs": 10 * (i + 1)},
                performance_metrics={"best_val_accuracy": 0.85 + i * 0.02},
                dataset_stats={"train": 80, "val": 10, "test": 10},
                training_duration=3600.0
            )
        
        versions = self.manager.list_versions(limit=10)
        
        self.assertEqual(len(versions), 5)
        # Should be sorted newest first
        self.assertEqual(versions[0]['version_id'], "v5.0")
        self.assertEqual(versions[-1]['version_id'], "v1.0")
    
    def test_training_history(self):
        """Test logging and retrieving training history"""
        version_id = self.manager.register_version(
            checkpoint_path="/path.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=3600.0
        )
        
        # Add epoch logs
        for epoch in range(1, 4):
            self.manager.add_training_history_entry(
                version_id=version_id,
                epoch=epoch,
                train_loss=1.0 / epoch,
                val_loss=0.8 / epoch,
                val_accuracy=0.80 + epoch * 0.05
            )
        
        # Retrieve history
        history = self.manager.get_training_history(version_id)
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['epoch'], 1)
        self.assertEqual(history[0]['train_loss'], 1.0)
        self.assertAlmostEqual(history[2]['val_accuracy'], 0.95, places=1)
    
    def test_version_lineage(self):
        """Test tracking version lineage"""
        v1 = self.manager.register_version(
            checkpoint_path="/path1.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=3600.0
        )
        
        v2 = self.manager.register_version(
            checkpoint_path="/path2.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=3600.0,
            parent_version=v1
        )
        
        v3 = self.manager.register_version(
            checkpoint_path="/path3.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=3600.0,
            parent_version=v2
        )
        
        # Get lineage of v3
        lineage = self.manager.get_version_lineage(v3)
        
        self.assertEqual(lineage, [v3, v2, v1])
    
    def test_compare_versions(self):
        """Test comparing multiple versions"""
        v1 = self.manager.register_version(
            checkpoint_path="/path1.pt",
            training_config={"epochs": 10, "lr": 0.001},
            performance_metrics={"best_val_accuracy": 0.90, "best_val_loss": 0.10},
            dataset_stats={"train": 80},
            training_duration=3600.0
        )
        
        v2 = self.manager.register_version(
            checkpoint_path="/path2.pt",
            training_config={"epochs": 20, "lr": 0.0005},
            performance_metrics={"best_val_accuracy": 0.95, "best_val_loss": 0.05},
            dataset_stats={"train": 100},
            training_duration=7200.0
        )
        
        comparison = self.manager.compare_versions([v1, v2])
        
        self.assertEqual(len(comparison['versions']), 2)
        self.assertIn('metric_differences', comparison)
        self.assertIn('config_differences', comparison)
        
        # Check that metrics are compared
        self.assertIn('best_val_accuracy', comparison['metric_differences'])
    
    def test_export_version_report(self):
        """Test exporting comprehensive version report"""
        version_id = self.manager.register_version(
            checkpoint_path="/path.pt",
            training_config={"epochs": 10},
            performance_metrics={"best_val_accuracy": 0.95},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=3600.0,
            description="Test version"
        )
        
        # Add some history
        self.manager.add_training_history_entry(
            version_id, epoch=1, train_loss=0.5, val_loss=0.4
        )
        
        report = self.manager.export_version_report(version_id)
        
        self.assertIn('version', report)
        self.assertIn('training_history', report)
        self.assertIn('lineage', report)
        self.assertIn('exported_at', report)
        
        self.assertEqual(len(report['training_history']), 1)
    
    def test_delete_version(self):
        """Test deleting a version"""
        version_id = self.manager.register_version(
            checkpoint_path="/path.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=3600.0
        )
        
        # Add history
        self.manager.add_training_history_entry(
            version_id, epoch=1, train_loss=0.5, val_loss=0.4
        )
        
        # Delete
        success = self.manager.delete_version(version_id)
        
        self.assertTrue(success)
        
        # Verify deleted
        version = self.manager.get_version(version_id)
        self.assertIsNone(version)
        
        # History should be gone too
        history = self.manager.get_training_history(version_id)
        self.assertEqual(len(history), 0)


class TestModelManagementAPI(unittest.TestCase):
    """Test model management API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        # Create temp directory for versions
        self.temp_dir = tempfile.mkdtemp()
        from backend.app import model_version_manager
        
        # Override paths
        model_version_manager.model_dir = Path(self.temp_dir)
        model_version_manager.versions_file = Path(self.temp_dir) / "versions_manifest.json"
        model_version_manager.history_file = Path(self.temp_dir) / "training_history.json"
        
        self.version_manager = model_version_manager
    
    def tearDown(self):
        """Clean up"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def _register_test_version(self, idx=1):
        """Helper to register a test version"""
        return self.version_manager.register_version(
            checkpoint_path=f"/path{idx}.pt",
            training_config={"epochs": 10 * idx, "lr": 0.001},
            performance_metrics={"best_val_accuracy": 0.85 + idx * 0.05},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=3600.0 * idx,
            description=f"Version {idx}"
        )
    
    def test_list_versions_endpoint(self):
        """Test GET /api/trm/versions"""
        v1 = self._register_test_version(1)
        v2 = self._register_test_version(2)
        
        response = self.client.get('/api/trm/versions')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('versions', data)
        self.assertIn('total_count', data)
        self.assertEqual(len(data['versions']), 2)
    
    def test_get_version_detail(self):
        """Test GET /api/trm/versions/<version_id>"""
        version_id = self._register_test_version(1)
        
        response = self.client.get(f'/api/trm/versions/{version_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('version', data)
        self.assertIn('training_history', data)
        self.assertIn('lineage', data)
        self.assertEqual(data['version']['version_id'], version_id)
    
    def test_get_best_version(self):
        """Test GET /api/trm/versions/best"""
        v1 = self._register_test_version(1)
        v2 = self._register_test_version(2)
        
        self.version_manager.mark_best_version(v2)
        
        response = self.client.get('/api/trm/versions/best')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['version']['version_id'], v2)
    
    def test_mark_best_version(self):
        """Test POST /api/trm/versions/<version_id>/mark-best"""
        v1 = self._register_test_version(1)
        
        response = self.client.post(f'/api/trm/versions/{v1}/mark-best')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['version_id'], v1)
    
    def test_compare_versions(self):
        """Test POST /api/trm/versions/compare"""
        v1 = self._register_test_version(1)
        v2 = self._register_test_version(2)
        
        payload = {
            "version_ids": [v1, v2]
        }
        
        response = self.client.post(
            '/api/trm/versions/compare',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('versions', data)
        self.assertEqual(len(data['versions']), 2)
    
    def test_get_training_history(self):
        """Test GET /api/trm/versions/<version_id>/history"""
        version_id = self._register_test_version(1)
        
        # Add history
        for epoch in range(1, 4):
            self.version_manager.add_training_history_entry(
                version_id, epoch=epoch, train_loss=0.5/epoch, val_loss=0.4/epoch
            )
        
        response = self.client.get(f'/api/trm/versions/{version_id}/history')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('epochs', data)
        self.assertEqual(len(data['epochs']), 3)
    
    def test_export_report(self):
        """Test GET /api/trm/versions/<version_id>/export"""
        version_id = self._register_test_version(1)
        
        response = self.client.get(f'/api/trm/versions/{version_id}/export')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('version', data)
        self.assertIn('training_history', data)
        self.assertIn('lineage', data)


if __name__ == '__main__':
    unittest.main()
