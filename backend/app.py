"""Flask API backend for IFC Explorer web application."""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import json
import logging
import tempfile
from typing import Dict, Any, List

from data_layer.services import DataLayerService
from data_layer.load_ifc import preview_ifc
from rule_layer.run_rules import run_with_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Services
data_svc = DataLayerService()


# ===== IFC Loading Endpoints =====

@app.route("/api/ifc/preview", methods=["POST"])
def preview_ifc_endpoint():
    """Load and preview an IFC file.
    
    Request:
        {
            "ifc_path": str
        }
    
    Response:
        {
            "success": bool,
            "preview": dict,
            "error": str or null
        }
    """
    try:
        data = request.get_json()
        ifc_path = data.get("ifc_path")
        
        if not ifc_path:
            return jsonify({"success": False, "error": "ifc_path required"}), 400
        
        logger.info("Loading IFC preview: %s", ifc_path)
        model = data_svc.load_model(ifc_path)
        preview = preview_ifc(model)
        
        return jsonify({
            "success": True,
            "preview": preview,
            "error": None,
        })
    except Exception as e:
        logger.exception("Preview failed")
        return jsonify({
            "success": False,
            "preview": None,
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
        graph = data_svc.build_graph(ifc_path, include_rules=include_rules)
        
        # Get summary
        elements = graph.get("elements", {}) or {}
        spaces = elements.get("spaces", []) or []
        doors = elements.get("doors", []) or []
        
        summary = {
            "num_spaces": len(spaces),
            "num_doors": len(doors),
            "spaces_with_area": sum(1 for s in spaces if s.get("area_m2") is not None),
            "doors_with_width": sum(1 for d in doors if d.get("width_mm") is not None),
        }
        
        return jsonify({
            "success": True,
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
                "spaces_with_area": sum(1 for s in spaces if s.get("area_m2") is not None),
                "doors_with_width": sum(1 for d in doors if d.get("width_mm") is not None),
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
    """Evaluate rules against a graph.
    
    Request:
        {
            "graph": dict,
            "include_manifest": bool (optional, default true),
            "include_builtin": bool (optional, default true)
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
        include_manifest = data.get("include_manifest", True)
        include_builtin = data.get("include_builtin", True)
        
        if not graph:
            return jsonify({"success": False, "error": "graph required"}), 400
        
        logger.info("Evaluating rules (manifest=%s, builtin=%s)",
                   include_manifest, include_builtin)
        
        # Save graph to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            temp_graph_file = f.name
        
        try:
            # Run rule engine
            results_file = run_with_graph(
                temp_graph_file,
                include_manifest=include_manifest,
                include_builtin=include_builtin,
            )
            
            # Load results
            with open(results_file, "r", encoding="utf-8") as f:
                results_data = json.load(f)
            
            results = results_data.get("results", [])
            
            # Compute summary
            summary = {
                "total": len(results),
                "passed": sum(1 for r in results if r.get("status") == "PASS"),
                "failed": sum(1 for r in results if r.get("status") == "FAIL"),
                "by_severity": {},
                "by_rule": {},
            }
            
            for result in results:
                severity = result.get("severity", "UNKNOWN")
                summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
                
                rule_id = result.get("rule_id", "UNKNOWN")
                summary["by_rule"][rule_id] = summary["by_rule"].get(rule_id, 0) + 1
            
            return jsonify({
                "success": True,
                "results": results,
                "summary": summary,
                "error": None,
            })
        finally:
            try:
                Path(temp_graph_file).unlink()
            except Exception:
                pass
                
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
        from rule_layer import get_ruleset_metadata
        
        metadata = get_ruleset_metadata()
        rules = metadata.get("rules", [])
        
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


# ===== Health Check =====

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting IFC Explorer API server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
