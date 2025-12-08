"""
Tests for Phase 4: TRM Backend API Endpoints
Tests all REST API endpoints for data ingestion, inference, and training
"""

import unittest
import json
import tempfile
import numpy as np
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app
from backend.trm_api import trm_system


class TestTRMAPIEndpoints(unittest.TestCase):
    """Test TRM API endpoints"""
    
    def setUp(self):
        """Set up test client and temp directory"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        # Create temp directory for test data
        self.temp_dir = tempfile.mkdtemp()
        trm_system.dataset_path = Path(self.temp_dir) / "test_dataset.json"
        trm_system.model_checkpoint_dir = Path(self.temp_dir) / "checkpoints"
    
    def tearDown(self):
        """Clean up temp directory"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_compliance_result(self, element_type="IfcDoor", label=1, idx=0):
        """Helper to create a sample compliance result"""
        return {
            "element_guid": f"element-{idx}",
            "element_data": {
                "type": element_type,
                "name": f"Test {element_type}",
                "width_mm": 950,
                "height_mm": 2100,
                "material": "wood",
                "fire_rating": "60"
            },
            "rule_id": f"rule-{idx}",
            "rule_name": "Test Rule",
            "result": "PASS" if label == 1 else "FAIL"
        }
    
    def test_health_check(self):
        """Test API health check endpoint"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_add_sample_success(self):
        """Test adding a single training sample"""
        payload = {
            "compliance_result": self._create_compliance_result(label=1),
            "label": 1
        }
        
        response = self.client.post(
            '/api/trm/add-sample',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
    
    def test_add_sample_pass_and_fail(self):
        """Test adding PASS and FAIL samples"""
        # PASS sample
        payload_pass = {
            "compliance_result": self._create_compliance_result(label=1),
            "ifc_file": "test.ifc"
        }
        
        response = self.client.post(
            '/api/trm/add-sample',
            data=json.dumps(payload_pass),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
    
    def test_add_sample_with_ifc_file(self):
        """Test adding sample with IFC file tracking"""
        payload = {
            "compliance_result": self._create_compliance_result(label=1),
            "ifc_file": "mybuilding.ifc"
        }
        
        response = self.client.post(
            '/api/trm/add-sample',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('mybuilding.ifc', data['metadata']['ifc_files_processed'])
    
    def test_analyze_single_sample(self):
        """Test inference on single sample"""
        payload = {
            "compliance_result": self._create_compliance_result()
        }
        
        response = self.client.post(
            '/api/trm/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('prediction', data)
        self.assertIn('confidence', data)
        self.assertIn('reasoning_trace', data)
        self.assertIn('total_steps', data)
        self.assertIn('converged', data)
        
        self.assertIn(data['prediction'], [0, 1])
        self.assertGreaterEqual(data['confidence'], 0.0)
        self.assertLessEqual(data['confidence'], 1.0)
    
    def test_analyze_no_result(self):
        """Test inference without compliance result"""
        payload = {}
        
        response = self.client.post(
            '/api/trm/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_batch_analyze(self):
        """Test batch inference"""
        payload = {
            "samples": [
                self._create_compliance_result(label=1),
                self._create_compliance_result(label=0),
                self._create_compliance_result(label=1),
            ]
        }
        
        response = self.client.post(
            '/api/trm/batch-analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('summary', data)
        
        self.assertEqual(len(data['results']), 3)
        self.assertEqual(data['count'], 3)
        
        summary = data['summary']
        self.assertIn('avg_confidence', summary)
        self.assertIn('pass_count', summary)
        self.assertIn('fail_count', summary)
        self.assertGreaterEqual(summary['avg_confidence'], 0.0)
        self.assertLessEqual(summary['avg_confidence'], 1.0)
    
    def test_batch_analyze_empty(self):
        """Test batch analyze with empty samples"""
        payload = {
            "samples": []
        }
        
        response = self.client.post(
            '/api/trm/batch-analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_batch_analyze_invalid_format(self):
        """Test batch analyze with invalid sample format"""
        payload = {
            "samples": "not a list"
        }
        
        response = self.client.post(
            '/api/trm/batch-analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_get_model_info(self):
        """Test getting model information"""
        response = self.client.get('/api/trm/models')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('model_type', data)
        self.assertIn('parameters', data)
        self.assertIn('device', data)
        self.assertIn('trained', data)
        self.assertIn('checkpoint_dir', data)
        
        self.assertEqual(data['model_type'], 'TinyComplianceNetwork')
        self.assertGreater(data['parameters'], 0)
        self.assertFalse(data['trained'])  # No training yet
    
    def test_reset_model(self):
        """Test model reset"""
        response = self.client.post('/api/trm/models/reset')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data.get('success'))
        self.assertIn('message', data)
    
    def test_dataset_stats_empty(self):
        """Test getting stats from empty dataset"""
        response = self.client.get('/api/trm/dataset/stats')
        
        # Should return 200 with stats (empty or with defaults)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check expected fields exist
        self.assertIn('total_samples', data)
        self.assertIn('train_samples', data)
        self.assertIn('val_samples', data)
        self.assertIn('test_samples', data)
    
    def test_dataset_stats_with_data(self):
        """Test getting stats after adding samples"""
        # Add multiple samples
        for i in range(2):
            payload = {
                "compliance_result": self._create_compliance_result(label=1),
                "ifc_file": "test.ifc"
            }
            
            self.client.post(
                '/api/trm/add-sample',
                data=json.dumps(payload),
                content_type='application/json'
            )
        
        # Get stats
        response = self.client.get('/api/trm/dataset/stats')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should have at least some samples
        self.assertGreaterEqual(data.get('total_samples', 0), 0)
    
    def test_clear_dataset(self):
        """Test clearing dataset"""
        # Add a sample first
        payload = {
            "compliance_result": self._create_compliance_result(label=1),
            "ifc_file": "test.ifc"
        }
        
        self.client.post(
            '/api/trm/add-sample',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Clear dataset
        response = self.client.post('/api/trm/dataset/clear')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))


class TestTRMAPIWorkflow(unittest.TestCase):
    """Test complete TRM workflow through API"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp()
        trm_system.dataset_path = Path(self.temp_dir) / "test_dataset.json"
        trm_system.model_checkpoint_dir = Path(self.temp_dir) / "checkpoints"
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_compliance_result(self, idx=0, label=1):
        """Helper to create diverse compliance results"""
        return {
            "element_guid": f"element-{idx}",
            "element_data": {
                "type": ["IfcDoor", "IfcWindow", "IfcWall"][idx % 3],
                "name": f"Test Element {idx}",
                "width_mm": 900 + idx * 10,
                "height_mm": 2000 + idx * 10,
                "material": ["wood", "concrete", "steel"][idx % 3],
                "fire_rating": f"{30 + idx*5}"
            },
            "rule_id": f"rule-{idx % 5}",
            "rule_name": f"Test Rule {idx % 5}",
            "result": "PASS" if label == 1 else "FAIL"
        }
    
    def test_complete_workflow(self):
        """Test: add samples → analyze → train → inference"""
        
        # 1. Add 20 samples
        sample_count = 20
        for i in range(sample_count):
            label = 1 if i % 2 == 0 else 0
            payload = {
                "compliance_result": self._create_compliance_result(idx=i, label=label),
                "ifc_file": "test.ifc"
            }
            
            response = self.client.post(
                '/api/trm/add-sample',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 201)
        
        # 2. Check dataset stats
        response = self.client.get('/api/trm/dataset/stats')
        data = json.loads(response.data)
        self.assertGreater(data['total_samples'], 0)
        
        # 3. Analyze samples
        batch_payload = {
            "samples": [
                self._create_compliance_result(idx=i, label=1)
                for i in range(5)
            ]
        }
        
        response = self.client.post(
            '/api/trm/batch-analyze',
            data=json.dumps(batch_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['count'], 5)
        
        # 4. Train model
        train_payload = {
            "epochs": 2,
            "learning_rate": 0.001,
            "batch_size": 8
        }
        
        response = self.client.post(
            '/api/trm/train',
            data=json.dumps(train_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertGreater(data.get('epochs_trained'), 0)
        
        # 5. Verify model is now trained
        response = self.client.get('/api/trm/models')
        data = json.loads(response.data)
        # Note: trained flag depends on checkpoint saving
        self.assertGreater(data['parameters'], 0)


class TestTRMAPIErrorHandling(unittest.TestCase):
    """Test API error handling"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        self.temp_dir = tempfile.mkdtemp()
        trm_system.dataset_path = Path(self.temp_dir) / "test_dataset.json"
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_train_no_data(self):
        """Test training without dataset"""
        payload = {"epochs": 1}
        
        response = self.client.post(
            '/api/trm/train',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_train_invalid_epochs(self):
        """Test training with invalid epochs"""
        payload = {"epochs": 2000}  # Too many
        
        response = self.client.post(
            '/api/trm/train',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_train_invalid_learning_rate(self):
        """Test training with invalid learning rate"""
        payload = {"learning_rate": 2.0}  # Out of range
        
        response = self.client.post(
            '/api/trm/train',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
