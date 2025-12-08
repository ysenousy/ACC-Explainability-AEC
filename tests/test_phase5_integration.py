"""
Phase 5 Integration Tests: Model Management System

Tests end-to-end workflows combining:
- TRM training and versioning
- Model comparison and selection
- Training history tracking
- Dashboard data flow
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app
from backend.trm_api import trm_system
from backend.trm_model_manager import ModelVersionManager


class TestPhase5Integration(unittest.TestCase):
    """Integration tests for Phase 5 Model Management"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        # Set up temp directories
        self.temp_dir = tempfile.mkdtemp()
        self.dataset_path = Path(self.temp_dir) / "dataset.json"
        self.checkpoint_dir = Path(self.temp_dir) / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Override paths in TRM system
        trm_system.dataset_path = self.dataset_path
        trm_system.model_checkpoint_dir = self.checkpoint_dir
        
        # Set up version manager
        from backend.app import model_version_manager
        model_version_manager.model_dir = Path(self.temp_dir) / "versions"
        model_version_manager.versions_file = Path(self.temp_dir) / "versions" / "versions_manifest.json"
        model_version_manager.history_file = Path(self.temp_dir) / "versions" / "training_history.json"
        model_version_manager.model_dir.mkdir(exist_ok=True)
        
        self.version_manager = model_version_manager
    
    def tearDown(self):
        """Clean up"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def _add_training_samples(self, count=10):
        """Helper to add training samples"""
        for i in range(count):
            payload = {
                "compliance_result": {
                    "element_guid": f"element-{i}",
                    "element_data": {
                        "type": "IfcDoor",
                        "name": f"Test {i}",
                        "width_mm": 950,
                        "height_mm": 2100,
                        "material": "wood",
                        "fire_rating": "60"
                    },
                    "rule_id": f"rule-{i % 3}",
                    "rule_name": "Test Rule",
                    "result": "PASS" if i % 2 == 0 else "FAIL"
                },
                "ifc_file": "test.ifc"
            }
            
            response = self.client.post(
                '/api/trm/add-sample',
                data=json.dumps(payload),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 201)
    
    def test_workflow_add_analyze_train_version(self):
        """Test: Add samples → Analyze → Train → Version workflow"""
        
        # 1. Add training samples
        self._add_training_samples(10)
        
        # 2. Verify dataset has data
        response = self.client.get('/api/trm/dataset/stats')
        self.assertEqual(response.status_code, 200)
        stats = json.loads(response.data)
        self.assertGreater(stats['total_samples'], 0)
        
        # 3. Analyze a sample
        payload = {
            "compliance_result": {
                "element_guid": "test-elem",
                "element_data": {
                    "type": "IfcDoor",
                    "width_mm": 950,
                    "height_mm": 2100
                },
                "rule_id": "rule-1"
            }
        }
        response = self.client.post(
            '/api/trm/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 4. Train model
        train_payload = {
            "epochs": 2,
            "learning_rate": 0.001,
            "batch_size": 2
        }
        response = self.client.post(
            '/api/trm/train',
            data=json.dumps(train_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        train_data = json.loads(response.data)
        self.assertTrue(train_data['success'])
        
        # 5. Register version
        version_id = self.version_manager.register_version(
            checkpoint_path=str(self.checkpoint_dir / "best.pt"),
            training_config={"epochs": 2, "lr": 0.001},
            performance_metrics=train_data['metrics'],
            dataset_stats=stats,
            training_duration=train_data['metrics']['total_epochs'] * 60,
            description="First training run"
        )
        
        # 6. Verify version exists
        version = self.version_manager.get_version(version_id)
        self.assertIsNotNone(version)
        self.assertEqual(version['version_id'], version_id)
    
    def test_multiple_training_runs_and_comparison(self):
        """Test: Multiple training runs with versioning and comparison"""
        
        # Run 1
        self._add_training_samples(10)
        
        train1 = self.client.post(
            '/api/trm/train',
            data=json.dumps({"epochs": 2, "learning_rate": 0.001}),
            content_type='application/json'
        )
        self.assertEqual(train1.status_code, 200)
        
        v1 = self.version_manager.register_version(
            checkpoint_path=str(self.checkpoint_dir / "v1.pt"),
            training_config={"epochs": 2},
            performance_metrics=json.loads(train1.data)['metrics'],
            dataset_stats={"train": 8, "val": 1, "test": 1},
            training_duration=120.0,
            description="Run 1 - baseline"
        )
        
        # Run 2 - different config
        train2 = self.client.post(
            '/api/trm/train',
            data=json.dumps({"epochs": 4, "learning_rate": 0.0005}),
            content_type='application/json'
        )
        self.assertEqual(train2.status_code, 200)
        
        v2 = self.version_manager.register_version(
            checkpoint_path=str(self.checkpoint_dir / "v2.pt"),
            training_config={"epochs": 4},
            performance_metrics=json.loads(train2.data)['metrics'],
            dataset_stats={"train": 8, "val": 1, "test": 1},
            training_duration=240.0,
            description="Run 2 - more epochs"
        )
        
        # Compare versions via API
        response = self.client.post(
            '/api/trm/versions/compare',
            data=json.dumps({"version_ids": [v1, v2]}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        comparison = json.loads(response.data)
        
        self.assertEqual(len(comparison['versions']), 2)
        self.assertIn('metric_differences', comparison)
        self.assertIn('config_differences', comparison)
    
    def test_best_version_workflow(self):
        """Test: Mark best version and retrieve it"""
        
        # Create two versions
        v1 = self.version_manager.register_version(
            checkpoint_path="/p1.pt",
            training_config={},
            performance_metrics={"best_val_accuracy": 0.85},
            dataset_stats={},
            training_duration=100.0
        )
        
        v2 = self.version_manager.register_version(
            checkpoint_path="/p2.pt",
            training_config={},
            performance_metrics={"best_val_accuracy": 0.95},
            dataset_stats={},
            training_duration=100.0
        )
        
        # Mark v2 as best via API
        response = self.client.post(f'/api/trm/versions/{v2}/mark-best')
        self.assertEqual(response.status_code, 200)
        
        # Get best version via API
        response = self.client.get('/api/trm/versions/best')
        self.assertEqual(response.status_code, 200)
        best_data = json.loads(response.data)
        
        self.assertEqual(best_data['version']['version_id'], v2)
    
    def test_version_lineage_tracking(self):
        """Test: Track version lineage through parent versions"""
        
        v1 = self.version_manager.register_version(
            checkpoint_path="/p1.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=100.0
        )
        
        v2 = self.version_manager.register_version(
            checkpoint_path="/p2.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=100.0,
            parent_version=v1
        )
        
        v3 = self.version_manager.register_version(
            checkpoint_path="/p3.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=100.0,
            parent_version=v2
        )
        
        # Get lineage via API
        response = self.client.get(f'/api/trm/versions/{v3}/lineage')
        self.assertEqual(response.status_code, 200)
        lineage_data = json.loads(response.data)
        
        self.assertEqual(lineage_data['lineage'], [v3, v2, v1])
    
    def test_training_history_logging(self):
        """Test: Log and retrieve training history for a version"""
        
        version_id = self.version_manager.register_version(
            checkpoint_path="/path.pt",
            training_config={"epochs": 5},
            performance_metrics={},
            dataset_stats={},
            training_duration=300.0
        )
        
        # Log training history
        for epoch in range(1, 6):
            self.version_manager.add_training_history_entry(
                version_id,
                epoch=epoch,
                train_loss=1.0 / epoch,
                val_loss=0.8 / epoch,
                val_accuracy=0.70 + epoch * 0.05
            )
        
        # Get history via API
        response = self.client.get(f'/api/trm/versions/{version_id}/history')
        self.assertEqual(response.status_code, 200)
        history_data = json.loads(response.data)
        
        self.assertEqual(history_data['total_epochs'], 5)
        self.assertEqual(len(history_data['epochs']), 5)
        self.assertEqual(history_data['epochs'][-1]['epoch'], 5)
    
    def test_version_export_report(self):
        """Test: Export comprehensive version report"""
        
        version_id = self.version_manager.register_version(
            checkpoint_path="/path.pt",
            training_config={"epochs": 3},
            performance_metrics={"best_val_accuracy": 0.92},
            dataset_stats={"train": 80, "val": 10, "test": 10},
            training_duration=180.0,
            description="Test version"
        )
        
        # Add history
        for epoch in range(1, 4):
            self.version_manager.add_training_history_entry(
                version_id,
                epoch=epoch,
                train_loss=0.5/epoch,
                val_loss=0.4/epoch
            )
        
        # Export via API
        response = self.client.get(f'/api/trm/versions/{version_id}/export')
        self.assertEqual(response.status_code, 200)
        report = json.loads(response.data)
        
        self.assertIn('version', report)
        self.assertIn('training_history', report)
        self.assertIn('lineage', report)
        self.assertIn('exported_at', report)
        self.assertEqual(len(report['training_history']), 3)
    
    def test_version_deletion(self):
        """Test: Delete version and verify removal"""
        
        version_id = self.version_manager.register_version(
            checkpoint_path="/path.pt",
            training_config={},
            performance_metrics={},
            dataset_stats={},
            training_duration=100.0
        )
        
        # Add history
        self.version_manager.add_training_history_entry(
            version_id, epoch=1, train_loss=0.5, val_loss=0.4
        )
        
        # Verify exists
        self.assertIsNotNone(self.version_manager.get_version(version_id))
        
        # Delete via manager
        success = self.version_manager.delete_version(version_id)
        self.assertTrue(success)
        
        # Verify deleted
        self.assertIsNone(self.version_manager.get_version(version_id))
        self.assertEqual(len(self.version_manager.get_training_history(version_id)), 0)
    
    def test_list_versions_endpoint(self):
        """Test: List versions with pagination"""
        
        # Create 5 versions
        for i in range(5):
            self.version_manager.register_version(
                checkpoint_path=f"/p{i}.pt",
                training_config={"epochs": 10 * (i + 1)},
                performance_metrics={"best_val_accuracy": 0.80 + i * 0.03},
                dataset_stats={},
                training_duration=100.0 * (i + 1),
                description=f"Version {i+1}"
            )
        
        # List all
        response = self.client.get('/api/trm/versions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(len(data['versions']), 5)
        self.assertEqual(data['total_count'], 5)
        
        # List with limit
        response = self.client.get('/api/trm/versions?limit=3')
        data = json.loads(response.data)
        self.assertEqual(len(data['versions']), 3)


if __name__ == '__main__':
    unittest.main()
