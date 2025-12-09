"""
Rules Catalogue Sync API Endpoints

Handles synchronization between catalogue and mappings.
When catalogue is updated, mappings are automatically regenerated.
"""

from flask import Blueprint, request, jsonify, current_app
from backend.rules_mapping_sync import RulesMappingSynchronizer

rules_sync_bp = Blueprint("rules_sync", __name__, url_prefix="/api/rules/sync")


@rules_sync_bp.route("/status", methods=["GET"])
def get_sync_status():
    """Get current sync status between catalogue and mappings."""
    try:
        sync_dir = current_app.config.get("rules_config_dir")
        synchronizer = RulesMappingSynchronizer(sync_dir)
        
        status = synchronizer.get_sync_status()
        
        return jsonify({
            "status": "success",
            "sync_status": status
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_sync_bp.route("/synchronize", methods=["POST"])
def synchronize():
    """
    Synchronize mappings with current catalogue.
    
    Removes mappings for rules that have been deleted from catalogue.
    Keeps mappings for all rules currently in catalogue.
    """
    try:
        sync_dir = current_app.config.get("rules_config_dir")
        synchronizer = RulesMappingSynchronizer(sync_dir)
        
        # Perform sync
        result = synchronizer.sync_mappings(verbose=True)
        
        return jsonify({
            "status": "success",
            "message": "Mappings synchronized with catalogue",
            "result": result
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_sync_bp.route("/validate", methods=["GET"])
def validate():
    """
    Validate that mappings match catalogue.
    
    Returns validation result without making changes.
    """
    try:
        sync_dir = current_app.config.get("rules_config_dir")
        synchronizer = RulesMappingSynchronizer(sync_dir)
        
        is_valid = synchronizer.validate_sync()
        status_info = synchronizer.get_sync_status()
        
        return jsonify({
            "status": "success",
            "is_valid": is_valid,
            "validation": status_info
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_sync_bp.route("/on-catalogue-update", methods=["POST"])
def on_catalogue_update():
    """
    Called when catalogue is updated (add/remove/modify rules).
    
    Automatically synchronizes mappings with the updated catalogue,
    and syncs the reasoning engine with the latest rules.
    """
    try:
        sync_dir = current_app.config.get("rules_config_dir")
        synchronizer = RulesMappingSynchronizer(sync_dir)
        
        # Get the update details from request
        data = request.get_json() or {}
        action = data.get("action", "update")  # add, remove, modify, batch
        rule_id = data.get("rule_id", "unknown")
        
        # Sync mappings
        result = synchronizer.sync_mappings(verbose=True)
        
        # Sync reasoning engine with latest rules
        # Get the reasoning engine from app context
        reasoning_engine = current_app.config.get("reasoning_engine")
        reasoning_synced = False
        if reasoning_engine:
            try:
                sync_result = reasoning_engine.load_rules_from_version_manager()
                reasoning_synced = sync_result.get('success', False)
            except Exception as e:
                current_app.logger.error(f"Error syncing reasoning engine: {e}")
        
        return jsonify({
            "status": "success",
            "message": f"Catalogue updated ({action} rule: {rule_id}). Mappings and reasoning engine synchronized.",
            "sync_result": result,
            "reasoning_engine_synced": reasoning_synced
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@rules_sync_bp.route("/detailed-status", methods=["GET"])
def detailed_status():
    """Get detailed sync status with complete rule lists."""
    try:
        sync_dir = current_app.config.get("rules_config_dir")
        synchronizer = RulesMappingSynchronizer(sync_dir)
        
        status = synchronizer.get_sync_status()
        
        return jsonify({
            "status": "success",
            "sync_status": status,
            "timestamp": None
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
