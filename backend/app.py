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

# Initialize reasoning engine WITHOUT loading rules at startup
# Rules will be loaded on-demand when user imports/selects them
reasoning_engine = ReasoningEngine(
    rules_file=None,  # Not loaded at startup
    custom_rules_file=None  # Not loaded at startup
)

# Track if rules have been imported in this session
rules_imported_in_session = False


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
    
    Uses the unified compliance engine with regulatory rules from enhanced-regulation-rules.json
    
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
        
        # Initialize unified compliance engine with regulatory rules
        rules_file = Path(__file__).parent.parent / 'rules_config' / 'enhanced-regulation-rules.json'
        engine = UnifiedComplianceEngine(str(rules_file))
        
        logger.info(f"Using {len(engine.rules)} regulatory compliance rules")
        
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
        # Load custom rules (user-imported rules)
        # Return empty array if no custom rules exist (empty catalogue by default)
        custom_rules = load_custom_rules()
        
        return jsonify({
            "success": True,
            "rules": custom_rules,
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
    """Add a custom rule to the ruleset.
    
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
        
        logger.info("Adding custom rule: %s", rule.get("id"))
        success = add_rule(rule)
        
        if success:
            custom = load_custom_rules()
            return jsonify({
                "success": True,
                "custom_rules": custom,
                "error": None,
            })
        else:
            return jsonify({
                "success": False,
                "custom_rules": None,
                "error": "Failed to add rule (may already exist)",
            }), 400
    except Exception as e:
        logger.exception("Failed to add rule")
        return jsonify({
            "success": False,
            "custom_rules": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/delete/<rule_id>", methods=["DELETE"])
def delete_rule_endpoint(rule_id):
    """Delete a custom rule from the ruleset.
    
    Response:
        {
            "success": bool,
            "rules": list,
            "error": str or null
        }
    """
    try:
        logger.info("Deleting custom rule: %s", rule_id)
        success = delete_rule(rule_id)
        
        if success:
            custom = load_custom_rules()
            
            # Reset rules imported flag if no rules left
            global rules_imported_in_session
            if len(custom) == 0:
                rules_imported_in_session = False
            
            return jsonify({
                "success": True,
                "rules": custom,
                "error": None,
            })
        else:
            return jsonify({
                "success": False,
                "rules": None,
                "error": "Rule not found",
            }), 404
    except Exception as e:
        logger.exception("Failed to delete rule")
        return jsonify({
            "success": False,
            "rules": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/save-all", methods=["POST"])
def save_all_rules_endpoint():
    """Save all custom rules at once.
    
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
        
        logger.info("Saving %d custom rules", len(rules))
        
        # Save all rules
        save_custom_rules(rules)
        
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
    """Get all custom rules.
    
    Response:
        {
            "success": bool,
            "custom_rules": list,
            "error": str or null
        }
    """
    try:
        custom = load_custom_rules()
        return jsonify({
            "success": True,
            "custom_rules": custom,
            "error": None,
        })
    except Exception as e:
        logger.exception("Failed to get custom rules")
        return jsonify({
            "success": False,
            "custom_rules": None,
            "error": str(e),
        }), 500


@app.route("/api/rules/import", methods=["POST"])
def import_rules_endpoint():
    """Import rules from JSON file.
    
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
        
        # Call import_rules (saves to custom_rules.json)
        status = import_rules(rules_to_import, merge=merge)
        logger.info(f"[IMPORT] Imported {status.get('added', 0)} rules, skipped {status.get('skipped', 0)}")
        
        # Immediately load the imported rules into reasoning_engine
        if status.get('added', 0) > 0:
            try:
                from pathlib import Path
                backend_dir = Path(__file__).parent
                project_root = backend_dir.parent
                custom_rules_path = str(project_root / "rules_config" / "custom_rules.json")
                logger.info(f"[IMPORT] Loading rules into reasoning engine from: {custom_rules_path}")
                
                result = reasoning_engine.load_rules_from_file(custom_rules_path, rule_type='custom')
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


@app.route("/api/rules/generate", methods=["POST"])
def generate_rules():
    """Generate rules from IFC graph using selected extraction strategies.
    
    Request:
        {
            "graph": dict (the data-layer graph),
            "strategies": list (["pset", "statistical", "metadata"])
        }
    
    Response:
        {
            "success": bool,
            "rules_count": int,
            "rules": list,
            "error": str or null
        }
    """
    try:
        from data_layer.extract_rules import extract_rules_from_graph
        
        data = request.get_json()
        graph = data.get("graph")
        strategies = data.get("strategies", ["pset", "statistical", "metadata"])
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        if not isinstance(strategies, list) or len(strategies) == 0:
            return jsonify({"success": False, "error": "strategies must be a non-empty list"}), 400
        
        # Validate strategy names
        valid_strategies = {"pset", "statistical", "metadata"}
        if not all(s in valid_strategies for s in strategies):
            return jsonify({"success": False, "error": f"Invalid strategies. Must be one of: {valid_strategies}"}), 400
        
        logger.info(f"Generating rules with strategies: {strategies}")
        
        # Extract rules using selected strategies
        result = extract_rules_from_graph(graph, strategies=strategies)
        rules = result.get("rules", [])
        
        # Save to custom_rules.json
        save_custom_rules(rules)
        
        # Mark that rules have been generated/activated in this session
        global rules_imported_in_session
        if len(rules) > 0:
            rules_imported_in_session = True
        
        return jsonify({
            "success": True,
            "rules_count": len(rules),
            "rules": rules,
            "error": None
        })
    
    except Exception as e:
        logger.exception("Rule generation failed")
        return jsonify({
            "success": False,
            "rules_count": 0,
            "rules": None,
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
    """Import rules from JSON file.
    
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
        
        mode = request.form.get('mode', 'append')  # Default to append for backward compatibility
        
        data = json.load(file)
        
        if 'rules' not in data or not isinstance(data.get('rules'), list):
            return jsonify({"success": False, "error": "Invalid JSON format: must contain 'rules' array"}), 400
        
        new_rules = data.get('rules', [])
        
        if mode == 'replace':
            # Fresh import: replace all existing rules
            existing_rules = []
            added_count = len(new_rules)
            skipped_count = 0
        else:
            # Append mode: merge with existing
            existing_rules = load_custom_rules()
            
            # Get existing rule IDs to avoid duplicates
            existing_ids = {rule.get('id') for rule in existing_rules}
            
            # Add new rules, skip duplicates
            added_count = 0
            skipped_count = 0
            
            for rule in new_rules:
                if rule.get('id') not in existing_ids:
                    existing_rules.append(rule)
                    added_count += 1
                else:
                    skipped_count += 1
        
        # Combine rules based on mode
        if mode == 'replace':
            final_rules = new_rules
        else:
            final_rules = existing_rules
        
        # Save updated rules
        save_custom_rules(final_rules)
        
        logger.info(f"[IMPORT-CATALOGUE] Imported {added_count} rules in '{mode}' mode, skipped {skipped_count}")
        
        # Immediately load the imported rules into reasoning_engine
        if added_count > 0:
            try:
                from pathlib import Path
                backend_dir = Path(__file__).parent
                project_root = backend_dir.parent
                custom_rules_path = str(project_root / "rules_config" / "custom_rules.json")
                logger.info(f"[IMPORT-CATALOGUE] Loading rules into reasoning engine from: {custom_rules_path}")
                
                result = reasoning_engine.load_rules_from_file(custom_rules_path, rule_type='custom')
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
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rules/update", methods=["PUT"])
def update_rule():
    """Update a specific rule."""
    try:
        data = request.get_json()
        rule_id = data.get('id')
        
        if not rule_id:
            return jsonify({"success": False, "error": "Rule ID required"}), 400
        
        # Load current custom rules
        custom_rules = load_custom_rules()
        
        # Find and update rule
        rule_found = False
        for rule in custom_rules:
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
        
        # Save updated rules
        save_custom_rules(custom_rules)
        
        return jsonify({
            "success": True,
            "rules": custom_rules,
            "error": None
        })
    
    except Exception as e:
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
            logger.info(f"Compliance check: Graph has elements section with keys: {list(elements.keys() if isinstance(elements, dict) else [])}")
            if isinstance(elements, dict):
                for elem_type, elem_list in elements.items():
                    logger.info(f"Compliance check: Found {len(elem_list) if isinstance(elem_list, list) else 0} {elem_type}")
        else:
            logger.info(f"Compliance check: Graph has NO elements section. Available keys: {list(graph.keys())}")
        
        # Initialize unified compliance engine
        rules_file = Path(__file__).parent.parent / 'rules_config' / 'enhanced-regulation-rules.json'
        engine = UnifiedComplianceEngine(str(rules_file))
        
        logger.info(f"Compliance check: Loaded {len(engine.rules)} rules")
        
        # Filter rules if specified
        rules_to_check = engine.rules
        if rule_ids:
            rules_to_check = [r for r in engine.rules if r.get('id') in rule_ids]
        
        # Run compliance check
        results = engine.check_graph(graph, rules_to_check, target_classes if target_classes else None)
        
        logger.info(f"Compliance check: Found {len(results.get('results', []))} check results")
        if results.get('results'):
            rule_ids = set(r.get('rule_id') for r in results['results'] if r.get('rule_id'))
            logger.info(f"Compliance check: Rule IDs in results: {rule_ids}")
        
        return jsonify({
            "success": True,
            **results,
            "error": None
        })
    
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
        
        # Load all regulatory rules
        rules_file = Path(__file__).parent.parent / 'rules_config' / 'enhanced-regulation-rules.json'
        if not rules_file.exists():
            return jsonify({"success": False, "error": "Rules file not found"}), 404
        
        with open(rules_file, 'r') as f:
            rules_data = json.load(f)
        
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
    
    Reloads rules from file each time to reflect any updates (deletions, modifications).
    """
    try:
        body = request.get_json()
        graph = body.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "No graph provided"}), 400
        
        # CRITICAL: Reload rules from file each time to reflect user updates
        # This ensures rule deletions/modifications are immediately reflected
        rules_file = Path(__file__).parent.parent / 'rules_config' / 'custom_rules.json'
        
        if not rules_file.exists():
            return jsonify({
                "success": False,
                "error": "No rules loaded. Please import regulatory rules first."
            }), 400
        
        # Load rules from file (fresh, not cached)
        with open(rules_file, 'r', encoding='utf-8') as f:
            loaded_rules_data = json.load(f)
        
        rules_list = loaded_rules_data.get('rules', []) if isinstance(loaded_rules_data, dict) else (loaded_rules_data if isinstance(loaded_rules_data, list) else [])
        
        if not rules_list:
            return jsonify({
                "success": False,
                "error": "No rules available. Please import regulatory rules first."
            }), 400
        
        # Convert list to dict format if needed
        rules_dict = {}
        for rule in rules_list:
            rule_id = rule.get('id')
            if rule_id:
                rules_dict[rule_id] = rule
        
        logger.info(f"[COMPLIANCE REPORT] Reloaded {len(rules_dict)} rules from {rules_file}")
        
        # Pass fresh rules to generator
        generator = ComplianceReportGenerator(rules=rules_dict)
        report = generator.generate_report(graph)
        
        return jsonify({"success": True, "report": report}), 200
    
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
    
    Uses ONLY rules that have been explicitly imported by the user in this session.
    Reloads rules from file each time to reflect any updates (deletions, modifications).
    """
    try:
        body = request.get_json()
        graph = body.get("graph")
        
        if not graph:
            return jsonify({"success": False, "error": "No graph provided"}), 400
        
        # CRITICAL: Reload rules from file each time to reflect user updates
        # This ensures rule deletions/modifications are immediately reflected
        rules_file = Path(__file__).parent.parent / 'rules_config' / 'custom_rules.json'
        
        if not rules_file.exists():
            return jsonify({
                "success": False, 
                "error": "No rules loaded. Please import regulatory rules first.",
                "compliance": None
            }), 400
        
        # Load rules from file (fresh, not cached)
        with open(rules_file, 'r', encoding='utf-8') as f:
            loaded_rules_data = json.load(f)
        
        rules_list = loaded_rules_data.get('rules', []) if isinstance(loaded_rules_data, dict) else (loaded_rules_data if isinstance(loaded_rules_data, list) else [])
        
        if not rules_list:
            return jsonify({
                "success": False, 
                "error": "No rules available. Please import regulatory rules first.",
                "compliance": None
            }), 400
        
        # Create engine and set the fresh rules
        engine = UnifiedComplianceEngine()
        engine.rules = rules_list
        
        logger.info(f"[COMPLIANCE CHECK] Reloaded {len(engine.rules)} rules from {rules_file}")
        logger.info(f"[COMPLIANCE CHECK] Rule IDs: {[r.get('id', 'N/A') for r in engine.rules[:5]]}")
        
        # Check compliance using the fresh rules
        result = engine.check_compliance(graph, rules_manifest_path=None)
        
        # Log summary
        if result.get("summary"):
            summary = result["summary"]
            logger.info(f"[COMPLIANCE CHECK] Summary: {summary['total_rules']} rules, {summary['components_checked']} components checked, {summary['total_evaluations']} evaluations")
            
            # Log results per rule
            for rule_result in result.get("rules", [])[:5]:
                logger.info(f"[COMPLIANCE CHECK] Rule {rule_result['rule_id']}: {rule_result['passed']} passed, {rule_result['failed']} failed")
        
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
    
    This endpoint:
    1. Checks if rules are in reasoning_engine.rules
    2. If not, but rules exist on disk, auto-loads them
    3. Returns current status
    
    Query parameters:
    - refresh=true: Force reload rules from disk
    """
    try:
        # Check if we should refresh/reload rules from disk
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Check if rules are in the reasoning_engine (user-imported rules)
        rules_dict = reasoning_engine.rules if hasattr(reasoning_engine, 'rules') else {}
        
        # Convert dict to list if needed
        if isinstance(rules_dict, dict):
            rules_list = list(rules_dict.values())
        else:
            rules_list = rules_dict if rules_dict else []
        
        rules_loaded = len(rules_list) > 0
        
        # If refresh requested or no rules in memory but they exist on disk, reload them
        if refresh or not rules_loaded:
            from pathlib import Path
            backend_dir = Path(__file__).parent
            project_root = backend_dir.parent
            custom_rules_path = project_root / "rules_config" / "custom_rules.json"
            
            if custom_rules_path.exists():
                try:
                    if refresh:
                        logger.info(f"[CHECK-STATUS] Refresh requested. Reloading rules from {custom_rules_path}")
                    else:
                        logger.info(f"[CHECK-STATUS] Rules not in memory. Auto-loading from {custom_rules_path}")
                    
                    # Always clear before loading to ensure we get the current state from disk
                    result = reasoning_engine.load_rules_from_file(str(custom_rules_path), rule_type='custom', clear_existing=True)
                    if result.get('success'):
                        logger.info(f"[CHECK-STATUS] ✓ Loaded {result['rules_loaded']} rules")
                        # Update rules_list after loading
                        rules_dict = reasoning_engine.rules if hasattr(reasoning_engine, 'rules') else {}
                        if isinstance(rules_dict, dict):
                            rules_list = list(rules_dict.values())
                        else:
                            rules_list = rules_dict if rules_dict else []
                        rules_loaded = len(rules_list) > 0
                except Exception as e:
                    logger.warning(f"[CHECK-STATUS] Failed to load rules: {e}")
        
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


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting IFC Explorer API server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
