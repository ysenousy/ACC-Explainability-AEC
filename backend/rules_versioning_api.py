"""
Rules Versioning API Endpoints

Provides REST API for managing rule versions:
- Load specific version
- Create new version from modifications
- Rollback to previous version
- List all versions
- Compare versions
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
from pathlib import Path

rules_versioning_bp = Blueprint("rules_versioning", __name__, url_prefix="/api/rules/versions")


@rules_versioning_bp.route("/current", methods=["GET"])
def get_current_version():
    """Get current active rule version."""
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        current_id = version_manager.get_current_version_id()
        version_info = version_manager.get_version_info(current_id)
        
        rules, mappings = version_manager.load_rules(current_id)
        
        return jsonify({
            "status": "success",
            "current_version": current_id,
            "version_info": version_info,
            "num_rules": len(rules.get("rules", [])),
            "num_mappings": len(mappings.get("rule_mappings", []))
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/list", methods=["GET"])
def list_versions():
    """List all available rule versions."""
    try:
        version_manager = current_app.config.get("rules_version_manager")
        versions = version_manager.list_all_versions()
        
        return jsonify({
            "status": "success",
            "total_versions": len(versions),
            "current_version": version_manager.get_current_version_id(),
            "versions": versions
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/<int:version_id>", methods=["GET"])
def get_version(version_id):
    """Get specific version details and rules."""
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        version_info = version_manager.get_version_info(version_id)
        if not version_info:
            return jsonify({"status": "error", "message": f"Version {version_id} not found"}), 404
        
        rules, mappings = version_manager.load_rules(version_id)
        
        return jsonify({
            "status": "success",
            "version_id": version_id,
            "version_info": version_info,
            "rules": rules,
            "mappings": mappings
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/save", methods=["POST"])
def save_new_version():
    """
    Create a new version from modified rules.
    
    Request body:
    {
        "rules": {...},                    # Updated rules object
        "mappings": {...},                 # Updated mappings object
        "description": "What changed",     # Description of modifications
        "modifications": [...]             # List of modification records (optional)
    }
    """
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        data = request.get_json()
        
        # Validate required fields
        if not data or "rules" not in data or "mappings" not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: rules, mappings"
            }), 400
        
        if "description" not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: description"
            }), 400
        
        # Create new version
        new_version_id = version_manager.create_new_version(
            rules_dict=data["rules"],
            mappings_dict=data["mappings"],
            description=data["description"],
            modifications=data.get("modifications"),
            created_by=data.get("created_by", "user")
        )
        
        new_version_info = version_manager.get_version_info(new_version_id)
        
        return jsonify({
            "status": "success",
            "message": f"New version {new_version_id} created successfully",
            "new_version_id": new_version_id,
            "version_info": new_version_info
        }), 201
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/rollback/<int:version_id>", methods=["POST"])
def rollback_version(version_id):
    """
    Rollback to a previous version.
    
    Args:
        version_id: Version to rollback to
    """
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        # Check if version exists
        if version_manager.get_version_info(version_id) is None:
            return jsonify({
                "status": "error",
                "message": f"Version {version_id} not found"
            }), 404
        
        # Perform rollback
        rules, mappings = version_manager.rollback_to(version_id)
        
        return jsonify({
            "status": "success",
            "message": f"Successfully rolled back to version {version_id}",
            "version_id": version_id,
            "num_rules": len(rules.get("rules", [])),
            "num_mappings": len(mappings.get("rule_mappings", []))
        }), 200
    
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/compare/<int:version_id_1>/<int:version_id_2>", methods=["GET"])
def compare_versions(version_id_1, version_id_2):
    """
    Compare two versions and show differences.
    
    Args:
        version_id_1: First version
        version_id_2: Second version
    """
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        # Verify both versions exist
        if not version_manager.get_version_info(version_id_1):
            return jsonify({"status": "error", "message": f"Version {version_id_1} not found"}), 404
        
        if not version_manager.get_version_info(version_id_2):
            return jsonify({"status": "error", "message": f"Version {version_id_2} not found"}), 404
        
        diff = version_manager.get_version_diff(version_id_1, version_id_2)
        
        return jsonify({
            "status": "success",
            "comparison": diff
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/original", methods=["GET"])
def get_original_version():
    """Get the original (v0) rule version."""
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        version_info = version_manager.get_version_info(0)
        rules, mappings = version_manager.load_rules(0)
        
        return jsonify({
            "status": "success",
            "version_id": 0,
            "version_info": version_info,
            "rules": rules,
            "mappings": mappings,
            "message": "Original rules (v0) - baseline configuration"
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_versioning_bp.route("/export/<int:version_id>", methods=["POST"])
def export_version(version_id):
    """
    Export a version to backup (prepare JSON export).
    
    Args:
        version_id: Version to export
    """
    try:
        version_manager = current_app.config.get("rules_version_manager")
        
        if not version_manager.get_version_info(version_id):
            return jsonify({"status": "error", "message": f"Version {version_id} not found"}), 404
        
        rules, mappings = version_manager.load_rules(version_id)
        version_info = version_manager.get_version_info(version_id)
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "version_id": version_id,
            "version_info": version_info,
            "rules": rules,
            "mappings": mappings
        }
        
        return jsonify({
            "status": "success",
            "message": f"Version {version_id} exported successfully",
            "export_data": export_data
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
