"""
Phase 5: Enhanced TRM API with Model Management Endpoints

Extends the basic TRM API with:
- Model versioning and version history
- Training history tracking
- Model comparison utilities
- Version rollback and management
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import logging
import json
from datetime import datetime

from backend.trm_model_manager import ModelVersionManager, ModelVersion

logger = logging.getLogger(__name__)

# Create blueprint for model management endpoints
model_mgmt_bp = Blueprint('model_management', __name__, url_prefix='/api/trm/versions')


class ModelManagementAPI:
    """API for model versioning and management"""
    
    def __init__(self, version_manager: ModelVersionManager):
        """
        Initialize model management API
        
        Args:
            version_manager: ModelVersionManager instance
        """
        self.version_manager = version_manager
        logger.info("ModelManagementAPI initialized")
    
    def get_all_versions(self):
        """
        GET /api/trm/versions
        Get list of all model versions
        
        Query params:
            limit: Max results (default 10)
        
        Response:
        {
            "versions": [list of version summaries],
            "total_count": int
        }
        """
        try:
            limit = request.args.get('limit', 10, type=int)
            versions = self.version_manager.list_versions(limit=limit)
            
            return jsonify({
                "versions": versions,
                "total_count": len(versions)
            }), 200
        
        except Exception as e:
            logger.error(f"Error fetching versions: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def get_version_detail(self, version_id: str):
        """
        GET /api/trm/versions/<version_id>
        Get detailed information about a specific version
        
        Response:
        {
            "version": {version metadata},
            "training_history": [epoch records],
            "lineage": [ancestor version IDs]
        }
        """
        try:
            version = self.version_manager.get_version(version_id)
            if not version:
                return jsonify({"error": f"Version {version_id} not found"}), 404
            
            history = self.version_manager.get_training_history(version_id)
            lineage = self.version_manager.get_version_lineage(version_id)
            
            return jsonify({
                "version": version,
                "training_history": history,
                "lineage": lineage
            }), 200
        
        except Exception as e:
            logger.error(f"Error fetching version detail: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def get_best_version(self):
        """
        GET /api/trm/versions/best
        Get the best performing version
        
        Response:
        {
            "version": {best version metadata}
        }
        """
        try:
            best = self.version_manager.get_best_version()
            if not best:
                return jsonify({"error": "No versions available"}), 404
            
            return jsonify({"version": best}), 200
        
        except Exception as e:
            logger.error(f"Error fetching best version: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def mark_best_version(self, version_id: str):
        """
        POST /api/trm/versions/<version_id>/mark-best
        Mark a version as the best performing
        
        Response:
        {
            "success": bool,
            "version_id": str
        }
        """
        try:
            success = self.version_manager.mark_best_version(version_id)
            
            if success:
                return jsonify({
                    "success": True,
                    "version_id": version_id
                }), 200
            else:
                return jsonify({"error": f"Version {version_id} not found"}), 404
        
        except Exception as e:
            logger.error(f"Error marking best version: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def compare_versions(self):
        """
        POST /api/trm/versions/compare
        Compare multiple versions
        
        Request body:
        {
            "version_ids": [list of version IDs to compare]
        }
        
        Response:
        {
            "versions": [version summaries],
            "metric_differences": {metrics that differ},
            "config_differences": {configs that differ}
        }
        """
        try:
            data = request.get_json() or {}
            version_ids = data.get('version_ids', [])
            
            if not version_ids or len(version_ids) < 2:
                return jsonify({"error": "At least 2 version IDs required"}), 400
            
            comparison = self.version_manager.compare_versions(version_ids)
            
            return jsonify(comparison), 200
        
        except Exception as e:
            logger.error(f"Error comparing versions: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def get_training_history(self, version_id: str):
        """
        GET /api/trm/versions/<version_id>/history
        Get training history (epoch-by-epoch logs) for a version
        
        Response:
        {
            "version_id": str,
            "epochs": [
                {"epoch": int, "train_loss": float, "val_loss": float, ...}
            ]
        }
        """
        try:
            history = self.version_manager.get_training_history(version_id)
            
            return jsonify({
                "version_id": version_id,
                "epochs": history,
                "total_epochs": len(history)
            }), 200
        
        except Exception as e:
            logger.error(f"Error fetching training history: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def get_version_lineage(self, version_id: str):
        """
        GET /api/trm/versions/<version_id>/lineage
        Get the lineage (ancestry) of a version
        
        Response:
        {
            "version_id": str,
            "lineage": [list of ancestor version IDs from newest to oldest]
        }
        """
        try:
            lineage = self.version_manager.get_version_lineage(version_id)
            
            return jsonify({
                "version_id": version_id,
                "lineage": lineage
            }), 200
        
        except Exception as e:
            logger.error(f"Error fetching lineage: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def export_version_report(self, version_id: str):
        """
        GET /api/trm/versions/<version_id>/export
        Export comprehensive report for a version
        
        Response:
        {
            "version": {metadata},
            "training_history": [epochs],
            "lineage": [ancestors],
            "exported_at": ISO timestamp
        }
        """
        try:
            report = self.version_manager.export_version_report(version_id)
            
            if not report:
                return jsonify({"error": f"Version {version_id} not found"}), 404
            
            return jsonify(report), 200
        
        except Exception as e:
            logger.error(f"Error exporting report: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    def delete_version(self, version_id: str):
        """
        DELETE /api/trm/versions/<version_id>
        Delete a version and its checkpoint
        
        Response:
        {
            "success": bool,
            "version_id": str
        }
        """
        try:
            success = self.version_manager.delete_version(version_id)
            
            if success:
                return jsonify({
                    "success": True,
                    "version_id": version_id
                }), 200
            else:
                return jsonify({"error": f"Version {version_id} not found"}), 404
        
        except Exception as e:
            logger.error(f"Error deleting version: {str(e)}")
            return jsonify({"error": str(e)}), 500


def register_model_management_endpoints(app, version_manager: ModelVersionManager):
    """Register model management API endpoints with Flask app"""
    
    api = ModelManagementAPI(version_manager)
    
    @model_mgmt_bp.route('', methods=['GET'])
    def list_versions():
        return api.get_all_versions()
    
    @model_mgmt_bp.route('/best', methods=['GET'])
    def get_best():
        return api.get_best_version()
    
    @model_mgmt_bp.route('/compare', methods=['POST'])
    def compare():
        return api.compare_versions()
    
    @model_mgmt_bp.route('/<version_id>', methods=['GET'])
    def get_detail(version_id):
        return api.get_version_detail(version_id)
    
    @model_mgmt_bp.route('/<version_id>/mark-best', methods=['POST'])
    def mark_best(version_id):
        return api.mark_best_version(version_id)
    
    @model_mgmt_bp.route('/<version_id>/history', methods=['GET'])
    def history(version_id):
        return api.get_training_history(version_id)
    
    @model_mgmt_bp.route('/<version_id>/lineage', methods=['GET'])
    def lineage(version_id):
        return api.get_version_lineage(version_id)
    
    @model_mgmt_bp.route('/<version_id>/export', methods=['GET'])
    def export(version_id):
        return api.export_version_report(version_id)
    
    @model_mgmt_bp.route('/<version_id>', methods=['DELETE'])
    def delete(version_id):
        return api.delete_version(version_id)
    
    app.register_blueprint(model_mgmt_bp)
    logger.info("Model management endpoints registered")
