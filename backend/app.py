"""Flask API backend for IFC Explorer web application."""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider
from pathlib import Path
import json
import logging
import tempfile
from typing import Dict, Any, List

from data_layer.services import DataLayerService
from data_layer.load_ifc import preview_ifc
from rule_layer.run_rules import run_with_graph
from backend.analyze_rules import analyze_ifc_rules
from backend.data_validator import validate_ifc
from backend.unified_compliance_engine import check_rule_compliance, UnifiedComplianceEngine
from backend.compliance_report_generator import generate_compliance_report, ComplianceReportGenerator
from backend.rule_config_manager import (
    load_custom_rules,
    save_custom_rules,
    add_rule,
    delete_rule,
    get_all_rules,
    import_rules,
    export_rules,
)
from reasoning_layer.reasoning_engine import ReasoningEngine
from backend.trm_api import register_trm_endpoints
from backend.trm_model_manager import ModelVersionManager
from backend.trm_model_management_api import register_model_management_endpoints
from backend.rules_version_manager import RulesVersionManager
from backend.rules_versioning_api import rules_versioning_bp
from backend.rules_mapping_sync import RulesMappingSynchronizer
from backend.rules_sync_api import rules_sync_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Custom JSON provider to handle UTF-8 properly
class UTF8JSONProvider(DefaultJSONProvider):
    """Custom JSON provider that preserves Unicode characters."""
    def dumps(self, obj, **kwargs):
        kwargs.setdefault('ensure_ascii', False)
        kwargs.setdefault('indent', 2)
        return super().dumps(obj, **kwargs)
    
    def dump(self, obj, fp, **kwargs):
        kwargs.setdefault('ensure_ascii', False)
        kwargs.setdefault('indent', 2)
        return super().dump(obj, fp, **kwargs)

app.json = UTF8JSONProvider(app)

# Ensure UTF-8 encoding for all JSON responses
@app.after_request
def set_utf8_encoding(response):
    """Ensure all responses have proper UTF-8 encoding."""
    if response.content_type and 'application/json' in response.content_type:
        response.content_type = 'application/json; charset=utf-8'
    return response

# Services
data_svc = DataLayerService()

# Initialize Rules Version Manager
rules_config_path = Path(__file__).parent.parent / "rules_config"
rules_version_manager = RulesVersionManager(str(rules_config_path))
app.config["rules_version_manager"] = rules_version_manager
app.config["rules_config_dir"] = str(rules_config_path)

# Initialize Rules Mapping Synchronizer
rules_sync = RulesMappingSynchronizer(str(rules_config_path))
app.config["rules_mapping_synchronizer"] = rules_sync

# Initialize reasoning engine WITHOUT loading rules at startup
# Rules will be loaded on-demand when user imports/selects them
reasoning_engine = ReasoningEngine(
    rules_file=None,  # Not loaded at startup
    custom_rules_file=None  # Not loaded at startup
)

# Store reasoning engine in app config so other blueprints can access it
app.config["reasoning_engine"] = reasoning_engine

# Track if rules have been imported in this session
rules_imported_in_session = False

# In-memory session state for rule edits (delete/add/modify)
# This maintains state across multiple operations until user saves
session_state = {
    'in_memory_rules': None,  # Current in-memory rules (None = use latest version)
    'is_editing': False,      # Whether user is currently editing
}

def get_session_rules():
    """Get current rules from session (in-memory) or latest version."""
    if session_state['in_memory_rules'] is not None:
        logger.debug(f"[SESSION] Returning in-memory rules: {len(session_state['in_memory_rules'])} rules")
        return session_state['in_memory_rules']
    # Load from latest version
    logger.debug(f"[SESSION] Loading from RulesVersionManager (in_memory_rules is None)")
    rules_dict, _ = rules_version_manager.load_rules()
    rules = rules_dict.get('rules', [])
    logger.debug(f"[SESSION] Loaded {len(rules)} rules from version manager")
    return rules

def set_session_rules(rules):
    """Update in-memory session rules."""
    session_state['in_memory_rules'] = rules
    session_state['is_editing'] = True

def clear_session_rules():
    """Clear in-memory session rules (after save)."""
    session_state['in_memory_rules'] = None
    session_state['is_editing'] = False


def sync_reasoning_engine_with_latest_rules():
    """Sync reasoning engine with latest rules from RulesVersionManager.
    
    This ensures the reasoning layer always has the latest version of rules.
    """
    try:
        result = reasoning_engine.load_rules_from_version_manager()
        if result.get('success'):
            logger.info(f"✓ Reasoning engine synced: {result.get('rules_loaded')} rules from v{result.get('version')}")
            return True
        else:
            logger.warning(f"Failed to sync reasoning engine: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Error syncing reasoning engine: {e}")
        return False


# ===== Health & Info Endpoints =====

@app.route("/", methods=["GET"])
def health_check():
    """Health check and API information endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "ACC-Explainability-AEC API",
        "version": "1.0",
        "message": "Backend API is running",
        "endpoints": "/api/info"
    })


@app.route("/api/info", methods=["GET"])
def api_info():
    """List all available API endpoints."""
    routes_info = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes_info.append({
                "endpoint": rule.rule,
                "methods": list(rule.methods - {'HEAD', 'OPTIONS'}),
                "function": rule.endpoint
            })
    
    routes_info.sort(key=lambda x: x['endpoint'])
    
    return jsonify({
        "status": "operational",
        "total_endpoints": len(routes_info),
        "endpoints": routes_info,
        "reasoning_engine": {
            "regulatory_rules": len(reasoning_engine.regulatory_rules),
            "custom_rules": len(reasoning_engine.custom_rules),
            "total_rules": len(reasoning_engine.rules)
        }
    })


# ===== IFC Loading Endpoints =====

@app.route("/api/ifc/preview", methods=["POST"])
def preview_ifc_endpoint():
    """Load and preview an IFC file.
    
    Request (form-data):
        file: File object
        include_rules: bool (optional)
    
    Or (JSON legacy):
        {
            "ifc_path": str
        }
    
    Response:
        {
            "success": bool,
            "preview": dict,
            "summary": dict,
            "error": str or null
        }
    """
    try:
        import os
        if 'file' not in request.files:
            data = request.get_json()
            ifc_path = data.get("ifc_path") if data else None
            if not ifc_path:
                return jsonify({"success": False, "error": "file or ifc_path required"}), 400
            model = data_svc.load_model(ifc_path)
        else:
            file = request.files['file']
            with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            try:
                model = data_svc.load_model(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        preview = preview_ifc(model)
        summary = {
            'num_spaces': preview.get('counts', {}).get('spaces', 0),
            'num_doors': preview.get('counts', {}).get('doors', 0),
            'num_windows': preview.get('counts', {}).get('windows', 0),
            'num_walls': preview.get('counts', {}).get('walls', 0),
            'num_slabs': preview.get('counts', {}).get('slabs', 0),
            'num_storeys': preview.get('counts', {}).get('storeys', 0),
            'ifc_space': preview.get('counts', {}).get('IfcSpace', 0),
            'ifc_door': preview.get('counts', {}).get('IfcDoor', 0),
            'ifc_window': preview.get('counts', {}).get('IfcWindow', 0),
            'ifc_wall': preview.get('counts', {}).get('IfcWall', 0),
            'ifc_building': preview.get('counts', {}).get('IfcBuilding', 0),
            'ifc_building_storey': preview.get('counts', {}).get('IfcBuildingStorey', 0),
        }
        
        return jsonify({
            "success": True,
            "preview": preview,
            "summary": summary,
            "error": None,
        })
    except Exception as e:
        logger.exception("Preview failed")
        return jsonify({
            "success": False,
            "preview": None,
            "summary": None,
            "error": str(e),
        }), 500


@app.route("/api/ifc/graph", methods=["POST"])
def build_graph_endpoint():
    """Build canonical data-layer graph from IFC.
    
    Request:
        {
            "ifc_path": str,
            "include_rules": bool (optional, default false)
        }
    
    Response:
        {
            "success": bool,
            "graph": dict,
            "summary": dict,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        ifc_path = data.get("ifc_path")
        include_rules = data.get("include_rules", False)
        
        if not ifc_path:
            return jsonify({"success": False, "error": "ifc_path required"}), 400
        
        logger.info("Building graph: %s (include_rules=%s)", ifc_path, include_rules)
        model = data_svc.load_model(ifc_path)
        preview = preview_ifc(model)
        graph = data_svc.build_graph(ifc_path, include_rules=include_rules)
        
        # Get summary
        elements = graph.get("elements", {}) or {}
        spaces = elements.get("spaces", []) or []
        doors = elements.get("doors", []) or []
        
        summary = {
            "num_spaces": len(spaces),
            "num_doors": len(doors),
            "num_windows": preview.get('counts', {}).get('windows', 0),
            "num_walls": preview.get('counts', {}).get('walls', 0),
            "num_slabs": preview.get('counts', {}).get('slabs', 0),
            "num_storeys": preview.get('counts', {}).get('storeys', 0),
            "ifc_space": preview.get('counts', {}).get('IfcSpace', 0),
            "ifc_door": preview.get('counts', {}).get('IfcDoor', 0),
            "ifc_window": preview.get('counts', {}).get('IfcWindow', 0),
            "ifc_wall": preview.get('counts', {}).get('IfcWall', 0),
            "ifc_building": preview.get('counts', {}).get('IfcBuilding', 0),
            "ifc_building_storey": preview.get('counts', {}).get('IfcBuildingStorey', 0),
        }
        
        return jsonify({
            "success": True,
            "preview": preview,
            "graph": graph,
            "summary": summary,
            "error": None,
        })
    except Exception as e:
        logger.exception("Graph building failed")
        return jsonify({
            "success": False,
            "graph": None,
            "summary": None,
            "error": str(e),
        }), 500


@app.route("/api/ifc/upload", methods=["POST"])
def upload_ifc_endpoint():
    """Upload an IFC file (multipart/form-data) and return preview + graph.

    Form fields:
      - file: uploaded IFC binary (required)
      - include_rules: optional, 'true'/'false' (defaults to 'true')

    Response mirrors combined preview + graph endpoint:
      { success, preview, graph, summary, error }
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "file field required"}), 400

        uploaded = request.files['file']
        if uploaded.filename == '':
            return jsonify({"success": False, "error": "empty filename"}), 400

        include_rules_raw = request.form.get('include_rules', 'true')
        include_rules = str(include_rules_raw).lower() in ("1", "true", "yes")

        # DO NOT clear the rules catalogue here - it persists across IFC uploads
        # The rules are session-level, not file-specific
        # save_custom_rules([]) was removed to preserve user-imported rules

        # Save to a temporary file and process
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as tmp:
            tmp_path = tmp.name
            uploaded.save(tmp_path)

        try:
            logger.info("Processing uploaded IFC file %s (include_rules=%s)", uploaded.filename, include_rules)

            # Build graph (this will load the model internally)
            graph = data_svc.build_graph(tmp_path, include_rules=include_rules)

            # Also produce preview by loading the model (preview_ifc expects a model)
            model = data_svc.load_model(tmp_path)
            preview = preview_ifc(model)

            elements = graph.get("elements", {}) or {}
            spaces = elements.get("spaces", []) or []
            doors = elements.get("doors", []) or []

            summary = {
                "num_spaces": len(spaces),
                "num_doors": len(doors),
                "num_windows": preview.get('counts', {}).get('windows', 0),
                "num_walls": preview.get('counts', {}).get('walls', 0),
                "num_slabs": preview.get('counts', {}).get('slabs', 0),
                "num_storeys": preview.get('counts', {}).get('storeys', 0),
                "ifc_space": preview.get('counts', {}).get('IfcSpace', 0),
                "ifc_door": preview.get('counts', {}).get('IfcDoor', 0),
                "ifc_window": preview.get('counts', {}).get('IfcWindow', 0),
                "ifc_wall": preview.get('counts', {}).get('IfcWall', 0),
                "ifc_building": preview.get('counts', {}).get('IfcBuilding', 0),
                "ifc_building_storey": preview.get('counts', {}).get('IfcBuildingStorey', 0),
            }

            return jsonify({
                "success": True,
                "preview": preview,
                "graph": graph,
                "summary": summary,
                "error": None,
            })
        finally:
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

    except Exception as e:
        logger.exception("Uploaded preview failed")
        return jsonify({
            "success": False,
            "preview": None,
            "graph": None,
            "summary": None,
            "error": str(e),
        }), 500


# ===== Element Endpoints =====

@app.route("/api/elements/spaces", methods=["POST"])
def get_spaces_endpoint():
    """Get all spaces from a graph.
    
    Request:
        {
            "graph": dict
        }
    
    Response:
        {
            "success": bool,
            "spaces": list,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        graph = data.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        spaces = graph.get("elements", {}).get("spaces", []) or []
        
        return jsonify({
            "success": True,
            "spaces": spaces,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get spaces")
        return jsonify({
            "success": False,
            "spaces": None,
            "error": str(e),
        }), 500


@app.route("/api/elements/doors", methods=["POST"])
def get_doors_endpoint():
    """Get all doors from a graph.
    
    Request:
        {
            "graph": dict
        }
    
    Response:
        {
            "success": bool,
            "doors": list,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        graph = data.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        doors = graph.get("elements", {}).get("doors", []) or []
        
        return jsonify({
            "success": True,
            "doors": doors,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get doors")
        return jsonify({
            "success": False,
            "doors": None,
            "error": str(e),
        }), 500


# ===== Rule Evaluation Endpoints =====

@app.route("/api/rules/evaluate", methods=["POST"])
def evaluate_rules_endpoint():
    """Evaluate regulatory compliance rules against a graph.
    
    Uses the unified compliance engine with the latest version of regulatory rules from RulesVersionManager.
    
    Request:
        {
            "graph": dict,
            "include_manifest": bool (optional, ignored - kept for API compatibility),
            "include_builtin": bool (optional, ignored - kept for API compatibility)
        }
    
    Response:
        {
            "success": bool,
            "results": list,
            "summary": dict,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        graph = data.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        logger.info("Evaluating regulatory compliance rules")
        
        # Load latest rules from RulesVersionManager
        rules_config_dir = Path(__file__).parent.parent / 'rules_config'
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_data, _ = version_manager.load_rules()
        rules_list = rules_data.get('rules', [])
        
        logger.info(f"Using {len(rules_list)} regulatory compliance rules from RulesVersionManager (latest version)")
        
        # Initialize unified compliance engine and set rules
        engine = UnifiedComplianceEngine()
        engine.rules = rules_list
        
        # Run compliance check
        results = engine.check_graph(graph)
        
        # Transform results to match expected format
        check_results = results.get('results', [])
        
        # Compute summary
        summary = {
            "total": results.get('total_checks', 0),
            "passed": results.get('passed', 0),
            "failed": results.get('failed', 0),
            "unable": results.get('unable', 0),
            "pass_rate": results.get('pass_rate', 0),
            "by_severity": {},
            "by_rule": {},
        }
        
        # Group by severity and rule
        for result in check_results:
            severity = result.get("severity", "UNKNOWN")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            rule_id = result.get("rule_id", "UNKNOWN")
            summary["by_rule"][rule_id] = summary["by_rule"].get(rule_id, 0) + 1
        
        logger.info(f"Evaluation complete: {len(check_results)} checks performed")
        
        return jsonify({
            "success": True,
            "results": check_results,
            "summary": summary,
            "error": None,
        })
                
    except Exception as e:
        logger.exception("Rule evaluation failed")
        return jsonify({
            "success": False,
            "results": None,
            "summary": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/manifest", methods=["POST"])
def get_manifest_endpoint():
    """Get rules manifest from a graph.
    
    Request:
        {
            "graph": dict
        }
    
    Response:
        {
            "success": bool,
            "manifest": dict or null,
            "num_rules": int,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        graph = data.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        manifest = graph.get("meta", {}).get("rules_manifest")
        num_rules = len(manifest.get("rules", [])) if manifest else 0
        
        return jsonify({
            "success": True,
            "manifest": manifest,
            "num_rules": num_rules,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get manifest")
        return jsonify({
            "success": False,
            "manifest": None,
            "num_rules": 0,
            "error": str(e),
        }), 500


@app.route("/api/rules/catalogue", methods=["GET"])
def get_rules_catalogue():
    """Get all available rules with full metadata.
    
    Loads from enhanced-regulation-rules.json (current version).
    
    Response:
        {
            "success": bool,
            "rules": [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "parameters": dict,
                    "severity": str,
                    "code_reference": str
                },
                ...
            ],
            "error": str or null
        }
    """
    try:
        # Load rules from current version (enhanced-regulation-rules.json)
        # This ensures we always show the user's current catalogue
        from backend.rules_version_manager import RulesVersionManager
        
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        
        # Load current version's rules
        rules_dict, _ = version_manager.load_rules()
        rules = rules_dict.get('rules', [])
        
        return jsonify({
            "success": True,
            "rules": rules,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get rules catalogue")
        return jsonify({
            "success": False,
            "rules": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/configure", methods=["POST"])
def configure_rules():
    """Update rule configuration (thresholds, severity levels).
    
    Request:
        {
            "door": {
                "min_width_mm": float,
                "severity": str,
                "code_reference": str
            },
            "space": {
                "min_area_m2": float,
                "severity": str,
                "code_reference": str
            },
            "building": {
                "max_occupancy_per_storey": int,
                "severity": str,
                "code_reference": str
            }
        }
    
    Response:
        {
            "success": bool,
            "config": dict,
            "ruleset_id": str,
            "error": str or null
        }
    """
    try:
        from rule_layer import RuleConfig, get_ruleset_metadata
        
        data = request.get_json()
        
        # Create new config from request data
        config = RuleConfig.from_mapping(data)
        
        # Get updated metadata
        metadata = get_ruleset_metadata(config)
        
        return jsonify({
            "success": True,
            "config": config.to_dict(),
            "ruleset_id": metadata.get("ruleset_id"),
            "rules": metadata.get("rules"),
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to configure rules")
        return jsonify({
            "success": False,
            "config": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/get-all", methods=["GET"])
def get_all_rules_endpoint():
    """Get baseline + custom rules combined.
    
    Response:
        {
            "success": bool,
            "baseline": list,
            "custom": list,
            "total": int,
            "error": str or null
        }
    """
    try:
        all_rules = get_all_rules()
        return jsonify({
            "success": True,
            "baseline": all_rules.get("baseline", []),
            "custom": all_rules.get("custom", []),
            "total": all_rules.get("total", 0),
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get all rules")
        return jsonify({
            "success": False,
            "baseline": None,
            "custom": None,
            "total": 0,
            "error": str(e),
        }), 500


@app.route("/api/rules/add", methods=["POST"])
def add_rule_endpoint():
    """Add a rule to the current ruleset.
    
    Request:
        {
            "rule": {
                "id": str,
                "name": str,
                "description": str,
                "target_type": str,
                "selector": dict,
                "condition": dict,
                "parameters": dict,
                "severity": str,
                "code_reference": str
            }
        }
    Response:
        {
            "success": bool,
            "custom_rules": list,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        rule = data.get("rule")
        if not rule or not rule.get("id"):
            return jsonify({"success": False, "error": "rule with id required"}), 400
        
        logger.info("Adding rule: %s", rule.get("id"))
        
        # Load current version rules and mappings
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_dict, mappings_dict = version_manager.load_rules()
        rules_list = rules_dict.get('rules', [])
        
        # Check if rule already exists
        for existing_rule in rules_list:
            if existing_rule.get('id') == rule.get('id'):
                return jsonify({
                    "success": False,
                    "custom_rules": None,
                    "error": "Rule with this ID already exists",
                }), 400
        
        # Add new rule
        rules_list.append(rule)
        rules_dict['rules'] = rules_list
        
        # Create new version
        new_version = version_manager.create_new_version(
            rules_dict,
            mappings_dict,
            f"Added rule: {rule.get('id')}"
        )
        logger.info(f"Rule {rule.get('id')} added. New version: {new_version}")
        
        return jsonify({
            "success": True,
            "custom_rules": rules_list,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to add rule")
        return jsonify({
            "success": False,
            "custom_rules": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/delete/<rule_id>", methods=["DELETE"])
def delete_rule_endpoint(rule_id):
    """Delete a rule from the in-memory session (does NOT persist to file yet).
    
    This removes the rule from the working set in memory.
    Changes are NOT saved to disk until user confirms via /api/rules/save-session.
    Original file remains unchanged until explicit save.
    
    Response:
        {
            "success": bool,
            "rules": list (remaining rules in session),
            "changes_count": int (total unsaved changes),
            "error": str or null
        }
    """
    try:
        logger.info(f"[DELETE] Attempting to delete rule: '{rule_id}'")
        
        # Get current session rules (either in-memory or latest version)
        current_rules = get_session_rules()
        rules_list = list(current_rules) if current_rules else []
        
        # If this is the first edit operation, initialize the session with current rules
        if session_state['in_memory_rules'] is None and rules_list:
            logger.info(f"[DELETE] First edit operation - initializing session state with {len(rules_list)} rules")
            set_session_rules(rules_list)
        
        logger.info(f"[DELETE] Current rules count: {len(rules_list)}")
        logger.info(f"[DELETE] Available rule IDs: {[r.get('id') for r in rules_list[:3]]}...")
        
        # Filter out the rule to delete (in memory only, not persisted yet)
        original_count = len(rules_list)
        updated_rules = [r for r in rules_list if r.get('id') != rule_id]
        
        logger.info(f"[DELETE] After filter - count: {len(updated_rules)}, original: {original_count}")
        
        if len(updated_rules) < original_count:
            # Rule was found and deleted from in-memory session
            logger.info(f"[DELETE] Rule '{rule_id}' deleted from session (NOT YET SAVED). Remaining: {len(updated_rules)} rules")
            
            # Update session state to maintain in-memory changes
            set_session_rules(updated_rules)
            
            # Don't sync mappings yet - only sync on final save
            # This prevents partial updates if user cancels editing
            # Return the updated rules, but note this is not persisted yet
            return jsonify({
                "success": True,
                "rules": updated_rules,
                "changes_count": original_count - len(updated_rules),
                "message": "Rule deleted from session. Click 'Save Changes' to persist.",
                "error": None,
            })
        else:
            logger.warning(f"[DELETE] Rule not found: '{rule_id}'. Available IDs: {[r.get('id') for r in rules_list]}")
            return jsonify({
                "success": False,
                "rules": None,
                "error": f"Rule not found: {rule_id}",
            }), 404
    except Exception as e:
        logger.exception("Failed to delete rule from session")
        return jsonify({
            "success": False,
            "rules": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/save-session", methods=["POST"])
def save_session_endpoint():
    """Save in-memory changes as a new version.
    
    This endpoint takes the current in-memory rules (after deletions/additions)
    and saves them as a new permanent version. Original source files are never modified.
    
    Request:
        {
            "rules": list (current in-memory rules),
            "description": str (optional, auto-generated if not provided)
        }
    
    Response:
        {
            "success": bool,
            "version_id": str (new version created),
            "rules_count": int,
            "message": str,
            "error": str or null
        }
    """
    try:
        data = request.get_json() or {}
        rules_list = data.get('rules', [])
        user_description = data.get('description', '')
        
        if not rules_list:
            return jsonify({
                "success": False,
                "error": "No rules provided to save"
            }), 400
        
        # Prepare rules for saving
        import copy
        saved_rules = copy.deepcopy(rules_list)
        
        # Load current version for mappings reference
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        _, mappings_dict = version_manager.load_rules()
        
        # Create description
        if user_description:
            description = user_description
        else:
            description = f"Session changes: Saved {len(saved_rules)} rules"
        
        # Create new version with in-memory changes
        rules_dict = {'rules': saved_rules}
        new_version = version_manager.create_new_version(
            rules_dict,
            mappings_dict,
            description
        )
        
        logger.info(f"[SAVE-SESSION] Saved in-memory changes as {new_version} with {len(saved_rules)} rules")
        
        # Automatically sync mappings
        try:
            synchronizer = RulesMappingSynchronizer(str(rules_config_dir))
            sync_result = synchronizer.sync_mappings(verbose=True)
            logger.info(f"[SAVE-SESSION] Mappings synced: {sync_result}")
        except Exception as sync_err:
            logger.error(f"[SAVE-SESSION] Error syncing mappings: {sync_err}")
        
        # Sync reasoning engine
        try:
            reasoning_result = reasoning_engine.load_rules_from_version_manager()
            logger.info(f"[SAVE-SESSION] Reasoning engine synced")
        except Exception as engine_err:
            logger.error(f"[SAVE-SESSION] Error syncing reasoning engine: {engine_err}")
        
        # Clear in-memory session state after successful save
        clear_session_rules()
        logger.info(f"[SAVE-SESSION] Session state cleared, ready for new edits")
        
        return jsonify({
            "success": True,
            "version_id": new_version,
            "rules_count": len(saved_rules),
            "message": f"Changes saved as {new_version}. Original files unchanged.",
            "error": None
        }), 201
    
    except Exception as e:
        logger.exception("Failed to save session")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/rules/save-all", methods=["POST"])
def save_all_rules_endpoint():
    """Save all rules at once to current version.
    
    Request:
        {
            "rules": list of rule objects
        }
    Response:
        {
            "success": bool,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        rules = data.get("rules", [])
        
        logger.info("Saving %d rules", len(rules))
        
        # Load current version, update rules, create new version
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_dict, mappings_dict = version_manager.load_rules()
        
        rules_dict['rules'] = rules
        new_version = version_manager.create_new_version(
            rules_dict,
            mappings_dict,
            f"Saved {len(rules)} rules"
        )
        logger.info(f"Rules saved. New version: {new_version}")
        
        return jsonify({
            "success": True,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to save rules")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route("/api/rules/custom", methods=["GET"])
def get_custom_rules_endpoint():
    """Get all current rules (from session or current version).
    
    Response:
        {
            "success": bool,
            "custom_rules": list,
            "is_editing": bool (whether in-memory edits exist),
            "error": str or null
        }
    """
    try:
        # Get rules from session (in-memory) or latest version
        rules = get_session_rules()
        
        return jsonify({
            "success": True,
            "custom_rules": rules,
            "is_editing": session_state['is_editing'],
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get custom rules")
        return jsonify({
            "success": False,
            "custom_rules": None,
            "is_editing": False,
            "error": str(e),
        }), 500


@app.route("/api/rules/import", methods=["POST"])
def import_rules_endpoint():
    """Import rules from JSON file to current version.
    
    Request (form-data):
        file: JSON file with rules array
        merge: bool (optional, default true) - merge with existing or replace
    
    Response:
        {
            "success": bool,
            "status": {
                "total_imported": int,
                "added": int,
                "skipped": int,
                "errors": list
            },
            "error": str or null
        }
    """
    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "status": None,
                "error": "No file provided"
            }), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({
                "success": False,
                "status": None,
                "error": "No file selected"
            }), 400
        
        # Read and parse JSON
        try:
            file_content = file.read().decode("utf-8")
            rules_data = json.loads(file_content)
        except json.JSONDecodeError as e:
            return jsonify({
                "success": False,
                "status": None,
                "error": f"Invalid JSON format: {str(e)}"
            }), 400
        
        # Extract rules list
        if isinstance(rules_data, dict) and "rules" in rules_data:
            rules_to_import = rules_data.get("rules", [])
        elif isinstance(rules_data, list):
            rules_to_import = rules_data
        else:
            return jsonify({
                "success": False,
                "status": None,
                "error": "JSON must contain 'rules' array or be an array directly"
            }), 400
        
        # Get merge flag from form data
        merge = request.form.get("merge", "true").lower() == "true"
        
        # Load current version
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_dict, mappings_dict = version_manager.load_rules()
        existing_rules = rules_dict.get('rules', [])
        
        # Process import
        status = {
            'total_imported': len(rules_to_import),
            'added': 0,
            'skipped': 0,
            'errors': []
        }
        
        if merge:
            # Merge mode: add new rules, skip duplicates
            existing_ids = {r.get('id') for r in existing_rules}
            final_rules = existing_rules.copy()
            
            for rule in rules_to_import:
                if rule.get('id') not in existing_ids:
                    final_rules.append(rule)
                    status['added'] += 1
                else:
                    status['skipped'] += 1
        else:
            # Replace mode: clear and import
            final_rules = rules_to_import
            status['added'] = len(rules_to_import)
        
        # Create new version with imported rules
        rules_dict['rules'] = final_rules
        new_version = version_manager.create_new_version(
            rules_dict,
            mappings_dict,
            f"Imported {status['added']} rules (merge={merge})"
        )
        logger.info(f"[IMPORT] Imported {status['added']} rules, skipped {status['skipped']}. New version: {new_version}")
        
        # Immediately load the imported rules into reasoning_engine
        if status.get('added', 0) > 0:
            try:
                backend_dir = Path(__file__).parent
                project_root = backend_dir.parent
                # Load from current version's enhanced-regulation-rules.json
                enhanced_rules_path = str(project_root / "rules_config" / "versions" / new_version / "enhanced-regulation-rules.json")
                logger.info(f"[IMPORT] Loading rules into reasoning engine from: {enhanced_rules_path}")
                
                result = reasoning_engine.load_rules_from_file(enhanced_rules_path, rule_type='custom')
                if result.get('success'):
                    logger.info(f"[IMPORT] ✓ Successfully loaded {result['rules_loaded']} rules into reasoning engine")
                else:
                    logger.warning(f"[IMPORT] Failed to load rules into reasoning engine: {result.get('error')}")
            except Exception as load_err:
                logger.error(f"[IMPORT] Error loading rules into reasoning engine: {load_err}")
        
        # Mark that rules have been imported in this session
        global rules_imported_in_session
        if status.get("total_imported", 0) > 0:
            rules_imported_in_session = True
            logger.info(f"[IMPORT] ✓ rules_imported_in_session = True")
        
        return jsonify({
            "success": True,
            "status": status,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to import rules")
        return jsonify({
            "success": False,
            "status": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/export", methods=["GET"])
def export_rules_endpoint():
    """Export custom rules as JSON file.
    
    Response:
        {
            "success": bool,
            "data": {
                "rules": list,
                "count": int,
                "exported_at": str
            },
            "error": str or null
        }
    """
    try:
        result = export_rules()
        return jsonify({
            "success": True,
            "data": result,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to export rules")
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e),
        }), 500


# ===== IFC Rule Analysis Endpoint =====

@app.route("/api/ifc/analyze-rules", methods=["POST"])
def analyze_ifc_rules_endpoint():
    """Analyze loaded IFC for element types, extracted rules, and rule coverage.
    
    Request:
        {
            "ifc_path": str
        }
    Response:
        {
            "success": bool,
            "analysis": dict,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        ifc_path = data.get("ifc_path")
        if not ifc_path:
            return jsonify({"success": False, "error": "ifc_path required"}), 400
        logger.info("Analyzing IFC for rules: %s", ifc_path)
        model = data_svc.load_model(ifc_path)
        analysis = analyze_ifc_rules(model)
        return jsonify({
            "success": True,
            "analysis": analysis,
            "error": None,
        })
    except Exception as e:
        logger.exception("IFC rule analysis failed")
        return jsonify({
            "success": False,
            "analysis": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/analyze-strategies", methods=["POST"])
def analyze_extraction_strategies():
    """Analyze the graph and return what each extraction strategy would generate.
    
    Request:
        {
            "graph": dict (the data-layer graph)
        }
    
    Response:
        {
            "success": bool,
            "strategies": {
                "pset": {
                    "available": bool,
                    "count": int,
                    "description": str,
                    "sample_rules": list
                },
                "statistical": {
                    "available": bool,
                    "count": int,
                    "description": str,
                    "sample_rules": list
                },
                "metadata": {
                    "available": bool,
                    "count": int,
                    "description": str,
                    "sample_rules": list
                }
            }
        }
    """
    try:
        from data_layer.extract_rules import extract_rules_from_graph
        
        data = request.get_json()
        graph = data.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        strategies_info = {}
        
        # Analyze each strategy
        for strategy_name in ["pset", "statistical", "metadata"]:
            try:
                # Extract rules for this specific strategy
                result = extract_rules_from_graph(graph, strategies=[strategy_name])
                rules = result.get("rules", [])
                
                # Count rules generated by this strategy
                strategy_prefix_map = {
                    "pset": "IFC_PARAM_",
                    "statistical": "STAT_",
                    "metadata": "METADATA_"
                }
                prefix = strategy_prefix_map.get(strategy_name, "")
                strategy_rules = [r for r in rules if r.get("id", "").startswith(prefix)]
                
                # Get sample rules (first 2)
                sample_rules = []
                for rule in strategy_rules[:2]:
                    sample_rules.append({
                        "id": rule.get("id"),
                        "name": rule.get("name"),
                        "target_type": rule.get("target_type")
                    })
                
                descriptions = {
                    "pset": "Extract rules from IFC property sets and element attributes",
                    "statistical": "Generate 10th percentile baselines from element measurements",
                    "metadata": "Detect missing or incomplete data in IFC elements"
                }
                
                # Always show metadata strategy even if count is 0 (to inform about missing data status)
                # For pset and statistical, only show if they generate rules
                if strategy_name == "metadata":
                    is_available = True
                else:
                    is_available = len(strategy_rules) > 0
                
                strategies_info[strategy_name] = {
                    "available": is_available,
                    "count": len(strategy_rules),
                    "description": descriptions.get(strategy_name, ""),
                    "sample_rules": sample_rules
                }
            except Exception as e:
                logger.warning(f"Strategy {strategy_name} analysis failed: {e}")
                strategies_info[strategy_name] = {
                    "available": False,
                    "count": 0,
                    "description": "",
                    "sample_rules": [],
                    "error": str(e)
                }
        
        return jsonify({
            "success": True,
            "strategies": strategies_info
        })
    
    except Exception as e:
        logger.exception("Strategy analysis failed")
        return jsonify({
            "success": False,
            "strategies": None,
            "error": str(e)
        }), 500


@app.route("/api/rules/check-against-ifc", methods=["POST"])
def check_rules_against_ifc():
    """Check selected rules against an IFC file.
    
    Request:
        {
            "graph": dict (the data-layer graph),
            "rules": list (rules to check),
            "mode": str ("regulatory" or "generated")
        }
    
    Response:
        {
            "success": bool,
            "results": {
                "mode": str,
                "pass_count": int,
                "fail_count": int,
                "details": [
                    {
                        "rule": dict,
                        "result": "PASS" or "FAIL",
                        "message": str,
                        "details": dict or null
                    },
                    ...
                ]
            },
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        graph = data.get("graph")
        rules = data.get("rules", [])
        mode = data.get("mode", "regulatory")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        if not rules:
            return jsonify({"success": False, "error": "rules required"}), 400
        
        # Use unified compliance engine to evaluate rules
        engine = UnifiedComplianceEngine()
        
        results_details = []
        pass_count = 0
        fail_count = 0
        
        # Check each rule against the graph
        for rule in rules:
            try:
                # Generic evaluation that supports both formats
                rule_result = engine.check_rule_against_graph(graph, rule)
                
                result_status = "PASS" if rule_result.get("passed", False) else "FAIL"
                if result_status == "PASS":
                    pass_count += 1
                else:
                    fail_count += 1
                
                results_details.append({
                    "rule": {
                        "id": rule.get("id"),
                        "name": rule.get("name"),
                        "severity": rule.get("severity"),
                        "target_type": rule.get("target_type")
                    },
                    "result": result_status,
                    "message": rule_result.get("message", ""),
                    "details": rule_result.get("details", None)
                })
            except Exception as e:
                logger.warning(f"Error checking rule {rule.get('id')}: {e}")
                results_details.append({
                    "rule": {
                        "id": rule.get("id"),
                        "name": rule.get("name"),
                        "severity": rule.get("severity")
                    },
                    "result": "ERROR",
                    "message": f"Error evaluating rule: {str(e)}",
                    "details": None
                })
        
        return jsonify({
            "success": True,
            "results": {
                "mode": mode,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "total_checked": len(rules),
                "details": results_details
            },
            "error": None
        })
    
    except Exception as e:
        logger.exception("Rule checking failed")
        return jsonify({
            "success": False,
            "results": None,
            "error": str(e)
        }), 500


# ===== Import and Update Rules =====

@app.route("/api/rules/import-catalogue", methods=["POST"])
def import_catalogue():
    """Import rules from JSON file as a new version.
    
    Creates a deep copy of imported rules into a new version.
    This ensures the original imported file is never modified.
    
    Supports two modes:
    - replace: Clear existing rules and import new ones (fresh import)
    - append: Add new rules to existing ones (merge)
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({"success": False, "error": "File must be JSON"}), 400
        
        mode = request.form.get('mode', 'replace')  # Default to replace for clean imports
        
        data = json.load(file)
        
        if 'rules' not in data or not isinstance(data.get('rules'), list):
            return jsonify({"success": False, "error": "Invalid JSON format: must contain 'rules' array"}), 400
        
        # Make a DEEP COPY of the imported rules (independent of original file)
        import copy
        new_rules = copy.deepcopy(data.get('rules', []))
        
        # Load current version rules and mappings
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_dict, mappings_dict = version_manager.load_rules()
        existing_rules = rules_dict.get('rules', [])
        
        if mode == 'replace':
            # Fresh import: replace all existing rules with a clean copy
            final_rules = copy.deepcopy(new_rules)
            added_count = len(new_rules)
            skipped_count = 0
            description = f"Imported from '{file.filename}' ({added_count} rules)"
        else:
            # Append mode: merge with existing
            # Get existing rule IDs to avoid duplicates
            existing_ids = {rule.get('id') for rule in existing_rules}
            
            # Add new rules, skip duplicates (use deep copies)
            added_count = 0
            skipped_count = 0
            final_rules = copy.deepcopy(existing_rules)
            
            for rule in new_rules:
                if rule.get('id') not in existing_ids:
                    final_rules.append(copy.deepcopy(rule))
                    added_count += 1
                else:
                    skipped_count += 1
            
            description = f"Appended {added_count} rules from '{file.filename}', skipped {skipped_count} duplicates"
        
        # Create new version with imported rules (as independent copy)
        rules_dict['rules'] = final_rules
        new_version = version_manager.create_new_version(
            rules_dict,
            mappings_dict,
            description
        )
        logger.info(f"[IMPORT-CATALOGUE] Imported {added_count} rules in '{mode}' mode, skipped {skipped_count}. New version: {new_version}")
        
        # Automatically sync mappings with the imported rules
        if added_count > 0:
            try:
                synchronizer = RulesMappingSynchronizer(str(rules_config_dir))
                sync_result = synchronizer.sync_mappings(verbose=True)
                logger.info(f"[IMPORT-CATALOGUE] ✓ Mappings synced after import: {sync_result}")
            except Exception as sync_err:
                logger.error(f"[IMPORT-CATALOGUE] Error syncing mappings after import: {sync_err}")
        
        # Immediately load the imported rules into reasoning_engine
        if added_count > 0:
            try:
                backend_dir = Path(__file__).parent
                project_root = backend_dir.parent
                # Load from current version's enhanced-regulation-rules.json
                enhanced_rules_path = str(project_root / "rules_config" / "versions" / new_version / "enhanced-regulation-rules.json")
                logger.info(f"[IMPORT-CATALOGUE] Loading rules into reasoning engine from: {enhanced_rules_path}")
                
                result = reasoning_engine.load_rules_from_file(enhanced_rules_path, rule_type='custom')
                if result.get('success'):
                    logger.info(f"[IMPORT-CATALOGUE] ✓ Successfully loaded {result['rules_loaded']} rules into reasoning engine")
                else:
                    logger.warning(f"[IMPORT-CATALOGUE] Failed to load rules into reasoning engine: {result.get('error')}")
            except Exception as load_err:
                logger.error(f"[IMPORT-CATALOGUE] Error loading rules into reasoning engine: {load_err}")
        
        # Mark that rules have been imported in this session
        global rules_imported_in_session
        if added_count > 0:
            rules_imported_in_session = True
            logger.info(f"[IMPORT-CATALOGUE] ✓ rules_imported_in_session = True")
        
        return jsonify({
            "success": True,
            "status": {"added": added_count, "skipped": skipped_count},
            "error": None
        })
    
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "Invalid JSON file"}), 400
    except Exception as e:
        logger.exception("Failed to import catalogue")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rules/update", methods=["PUT"])
def update_rule():
    """Update a specific rule from current version.
    
    Updates rule in enhanced-regulation-rules.json (current version).
    """
    try:
        data = request.get_json()
        rule_id = data.get('id')
        
        if not rule_id:
            return jsonify({"success": False, "error": "Rule ID required"}), 400
        
        # Load current version rules and mappings
        rules_config_dir = Path(__file__).parent.parent / "rules_config"
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_dict, mappings_dict = version_manager.load_rules()
        rules_list = rules_dict.get('rules', [])
        
        # Find and update rule
        rule_found = False
        for rule in rules_list:
            if rule.get('id') == rule_id:
                rule_found = True
                rule['name'] = data.get('name', rule.get('name'))
                rule['description'] = data.get('description', rule.get('description'))
                rule['severity'] = data.get('severity', rule.get('severity'))
                rule['code_reference'] = data.get('code_reference', rule.get('code_reference'))
                rule['enabled'] = data.get('enabled', rule.get('enabled', True))
                
                # Handle parameters - could be string or object
                if 'parameters' in data:
                    params = data.get('parameters', {})
                    if isinstance(params, str):
                        rule['parameters'] = json.loads(params)
                    else:
                        rule['parameters'] = params
                break
        
        if not rule_found:
            return jsonify({"success": False, "error": "Rule not found"}), 404
        
        # Create new version with updated rules
        rules_dict['rules'] = rules_list
        new_version = version_manager.create_new_version(
            rules_dict,
            mappings_dict,
            f"Updated rule: {rule_id}"
        )
        logger.info(f"Rule {rule_id} updated. New version: {new_version}")
        
        return jsonify({
            "success": True,
            "rules": rules_list,
            "error": None
        })
    
    except Exception as e:
        logger.exception("Failed to update rule")
        return jsonify({"success": False, "error": str(e)}), 500


# ===== Compliance Checking =====

@app.route("/api/compliance/check", methods=["POST"])
def check_compliance():
    """
    Check IFC graph against regulatory compliance rules.
    
    Request:
        {
            "graph": dict (IFC graph),
            "rules": list (optional, rule IDs to check - uses all if omitted),
            "target_classes": list (optional, IFC classes to check)
        }
    
    Response:
        {
            "success": bool,
            "timestamp": str,
            "total_checks": int,
            "passed": int,
            "failed": int,
            "unable": int,
            "pass_rate": float,
            "results": [
                {
                    "rule_id": str,
                    "rule_name": str,
                    "element_guid": str,
                    "element_type": str,
                    "passed": bool,
                    "severity": str,
                    "explanation": str,
                    "code_reference": str
                }
            ]
        }
    """
    try:
        data = request.get_json()
        graph = data.get('graph')
        rule_ids = data.get('rules', [])
        target_classes = data.get('target_classes', [])
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        # Log graph structure for debugging
        logger.info(f"Compliance check: Received graph with keys: {list(graph.keys())}")
        if 'elements' in graph:
            elements = graph.get('elements', {})
            logger.info(f"Compliance check: Graph has elements section with type: {type(elements).__name__}")
            if isinstance(elements, dict):
                elem_counts = {k: len(v) if isinstance(v, list) else 0 for k, v in elements.items()}
                logger.info(f"Compliance check: Elements by type: {elem_counts}")
                total_elems = sum(elem_counts.values())
                logger.info(f"Compliance check: TOTAL ELEMENTS IN GRAPH: {total_elems}")
            elif isinstance(elements, list):
                logger.info(f"Compliance check: Elements is list with {len(elements)} items")
        else:
            logger.info(f"Compliance check: Graph has NO elements section. Available keys: {list(graph.keys())}")
        
        # Load latest rules from RulesVersionManager
        rules_config_dir = Path(__file__).parent.parent / 'rules_config'
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_data, _ = version_manager.load_rules()
        all_rules = rules_data.get('rules', [])
        
        logger.info(f"Compliance check: Loaded {len(all_rules)} rules from RulesVersionManager (latest version)")
        
        # Filter rules if specified
        rules_to_check = all_rules
        if rule_ids:
            rules_to_check = [r for r in all_rules if r.get('id') in rule_ids]
        
        # Initialize unified compliance engine and set rules
        engine = UnifiedComplianceEngine()
        engine.rules = rules_to_check
        
        # Run compliance check
        results = engine.check_graph(graph, rules_to_check, target_classes if target_classes else None)
        
        logger.info(f"Compliance check: Found {len(results.get('results', []))} check results")
        if results.get('results'):
            rule_ids_in_results = set(r.get('rule_id') for r in results['results'] if r.get('rule_id'))
            logger.info(f"Compliance check: Rule IDs in results: {rule_ids_in_results}")
        
        response_data = {
            "success": True,
            **results,
            "error": None
        }
        logger.info(f"[check_compliance response] Total elements in response: {response_data.get('total_elements')}, Total checks: {response_data.get('total_checks')}, Response keys: {list(response_data.keys())}")
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.exception("Compliance check failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/compliance/summary-by-rule", methods=["POST"])
def compliance_summary_by_rule():
    """
    Get compliance summary grouped by rule.
    
    Request:
        {
            "check_results": dict (results from /api/compliance/check)
        }
    
    Response:
        {
            "success": bool,
            "summary": {
                "rule_id": {
                    "rule_name": str,
                    "passed": int,
                    "failed": int,
                    "unable": int,
                    "severity": str
                }
            }
        }
    """
    try:
        data = request.get_json()
        check_results = data.get('check_results')
        
        if not check_results:
            return jsonify({"success": False, "error": "check_results required"}), 400
        
        engine = UnifiedComplianceEngine()
        summary = engine.get_summary_by_rule(check_results)
        
        return jsonify({
            "success": True,
            "summary": summary
        })
    
    except Exception as e:
        logger.exception("Summary generation failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/compliance/failing-elements", methods=["POST"])
def get_failing_elements():
    """
    Get all elements that failed compliance checks.
    
    Request:
        {
            "check_results": dict (results from /api/compliance/check)
        }
    
    Response:
        {
            "success": bool,
            "failing_elements": [...]
        }
    """
    try:
        data = request.get_json()
        check_results = data.get('check_results')
        
        if not check_results:
            return jsonify({"success": False, "error": "check_results required"}), 400
        
        engine = UnifiedComplianceEngine()
        failing = engine.get_failing_elements(check_results)
        
        return jsonify({
            "success": True,
            "failing_count": len(failing),
            "failing_elements": failing
        })
    
    except Exception as e:
        logger.exception("Failing elements retrieval failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/compliance/get-failures", methods=["POST"])
def get_failures_for_reasoning():
    """
    Get list of failures from compliance check for reasoning layer analysis.
    
    Request:
        {
            "check_results": dict (results from /api/compliance/check)
        }
    
    Response:
        {
            "success": bool,
            "failures": [
                {
                    "element_id": str,
                    "element_type": str,
                    "element_name": str,
                    "failed_rules": [
                        {
                            "rule_id": str,
                            "rule_name": str,
                            "actual_value": any,
                            "required_value": any,
                            "unit": str,
                            "explanation": str
                        }
                    ]
                }
            ],
            "total_failures": int,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        check_results = data.get('check_results', {})
        
        if not check_results:
            return jsonify({"success": False, "error": "check_results required"}), 400
        
        results = check_results.get('results', [])
        
        # Group failures by element
        failures_by_element = {}
        
        for result in results:
            if result.get('passed') is False:  # Only failed checks
                element_id = result.get('element_guid', 'unknown')
                element_type = result.get('element_type', 'unknown')
                element_name = result.get('element_name', element_id)
                
                if element_id not in failures_by_element:
                    failures_by_element[element_id] = {
                        "element_id": element_id,
                        "element_type": element_type,
                        "element_name": element_name,
                        "failed_rules": []
                    }
                
                # Add failed rule
                failures_by_element[element_id]["failed_rules"].append({
                    "rule_id": result.get('rule_id', 'unknown'),
                    "rule_name": result.get('rule_name', 'Unknown Rule'),
                    "actual_value": result.get('actual_value'),
                    "required_value": result.get('required_value'),
                    "unit": result.get('unit', ''),
                    "explanation": result.get('explanation', ''),
                    "severity": result.get('severity', 'WARNING')
                })
        
        failures_list = list(failures_by_element.values())
        
        return jsonify({
            "success": True,
            "failures": failures_list,
            "total_failures": len(failures_list),
            "error": None
        })
    
    except Exception as e:
        logger.exception("Error getting failures for reasoning")
        return jsonify({
            "success": False,
            "failures": [],
            "total_failures": 0,
            "error": str(e)
        }), 500
    """
    Export compliance report as JSON file.
    
    Request:
        {
            "check_results": dict (results from /api/compliance/check)
        }
    
    Response:
        File download (compliance-report-TIMESTAMP.json)
    """
    try:
        from datetime import datetime
        import os
        
        data = request.get_json()
        check_results = data.get('check_results')
        
        if not check_results:
            return jsonify({"success": False, "error": "check_results required"}), 400
        
        # Create report file
        engine = UnifiedComplianceEngine()
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        report_file = f'/tmp/compliance-report-{timestamp}.json'
        
        if engine.export_report(check_results, report_file):
            return send_file(report_file, as_attachment=True, 
                           download_name=f'compliance-report-{timestamp}.json')
        else:
            return jsonify({"success": False, "error": "Failed to create report"}), 500
    
    except Exception as e:
        logger.exception("Report export failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reasoning/all-rules", methods=["GET"])
def get_all_regulatory_rules():
    """
    Get all rules (regulatory and custom) loaded in the ReasoningEngine.
    
    Response:
        {
            "success": bool,
            "rules": [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "severity": str,
                    "source": str ("regulatory" or "custom"),
                    "target_ifc_class": str,
                    "regulation": str,
                    "section": str,
                    "jurisdiction": str
                }
            ],
            "total_rules": int,
            "regulatory_rules": int,
            "custom_rules": int,
            "error": str or null
        }
    """
    try:
        # Get rules from ReasoningEngine (loads both regulatory and custom)
        all_rules = reasoning_engine.rules
        
        if not all_rules:
            return jsonify({
                "success": False,
                "error": "No rules loaded",
                "rules": [],
                "total_rules": 0
            }), 404
        
        # Transform rules to simplified format for display
        rules_list = []
        for rule_id, rule in all_rules.items():
            # Determine if rule is regulatory or custom
            rule_source = "custom" if rule_id in reasoning_engine.custom_rules else "regulatory"
            
            rules_list.append({
                "id": rule.get("id"),
                "name": rule.get("name"),
                "description": rule.get("description"),
                "severity": rule.get("severity", "WARNING"),
                "source": rule_source,
                "target_ifc_class": rule.get("target", {}).get("ifc_class") if isinstance(rule.get("target"), dict) else None,
                "regulation": rule.get("provenance", {}).get("regulation") if isinstance(rule.get("provenance"), dict) else None,
                "section": rule.get("provenance", {}).get("section") if isinstance(rule.get("provenance"), dict) else None,
                "jurisdiction": rule.get("provenance", {}).get("jurisdiction") if isinstance(rule.get("provenance"), dict) else None,
                "short_explanation": rule.get("explanation", {}).get("short", "") if isinstance(rule.get("explanation"), dict) else rule.get("explanation", "")
            })
        
        return jsonify({
            "success": True,
            "rules": rules_list,
            "total_rules": len(all_rules),
            "regulatory_rules": len(reasoning_engine.regulatory_rules),
            "custom_rules": len(reasoning_engine.custom_rules),
            "error": None
        })
    
    except Exception as e:
        logger.exception("Error getting all rules")
        return jsonify({
            "success": False,
            "rules": [],
            "total_rules": 0,
            "error": str(e)
        }), 500


@app.route("/api/reasoning/all-rules-with-status", methods=["POST"])
def get_all_rules_with_applicability():
    """
    Get all loaded rules with applicability status for current IFC.
    
    Request:
        {
            "graph": dict (IFC graph)
        }
    
    Response:
        {
            "success": bool,
            "rules": [
                {
                    "id": str,
                    "name": str,
                    "applicable": bool,
                    "reason": str (why or why not applicable),
                    "target_ifc_class": str,
                    "applicable_element_count": int,
                    "description": str,
                    "severity": str
                }
            ],
            "total_rules": int,
            "applicable_rules": int,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        graph = data.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        # Load all regulatory rules from RulesVersionManager
        rules_config_dir = Path(__file__).parent.parent / 'rules_config'
        version_manager = RulesVersionManager(str(rules_config_dir))
        rules_data, _ = version_manager.load_rules()
        all_rules = rules_data.get('rules', [])
        
        # Get element counts from graph
        elements = graph.get("elements", {})
        element_counts = {
            "IfcDoor": len(elements.get("doors", [])),
            "IfcSpace": len(elements.get("spaces", [])),
            "IfcWindow": len(elements.get("windows", [])),
            "IfcStairFlight": len(elements.get("stairs", [])),
            "IfcWall": len(elements.get("walls", [])),
            "IfcSlab": len(elements.get("slabs", [])),
            "IfcColumn": len(elements.get("columns", [])),
            "IfcBeam": len(elements.get("beams", []))
        }
        
        # Build rules with applicability status
        rules_with_status = []
        applicable_count = 0
        
        for rule in all_rules:
            target = rule.get("target", {})
            ifc_class = target.get("ifc_class", "")
            element_count = element_counts.get(ifc_class, 0)
            
            # Check if rule is applicable
            is_applicable = element_count > 0
            
            if is_applicable:
                applicable_count += 1
                reason = f"Applicable - {element_count} {ifc_class} element(s) in IFC"
            else:
                reason = f"Not applicable - No {ifc_class} elements in current IFC"
            
            rules_with_status.append({
                "id": rule.get("id", "unknown"),
                "name": rule.get("name", "Unknown Rule"),
                "applicable": is_applicable,
                "reason": reason,
                "target_ifc_class": ifc_class,
                "applicable_element_count": element_count,
                "description": rule.get("description", ""),
                "severity": rule.get("severity", "WARNING"),
                "regulation": rule.get("provenance", {}).get("regulation", ""),
                "section": rule.get("provenance", {}).get("section", "")
            })
        
        return jsonify({
            "success": True,
            "rules": rules_with_status,
            "total_rules": len(all_rules),
            "applicable_rules": applicable_count,
            "error": None
        })
    
    except Exception as e:
        logger.exception("Error getting rules with status")
        return jsonify({
            "success": False,
            "rules": [],
            "total_rules": 0,
            "applicable_rules": 0,
            "error": str(e)
        }), 500


# ===== Health Check =====

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.route("/api/reports/generate-compliance", methods=["POST"])
def generate_compliance_report_endpoint():
    """Generate comprehensive compliance report.
    
    Loads latest rules from RulesVersionManager to reflect any updates (deletions, modifications).
    """
    try:
        body = request.get_json()
        graph = body.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "No graph provided"}), 400
        
        # Load latest rules from RulesVersionManager
        rules_config_dir = Path(__file__).parent.parent / 'rules_config'
        version_manager = RulesVersionManager(str(rules_config_dir))
        
        try:
            rules_data, mappings_data = version_manager.load_rules()
            rules_list = rules_data.get('rules', [])
            
            if not rules_list:
                return jsonify({
                    "success": False,
                    "error": "No rules available in the current version."
                }), 400
            
            logger.info(f"[COMPLIANCE REPORT] Loaded {len(rules_list)} rules from RulesVersionManager (latest version)")
            
            # Pass rules to generator
            generator = ComplianceReportGenerator(rules=rules_list)
            report = generator.generate_report(graph)
            
            return jsonify({"success": True, "report": report}), 200
            
        except Exception as e:
            logger.error(f"Error loading rules from RulesVersionManager: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to load rules: {str(e)}"
            }), 500
    
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/export-compliance", methods=["POST"])
def export_compliance_report_endpoint():
    """Export compliance report as JSON file.
    
    Request:
        {
            "report": dict (the compliance report object),
            "graph_name": str (optional, for filename)
        }
    
    Response:
        File download (compliance-report-TIMESTAMP.json)
    """
    try:
        from datetime import datetime
        import os
        
        body = request.get_json()
        report = body.get("report")
        graph_name = body.get("graph_name", "compliance")
        
        if not report:
            return jsonify({"success": False, "error": "report required"}), 400
        
        # Create export data with metadata
        export_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "format_version": "1.0",
                "graph_name": graph_name
            },
            "report": report
        }
        
        # Create temporary file with report data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"compliance-report_{graph_name}_{timestamp}.json"
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(export_data, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name
        
        try:
            # Send file as download
            return send_file(
                tmp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )
        finally:
            # Clean up temp file after download
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error exporting compliance report: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rules/check-compliance", methods=["POST"])
def check_rules_compliance():
    """Check IFC rules compliance against regulatory rules.
    
    Uses latest rules from RulesVersionManager to reflect any updates (deletions, modifications).
    """
    try:
        body = request.get_json()
        graph = body.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "No graph provided"}), 400
        
        # Load latest rules from RulesVersionManager
        rules_config_dir = Path(__file__).parent.parent / 'rules_config'
        version_manager = RulesVersionManager(str(rules_config_dir))
        
        try:
            rules_data, _ = version_manager.load_rules()
            rules_list = rules_data.get('rules', [])
            
            if not rules_list:
                return jsonify({
                    "success": False, 
                    "error": "No rules available in the current version.",
                    "compliance": None
                }), 400
            
            logger.info(f"[COMPLIANCE CHECK] Loaded {len(rules_list)} rules from RulesVersionManager (latest version)")
            logger.info(f"[COMPLIANCE CHECK] Rule IDs: {[r.get('id', 'N/A') for r in rules_list[:5]]}")
        except Exception as e:
            logger.error(f"[COMPLIANCE CHECK] Error loading from RulesVersionManager: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to load rules: {str(e)}",
                "compliance": None
            }), 400
        
        # Create engine and set the fresh rules
        engine = UnifiedComplianceEngine()
        engine.rules = rules_list
        
        logger.info(f"[COMPLIANCE CHECK] Using {len(engine.rules)} rules for compliance check")
        
        # Check compliance using check_graph to get detailed failure results with regulatory fields
        check_result = engine.check_graph(graph, rules=rules_list)
        
        # Transform to format expected by RuleCheckView while keeping detailed results for Reasoning Layer
        # Get rules summary per rule
        rules_by_id = {}
        for result in check_result.get('results', []):
            rule_id = result.get('rule_id')
            if rule_id not in rules_by_id:
                rules_by_id[rule_id] = {
                    'rule_id': rule_id,
                    'rule_name': result.get('rule_name'),
                    'code_reference': result.get('code_reference'),
                    'severity': result.get('severity'),
                    'passed': 0,
                    'failed': 0,
                    'unable': 0,
                    'components_evaluated': 0
                }
            
            # Count results per rule
            if result.get('passed') is True:
                rules_by_id[rule_id]['passed'] += 1
            elif result.get('passed') is False:
                rules_by_id[rule_id]['failed'] += 1
            else:
                rules_by_id[rule_id]['unable'] += 1
            rules_by_id[rule_id]['components_evaluated'] += 1
        
        # Build summary
        summary = {
            'total_rules': len(rules_by_id),
            'components_checked': check_result.get('total_elements', 0),
            'total_evaluations': len(check_result.get('results', []))
        }
        
        # Return result with both summary (for RuleCheckView) and detailed results (for ReasoningView)
        result = {
            'summary': summary,
            'rules': list(rules_by_id.values()),
            'results': check_result.get('results', []),  # Detailed failures for Reasoning Layer
            'total_checks': check_result.get('total_checks', 0),
            'total_elements': check_result.get('total_elements', 0),
            'passed': check_result.get('passed', 0),
            'failed': check_result.get('failed', 0),
            'unable': check_result.get('unable', 0)
        }
        
        # Log summary
        logger.info(f"[COMPLIANCE CHECK] Results: {len(result.get('results', []))} total checks")
        logger.info(f"[COMPLIANCE CHECK] Passed: {result.get('passed', 0)}, Failed: {result.get('failed', 0)}, Unable: {result.get('unable', 0)}")
        logger.info(f"[COMPLIANCE CHECK] Total elements: {result.get('total_elements', 0)}")
        
        logger.info(f"[check_rules_compliance] Returning result with {len(result.get('results', []))} individual results and {len(result.get('rules', []))} rules")
        return jsonify({"success": True, "compliance": result}), 200
    
    except Exception as e:
        logger.error(f"Error checking rule compliance: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/validation/validate-ifc", methods=["POST"])
def validate_ifc_endpoint():
    """Validate IFC data completeness and quality."""
    try:
        body = request.get_json()
        graph = body.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "No graph provided"}), 400
        
        validation = validate_ifc(graph)
        
        return jsonify({
            "success": True,
            "validation": validation
        })
    except Exception as e:
        logger.error(f"Error validating IFC: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rules/check-status", methods=["GET"])
def check_rules_status():
    """Check if regulatory rules are loaded and available.
    
    Uses RulesVersionManager to check the current version of rules.
    
    Query parameters:
    - refresh=true: Force reload rules from disk
    """
    try:
        # Load latest rules from RulesVersionManager
        rules_config_dir = Path(__file__).parent.parent / 'rules_config'
        version_manager = RulesVersionManager(str(rules_config_dir))
        
        rules_data, _ = version_manager.load_rules()
        rules_list = rules_data.get('rules', [])
        
        rules_loaded = len(rules_list) > 0
        
        logger.info(f"[CHECK-STATUS] Rules loaded from RulesVersionManager: {rules_loaded} ({len(rules_list)} rules)")
        
        return jsonify({
            "success": True,
            "rules_loaded": rules_loaded,
            "rule_count": len(rules_list),
            "rules": [{"id": r.get("id"), "name": r.get("name")} for r in rules_list]
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking rules status: {e}")
        return jsonify({
            "success": False,
            "rules_loaded": False,
            "error": str(e)
        }), 500


# ===== Reasoning Layer Endpoints =====

@app.route("/api/reasoning/explain-rule", methods=["POST"])
def explain_rule():
    """
    Explain WHY a rule exists (regulatory intent, beneficiaries, safety concerns).
    
    Request:
        {
            "rule_id": str,
            "applicable_elements": list (optional),
            "elements_checked": int (optional),
            "elements_passing": int (optional),
            "elements_failing": int (optional)
        }
    
    Response:
        {
            "success": bool,
            "reasoning": {
                "reasoning_type": str,
                "rule_explanations": [
                    {
                        "rule_id": str,
                        "rule_name": str,
                        "justification": {
                            "regulatory_intent": str,
                            "target_beneficiary": str,
                            "safety_concern": str or null,
                            "accessibility_concern": str or null,
                            "explanation": str,
                            "primary_regulation": {...},
                            ...
                        },
                        ...
                    }
                ]
            }
        }
    """
    try:
        data = request.get_json()
        rule_id = data.get("rule_id")
        
        if not rule_id:
            return jsonify({"success": False, "error": "rule_id required"}), 400
        
        logger.info(f"Explaining rule: {rule_id}")
        logger.info(f"ReasoningEngine has {len(reasoning_engine.rules)} rules loaded")
        logger.info(f"Available rule IDs: {list(reasoning_engine.rules.keys())[:5]}...")
        
        result = reasoning_engine.explain_rule(
            rule_id,
            applicable_elements=data.get("applicable_elements"),
            elements_checked=data.get("elements_checked", 0),
            elements_passing=data.get("elements_passing", 0),
            elements_failing=data.get("elements_failing", 0)
        )
        
        if "error" in result:
            logger.warning(f"Rule explanation error: {result['error']}")
            return jsonify({"success": False, "error": result['error']}), 404
        else:
            logger.info(f"Successfully generated explanation for {rule_id}")
        
        return jsonify({"success": True, "reasoning": result}), 200
    
    except Exception as e:
        logger.error(f"Error explaining rule: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reasoning/analyze-failure", methods=["POST"])
def analyze_failure():
    """
    Explain WHY an element failed and HOW to fix it.
    
    Request:
        {
            "element_id": str,
            "element_type": str,
            "element_name": str (optional),
            "failed_rules": [
                {
                    "rule_id": str,
                    "rule_name": str,
                    "actual_value": any,
                    "required_value": any,
                    "unit": str (optional),
                    "location": str (optional)
                }
            ]
        }
    
    Response:
        {
            "success": bool,
            "reasoning": {
                "reasoning_type": str,
                "element_explanations": [
                    {
                        "element_id": str,
                        "element_type": str,
                        "analyses": [
                            {
                                "failure_reason": str,
                                "root_cause": str,
                                "metrics": {...},
                                "impact_on_users": str,
                                ...
                            }
                        ],
                        "solutions": [
                            {
                                "recommendation": str,
                                "implementation_steps": [...],
                                "alternatives": [...],
                                "estimated_cost": str,
                                ...
                            }
                        ]
                    }
                ]
            }
        }
    """
    try:
        data = request.get_json()
        element_id = data.get("element_id")
        element_type = data.get("element_type")
        element_name = data.get("element_name")
        failed_rules = data.get("failed_rules", [])
        
        if not element_id or not element_type:
            return jsonify({"success": False, "error": "element_id and element_type required"}), 400
        
        if not failed_rules:
            return jsonify({"success": False, "error": "failed_rules required"}), 400
        
        logger.info(f"Analyzing failure for element {element_id} with {len(failed_rules)} failed rules")
        
        # Enrich failed_rules with full rule objects from reasoning engine
        enriched_failed_rules = []
        for failed_rule in failed_rules:
            rule_id = failed_rule.get("rule_id")
            
            # Look up full rule object from reasoning engine
            full_rule = None
            if rule_id in reasoning_engine.rules:
                full_rule = reasoning_engine.rules[rule_id]
            
            # Build enriched rule result with full rule object
            enriched_rule = {
                "rule": full_rule or {
                    "id": rule_id,
                    "name": failed_rule.get("rule_name", "Unknown Rule"),
                    "description": failed_rule.get("rule_name", "Unknown Rule")
                },
                "actual_value": failed_rule.get("actual_value"),
                "required_value": failed_rule.get("required_value"),
                "unit": failed_rule.get("unit", ""),
                "location": failed_rule.get("location")
            }
            enriched_failed_rules.append(enriched_rule)
        
        result = reasoning_engine.explain_failure(
            element_id, element_type, element_name, enriched_failed_rules
        )
        
        return jsonify({"success": True, "reasoning": result}), 200
    
    except Exception as e:
        logger.exception("Error analyzing failure")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reasoning/analyze-pass", methods=["POST"])
def analyze_pass():
    """
    Explain WHY an element PASSED a compliance check.
    
    Request:
        {
            "element_id": str,
            "element_type": str,
            "element_name": str (optional),
            "passed_rules": [
                {
                    "rule_id": str,
                    "rule_name": str,
                    "actual_value": any,
                    "required_value": any,
                    "unit": str (optional),
                    "location": str (optional)
                }
            ]
        }
    
    Response:
        {
            "success": bool,
            "reasoning": {
                "element_id": str,
                "element_type": str,
                "element_name": str,
                "compliance_explanations": [
                    {
                        "rule_id": str,
                        "rule_name": str,
                        "why_passed": str,
                        "actual_value": any,
                        "required_value": any,
                        "metrics": {...},
                        "margin": str,
                        "beneficiaries": str,
                        "design_standard": str
                    }
                ]
            }
        }
    """
    try:
        data = request.get_json()
        element_id = data.get("element_id")
        element_type = data.get("element_type")
        element_name = data.get("element_name")
        passed_rules = data.get("passed_rules", [])
        
        if not element_id or not element_type:
            return jsonify({"success": False, "error": "element_id and element_type required"}), 400
        
        if not passed_rules:
            return jsonify({"success": False, "error": "passed_rules required"}), 400
        
        # Build explanations for passing checks
        compliance_explanations = []
        
        for passed_rule in passed_rules:
            rule_id = passed_rule.get("rule_id")
            actual_value = passed_rule.get("actual_value")
            required_value = passed_rule.get("required_value")
            unit = passed_rule.get("unit", "")
            
            # Look up full rule from reasoning engine
            full_rule = reasoning_engine.rules.get(rule_id, {})
            
            # Calculate how much it exceeds requirement
            margin_info = ""
            if actual_value is not None and required_value is not None:
                try:
                    actual_float = float(actual_value)
                    required_float = float(required_value)
                    if required_float > 0:
                        excess_pct = ((actual_float - required_float) / required_float) * 100
                        excess_abs = actual_float - required_float
                        margin_info = f"{excess_pct:.1f}% above minimum ({excess_abs:.1f}{unit} margin)"
                except (ValueError, TypeError):
                    margin_info = f"Exceeds minimum requirement"
            
            # Get beneficiaries from rule
            beneficiaries = ""
            rule_name = full_rule.get("name", passed_rule.get("rule_name", "Unknown"))
            
            if "door" in rule_name.lower() or "door" in element_type.lower():
                beneficiaries = "Users with mobility devices, wheelchair users, elderly"
            elif "window" in rule_name.lower():
                beneficiaries = "Building occupants - emergency egress and daylight access"
            elif "bedroom" in rule_name.lower():
                beneficiaries = "Building occupants - habitable space requirements"
            elif "bathroom" in rule_name.lower():
                beneficiaries = "Building occupants - bathroom functionality"
            elif "stair" in rule_name.lower():
                beneficiaries = "All building occupants - accessible circulation"
            elif "corridor" in rule_name.lower():
                beneficiaries = "Users with mobility limitations, wheelchair users"
            else:
                beneficiaries = "Building occupants and users with accessibility needs"
            
            # Get design standard
            provenance = full_rule.get("provenance", {})
            design_standard = f"{provenance.get('regulation', 'Building Code')} - Section {provenance.get('section', 'TBD')}"
            
            explanation = {
                "rule_id": rule_id,
                "rule_name": rule_name,
                "why_passed": f"This element meets or exceeds the {rule_name}. {margin_info}",
                "actual_value": actual_value,
                "required_value": required_value,
                "unit": unit,
                "metrics": {
                    "actual": actual_value,
                    "required": required_value,
                    "unit": unit,
                    "compliance": "✓ Pass"
                },
                "margin": margin_info,
                "beneficiaries": beneficiaries,
                "design_standard": design_standard,
                "description": full_rule.get("description", "")
            }
            compliance_explanations.append(explanation)
        
        result = {
            "element_id": element_id,
            "element_type": element_type,
            "element_name": element_name or "Unknown",
            "compliance_explanations": compliance_explanations,
            "summary": f"Element {element_name or element_id} passes {len(compliance_explanations)} compliance requirements"
        }
        
        return jsonify({"success": True, "reasoning": result}), 200
    
    except Exception as e:
        logger.exception("Error analyzing pass")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reasoning/enrich-compliance", methods=["POST"])
def enrich_compliance_with_reasoning():
    """
    REASONING LAYER: Enrich cached compliance results with explanations.
    
    ARCHITECTURE DEPENDENCY CHAIN:
    ==============================
    1. Rule Layer (Foundation)
       └─ Provides rule definitions and catalogue
    
    2. Compliance Check Layer (Calculation - CACHED)
       └─ /api/compliance/check executes rules, caches results
       └─ Results include: pass/fail, metrics, explanations (WHY)
    
    3. Reasoning Layer (Explanation - THIS ENDPOINT)
       └─ Reads cached compliance results (NO recalculation)
       └─ Adds detailed reasoning and solutions
       └─ Enriches results with "why" information
    
    KEY BEHAVIOR:
    - This endpoint does NOT re-execute compliance checks
    - This endpoint does NOT modify rules or pass/fail status
    - This endpoint ONLY adds explanations to cached results
    - Uses results from /api/compliance/check as input
    
    Request:
        {
            "compliance_results": dict (from /api/compliance/check endpoint)
        }
    
    The input compliance_results must contain:
    - results: List of individual rule check results (ALREADY CALCULATED)
    - summary: {total, passed, failed, unknown}
    - Each result includes: element_guid, rule_id, passed (boolean), explanation
    
    Response:
        {
            "success": bool,
            "enriched_results": {...},  // Original results + element_reasoning
            "reasoning_added": bool,     // Whether reasoning was added
            "element_explanations_count": int  // Number of elements explained
        }
    """
    try:
        data = request.get_json()
        compliance_results = data.get("compliance_results")
        
        if not compliance_results:
            return jsonify({"success": False, "error": "compliance_results required"}), 400
        
        # Call reasoning layer to enrich (read-only operation on cached results)
        enriched = reasoning_engine.explain_compliance_check(compliance_results)
        
        return jsonify({
            "success": True,
            "enriched_results": enriched,
            "reasoning_added": "element_reasoning" in enriched,
            "element_explanations_count": len(enriched.get("element_reasoning", []))
        }), 200
    
    except Exception as e:
        logger.error(f"Error enriching compliance results: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reasoning/validate", methods=["GET"])
def validate_reasoning_layer():
    """
    Validate reasoning layer configuration and readiness.
    
    Response:
        {
            "success": bool,
            "validation": {
                "rules_loaded": bool,
                "total_rules": int,
                "standards": {...},
                "components": {...}
            }
        }
    """
    try:
        validation = reasoning_engine.validate_reasoning_layer()
        
        return jsonify({
            "success": True,
            "validation": validation
        }), 200
    
    except Exception as e:
        logger.error(f"Error validating reasoning layer: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rules/load-regulations", methods=["POST"])
def load_regulations_endpoint():
    """Load regulatory rules on-demand into the reasoning engine.
    
    This endpoint allows the frontend to trigger lazy-loading of rules.
    Rules are NOT loaded at server startup - they are loaded when the user
    imports/selects them via this endpoint.
    
    Request JSON:
        {
            "file_path": str - path to rules JSON file,
            "rule_type": str - 'regulatory' or 'custom' (default: 'regulatory')
        }
    
    Response:
        {
            "success": bool,
            "rule_type": str,
            "rules_loaded": int - number of rules loaded,
            "sample_rules": list - first 3 rule IDs as examples,
            "error": str or null
        }
    
    Architecture Context:
    - Rule Layer: Loads rules (now lazy-loaded here)
    - Compliance Layer: Executes compliance checks (cached)
    - Reasoning Layer: Reads cached results to explain why rules passed/failed
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body required with file_path"
            }), 400
        
        file_path = data.get("file_path")
        rule_type = data.get("rule_type", "regulatory")
        
        if not file_path:
            return jsonify({
                "success": False,
                "error": "file_path is required"
            }), 400
        
        if rule_type not in ["regulatory", "custom"]:
            return jsonify({
                "success": False,
                "error": "rule_type must be 'regulatory' or 'custom'"
            }), 400
        
        # Resolve file_path relative to project root
        # If path is relative, resolve from project root (parent of backend/)
        from pathlib import Path
        if not Path(file_path).is_absolute():
            # Get project root (parent of backend directory)
            backend_dir = Path(__file__).parent
            project_root = backend_dir.parent
            file_path = str(project_root / file_path)
        
        logger.info(f"[APP] Loading {rule_type} rules from: {file_path}")
        
        # Call the reasoning engine to load rules on-demand
        result = reasoning_engine.load_rules_from_file(file_path, rule_type=rule_type)
        
        if result.get("success"):
            # Track that rules were imported in this session
            global rules_imported_in_session
            rules_imported_in_session = True
            logger.info(f"[APP] Loaded {rule_type} rules: {result['rules_loaded']} rules from {file_path}")
        
        return jsonify(result), (200 if result.get("success") else 400)
    
    except Exception as e:
        logger.error(f"Error loading regulations: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ===== Unified Configuration Management Endpoints =====

@app.route("/api/config/load", methods=["GET"])
def load_unified_config():
    """Load the unified rules mapping configuration."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        config = manager.load_config()
        
        if not config:
            logger.error("Config returned empty")
            return jsonify({
                "success": False,
                "config": None,
                "error": "Configuration is empty or could not be loaded"
            }), 500
        
        logger.info(f"Successfully loaded config with {len(config.get('rule_mappings', []))} mappings")
        return jsonify({
            "success": True,
            "config": config,
            "error": None
        })
    except Exception as e:
        logger.exception("Error loading unified config")
        return jsonify({
            "success": False,
            "config": None,
            "error": f"Error loading config: {str(e)}"
        }), 500


@app.route("/api/config/save", methods=["POST"])
def save_unified_config():
    """Save the unified rules mapping configuration."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "config" not in data:
            return jsonify({
                "success": False,
                "error": "config object required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.save_config(data["config"])
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception("Error saving unified config")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/validate", methods=["POST"])
def validate_unified_config():
    """Validate the unified rules mapping configuration."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "config" not in data:
            return jsonify({
                "success": False,
                "error": "config object required in request body"
            }), 400
        
        manager = get_config_manager()
        is_valid, errors = manager.validate_config(data["config"])
        
        return jsonify({
            "success": is_valid,
            "is_valid": is_valid,
            "errors": errors
        })
    except Exception as e:
        logger.exception("Error validating unified config")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/check-mappings", methods=["POST"])
def check_config_mappings():
    """Check how many IFC elements are mapped to rules.
    
    Uses current rules from RulesVersionManager to get the latest mappings.
    
    Expects JSON POST with:
    - graph: The IFC graph object (from data layer)
    
    Returns statistics on element counts per element type and rule mapping coverage.
    """
    try:
        data = request.get_json()
        graph = data.get("graph") if data else None
        
        if not graph:
            return jsonify({
                "success": False,
                "error": "graph object required in request body"
            }), 400
        
        # Extract elements from the graph
        elements = graph.get("elements", {}) or {}
        
        # Load current rules from session (in-memory) or latest version
        try:
            rules_list = get_session_rules()
        except Exception as e:
            logger.error(f"[CHECK-MAPPINGS] Error loading rules from session: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to load rules: {str(e)}"
            }), 500
        
        # Create rule mappings from current rules based on their target IFC classes
        rule_mappings = []
        for rule in rules_list:
            target = rule.get('target', {})
            ifc_class = target.get('ifc_class', '')
            if ifc_class:
                # Map rule to its target IFC class
                rule_mappings.append({
                    'mapping_id': rule.get('id'),
                    'rule_id': rule.get('id'),
                    'rule_reference': {'rule_id': rule.get('id')},
                    'element_type': ifc_class,
                    'enabled': True
                })
        
        logger.info(f"[CHECK-MAPPINGS] Loaded {len(rules_list)} rules, created {len(rule_mappings)} mappings")
        
        # Build mapping statistics
        mapping_stats = {}
        total_elements_by_type = {}
        
        # Count total elements by type in IFC
        for element_type, element_list in elements.items():
            if isinstance(element_list, list):
                total_elements_by_type[element_type] = len(element_list)
        
        logger.info(f"IFC element types found: {list(total_elements_by_type.keys())}")
        
        # Create normalized mapping (lowercase + remove 'ifc' prefix + singularize for common plurals)
        def normalize_element_type(type_str):
            """Normalize element type: lowercase, remove 'Ifc' prefix, and singularize"""
            normalized = type_str.lower()
            # Remove 'ifc' prefix if present
            if normalized.startswith('ifc'):
                normalized = normalized[3:]
            # Remove trailing 's' for common plurals: doors->door, spaces->space, stairs->stair, etc.
            if normalized.endswith('s') and len(normalized) > 1:
                singular = normalized[:-1]  # Remove the 's'
                return singular
            return normalized
        
        # Normalize both element types from IFC and rule targets
        elements_by_type_normalized = {normalize_element_type(k): v for k, v in total_elements_by_type.items()}
        logger.info(f"Normalized element types from IFC: {list(elements_by_type_normalized.keys())}")
        
        # For each rule mapping, count how many elements of that type exist
        for mapping in rule_mappings:
            if not mapping.get("enabled", True):
                continue
            
            mapping_id = mapping.get("mapping_id", "unknown")
            element_type_raw = mapping.get("element_type", "")
            element_type_normalized = normalize_element_type(element_type_raw)  # Normalize the rule's target
            rule_id = mapping.get("rule_reference", {}).get("rule_id", "")
            
            # Look up normalized element count
            element_count = elements_by_type_normalized.get(element_type_normalized, 0)
            logger.debug(f"Mapping {mapping_id}: rule targets '{element_type_raw}' -> normalized '{element_type_normalized}' -> found {element_count} elements")
            
            mapping_stats[mapping_id] = {
                "mapping_id": mapping_id,
                "rule_id": rule_id,
                "element_type": element_type_raw,
                "elements_in_ifc": element_count,
                "enabled": mapping.get("enabled", True)
            }
        
        # Summary statistics
        # Count unique elements that have at least one mapping
        element_types_with_mappings = set()
        for mapping in rule_mappings:
            if mapping.get("enabled", True):
                element_types_with_mappings.add(normalize_element_type(mapping.get("element_type", "")))
        
        # Count total elements that have at least one mapping
        mapped_elements = sum(
            v for k, v in elements_by_type_normalized.items() 
            if k in element_types_with_mappings
        )
        
        summary = {
            "total_elements": sum(total_elements_by_type.values()),
            "elements_by_type": total_elements_by_type,
            "total_mappings": len([m for m in rule_mappings if m.get("enabled", True)]),
            "mapped_elements": mapped_elements,  # Elements that have at least one mapping
            "coverage_percentage": int((mapped_elements / sum(total_elements_by_type.values()) * 100)) if sum(total_elements_by_type.values()) > 0 else 0
        }
        
        return jsonify({
            "success": True,
            "summary": summary,
            "mappings": mapping_stats
        })
    except Exception as e:
        logger.exception("Error checking config mappings")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/ifc-elements", methods=["GET"])
def get_ifc_elements():
    """Get all IFC element type mappings."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        elements = manager.get_ifc_element_mappings()
        
        return jsonify({
            "success": True,
            "elements": elements
        })
    except Exception as e:
        logger.exception("Error getting IFC element mappings")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/element-attributes/<element_type>", methods=["GET"])
def get_element_attributes(element_type):
    """Get attributes for a specific IFC element type."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        attributes = manager.get_element_attributes(element_type)
        
        return jsonify({
            "success": True,
            "element_type": element_type,
            "attributes": attributes
        })
    except Exception as e:
        logger.exception(f"Error getting attributes for element {element_type}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/element-attributes/<element_type>", methods=["POST"])
def add_element_attribute(element_type):
    """Add a new attribute to an element type."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "attribute" not in data:
            return jsonify({
                "success": False,
                "error": "attribute object required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.add_element_attribute(element_type, data["attribute"])
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception(f"Error adding attribute to element {element_type}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/element-attributes/<element_type>/<attribute_name>", methods=["PUT"])
def update_element_attribute(element_type, attribute_name):
    """Update an attribute in an element type."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "attribute" not in data:
            return jsonify({
                "success": False,
                "error": "attribute object required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.update_element_attribute(
            element_type, attribute_name, data["attribute"]
        )
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception(f"Error updating attribute {attribute_name} in element {element_type}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/element-attributes/<element_type>/<attribute_name>", methods=["DELETE"])
def delete_element_attribute(element_type, attribute_name):
    """Delete an attribute from an element type."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        success, message = manager.delete_element_attribute(element_type, attribute_name)
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception(f"Error deleting attribute {attribute_name} from element {element_type}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/rule-mappings", methods=["GET"])
def get_rule_mappings():
    """Get all rule mappings."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        mappings = manager.get_rule_mappings()
        
        return jsonify({
            "success": True,
            "mappings": mappings
        })
    except Exception as e:
        logger.exception("Error getting rule mappings")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/rule-mappings", methods=["POST"])
def add_rule_mapping():
    """Add a new rule mapping."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "mapping" not in data:
            return jsonify({
                "success": False,
                "error": "mapping object required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.add_rule_mapping(data["mapping"])
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception("Error adding rule mapping")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/rule-mappings/<mapping_id>", methods=["PUT"])
def update_rule_mapping(mapping_id):
    """Update a rule mapping."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "mapping" not in data:
            return jsonify({
                "success": False,
                "error": "mapping object required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.update_rule_mapping(mapping_id, data["mapping"])
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception(f"Error updating rule mapping {mapping_id}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/rule-mappings/<mapping_id>", methods=["DELETE"])
def delete_rule_mapping(mapping_id):
    """Delete a rule mapping."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        success, message = manager.delete_rule_mapping(mapping_id)
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception(f"Error deleting rule mapping {mapping_id}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/rule-mappings/<mapping_id>/toggle", methods=["PUT"])
def toggle_rule_mapping(mapping_id):
    """Enable or disable a rule mapping."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "enabled" not in data:
            return jsonify({
                "success": False,
                "error": "enabled boolean required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.enable_rule_mapping(mapping_id, data["enabled"])
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception(f"Error toggling rule mapping {mapping_id}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/import", methods=["POST"])
def import_config():
    """Import and merge configuration."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        data = request.get_json()
        if not data or "config" not in data:
            return jsonify({
                "success": False,
                "error": "config object required in request body"
            }), 400
        
        manager = get_config_manager()
        success, message = manager.import_config(data["config"])
        
        return jsonify({
            "success": success,
            "message": message,
            "error": None if success else message
        }), (200 if success else 400)
    except Exception as e:
        logger.exception("Error importing config")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/export", methods=["GET"])
def export_config():
    """Export current configuration."""
    try:
        from backend.unified_config_manager import get_config_manager
        
        manager = get_config_manager()
        config = manager.export_config()
        
        return jsonify({
            "success": True,
            "config": config
        })
    except Exception as e:
        logger.exception("Error exporting config")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config/validate-mappings", methods=["POST"])
def validate_mappings_endpoint():
    """Validate Rule Config mappings against catalogue and cleanup orphaned mappings."""
    try:
        from validate_mappings import validate_mappings, cleanup_orphaned_mappings
        
        base_path = Path(__file__).parent.parent / 'rules_config'
        catalogue_path = str(base_path / 'enhanced-regulation-rules.json')
        config_path = str(base_path / 'unified_rules_mapping.json')
        
        # Validate
        orphaned, total, valid = validate_mappings(catalogue_path, config_path)
        
        result = {
            "success": True,
            "catalogue_rules": len(set(rule['id'] for rule in 
                json.load(open(catalogue_path))['rules'])),
            "total_mappings": total,
            "valid_mappings": valid,
            "orphaned_mappings": len(orphaned),
            "orphaned_list": orphaned
        }
        
        # Auto-cleanup if orphaned mappings found
        if orphaned:
            removed = cleanup_orphaned_mappings(config_path, orphaned)
            result["removed_mappings"] = removed
            result["message"] = f"Found and removed {removed} orphaned mapping(s)"
            logger.info(f"Cleaned up {removed} orphaned mappings from Rule Config")
            
            # Reload config manager to reflect changes
            config_manager.reload()
        else:
            result["message"] = "All mappings are valid"
            result["removed_mappings"] = 0
        
        return jsonify(result)
    
    except Exception as e:
        logger.exception("Error validating mappings")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Validation failed"
        }), 500


@app.route("/api/rules/available", methods=["GET"])
def get_available_rules():
    """Get available regulatory rules from session or current version."""
    try:
        # Get rules from session (in-memory) or latest version
        rules = get_session_rules()
        
        return jsonify({
            "success": True,
            "rules": [
                {
                    "id": rule.get('id'),
                    "name": rule.get('name'),
                    "description": rule.get('description')
                }
                for rule in rules
            ]
        })
    except Exception as e:
        logger.exception("Error loading available rules")
        return jsonify({
            "success": False,
            "error": str(e),
            "rules": []
        }), 500


@app.route("/api/rules/verify-sync", methods=["GET"])

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


# Register TRM API endpoints
from backend.trm_model_manager import ModelVersionManager
model_version_manager = ModelVersionManager(Path("backend/model_versions"))
register_trm_endpoints(app, model_version_manager)

# Register Model Management endpoints
register_model_management_endpoints(app, model_version_manager)

# Register Rules Versioning endpoints
app.register_blueprint(rules_versioning_bp)

# Register Rules Sync endpoints
app.register_blueprint(rules_sync_bp)


if __name__ == "__main__":
    logger.info("Starting IFC Explorer API server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
