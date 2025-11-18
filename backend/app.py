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
from backend.analyze_rules import analyze_ifc_rules
from backend.rule_config_manager import (
    load_custom_rules,
    save_custom_rules,
    add_rule,
    delete_rule,
    get_all_rules,
    import_rules,
    export_rules,
)

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

        # Clear the rules catalogue when loading a new IFC file
        # This ensures a fresh start for each IFC file
        save_custom_rules([])
        logger.info("Rules catalogue cleared for new IFC file upload")

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
        
        # Call import_rules
        status = import_rules(rules_to_import, merge=merge)
        
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
                
                strategies_info[strategy_name] = {
                    "available": len(strategy_rules) > 0,
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
