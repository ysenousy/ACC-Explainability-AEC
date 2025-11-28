"""Convert Unified Rule Config format to Regulatory Rules format for compliance checking."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def convert_unified_config_to_regulatory_format(unified_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert Rule Config mappings to Regulatory Rules format.
    Mappings act as bridges that link IFC elements to catalogue rules.
    Rule properties (severity, description, etc.) come from the catalogue, not the mapping.
    
    Args:
        unified_config: Dict containing rule_mappings from unified_rules_mapping.json
    
    Returns:
        List of rules in regulatory format
    """
    converted_rules = []
    
    # Load the catalogue to get original rule data
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    catalogue_path = project_root / "rules_config" / "enhanced-regulation-rules.json"
    
    catalogue_rules = {}
    try:
        with open(catalogue_path, 'r') as f:
            catalogue_data = json.load(f)
            for rule in catalogue_data.get("rules", []):
                catalogue_rules[rule.get("id")] = rule
    except Exception as e:
        logger.warning(f"Could not load catalogue rules from {catalogue_path}: {e}")
    
    rule_mappings = unified_config.get("rule_mappings", [])
    ifc_mappings = unified_config.get("ifc_element_mappings", {})
    
    for mapping in rule_mappings:
        try:
            # Skip disabled mappings
            if not mapping.get("enabled", True):
                logger.debug(f"Skipping disabled mapping: {mapping.get('mapping_id')}")
                continue
            
            # Extract base information
            mapping_id = mapping.get("mapping_id")
            element_type = mapping.get("element_type")
            
            if not mapping_id or not element_type:
                logger.warning(f"Skipping mapping with missing mapping_id or element_type")
                continue
            
            # Get rule reference from mapping
            rule_ref = mapping.get("rule_reference", {})
            rule_id = rule_ref.get("rule_id", mapping_id)
            
            # Get catalogue rule to use its original properties
            catalogue_rule = catalogue_rules.get(rule_id, {})
            
            # Build regulatory format rule
            # Use mapping data only for IFC extraction logic
            # Use catalogue data for severity, description, parameters, etc.
            regulatory_rule = {
                "id": rule_id,
                "name": catalogue_rule.get("name", mapping.get("explanation", {}).get("short", rule_id)),
                "rule_type": catalogue_rule.get("rule_type", "attribute_comparison"),
                "description": catalogue_rule.get("description", mapping.get("explanation", {}).get("short", "")),
                
                # Target: IFC class for this element type (from mapping's extraction logic)
                "target": _build_target(element_type, mapping, ifc_mappings),
                
                # Condition: comparison logic (from mapping's extraction logic)
                "condition": _build_condition(mapping),
                
                # Parameters with default values (from mapping's parameter bindings)
                "parameters": _build_parameters(mapping),
                
                # Severity level - comes from CATALOGUE, not mapping
                "severity": catalogue_rule.get("severity", "ERROR").upper(),
                
                # Explanation messages - use mapping's explanations if available, fall back to catalogue
                "explanation": {
                    "short": mapping.get("explanation", {}).get("short", catalogue_rule.get("explanation", {}).get("short", "")),
                    "on_fail": mapping.get("explanation", {}).get("on_fail", catalogue_rule.get("explanation", {}).get("on_fail", "")),
                    "on_pass": mapping.get("explanation", {}).get("on_pass", catalogue_rule.get("explanation", {}).get("on_pass", "")),
                },
                
                # Provenance - use catalogue's provenance (it's the source of truth)
                "provenance": catalogue_rule.get("provenance", {
                    "source": mapping.get("provenance", {}).get("source", "configuration"),
                    "regulation": mapping.get("provenance", {}).get("regulation", ""),
                    "section": mapping.get("provenance", {}).get("section", ""),
                    "title": mapping.get("provenance", {}).get("title", ""),
                    "jurisdiction": mapping.get("provenance", {}).get("jurisdiction", ""),
                    "jurisdiction_scope": mapping.get("provenance", {}).get("jurisdiction_scope", []),
                }),
            }
            
            converted_rules.append(regulatory_rule)
            logger.debug(f"Converted mapping {mapping_id} to rule {rule_id} (severity: {regulatory_rule['severity']})")
            
        except Exception as e:
            logger.error(f"Error converting mapping {mapping.get('mapping_id')}: {e}")
            continue
    
    logger.info(f"Converted {len(converted_rules)} rule mappings to regulatory format")
    return converted_rules


def _build_target(element_type: str, mapping: Dict[str, Any], ifc_mappings: Dict[str, Any]) -> Dict[str, Any]:
    """Build target object for regulatory rule."""
    
    # Get IFC class from element mappings
    element_config = ifc_mappings.get(element_type, {})
    ifc_class = element_config.get("ifc_class", f"Ifc{element_type.capitalize()}")
    
    # Build selector from element filters
    element_filter = mapping.get("element_filter", {})
    filters = element_filter.get("filters", [])
    
    selector_filters = []
    for f in filters:
        selector_filters.append({
            "pset": f.get("pset_name") or f.get("pset", ""),
            "property": f.get("property_name") or f.get("property", ""),
            "op": f.get("operator", "="),
            "value": f.get("value"),
        })
    
    return {
        "ifc_class": ifc_class,
        "selector": {
            "filters": selector_filters
        } if selector_filters else {}
    }


def _build_condition(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Build condition object for regulatory rule."""
    
    attr_extraction = mapping.get("attribute_extraction", {})
    
    lhs = attr_extraction.get("lhs", {})
    operator = attr_extraction.get("operator", ">=")
    rhs = attr_extraction.get("rhs", {})
    
    return {
        "op": operator,
        "lhs": {
            "source": lhs.get("source", "ifc"),
            "qto_name": lhs.get("qto_name", ""),
            "quantity": lhs.get("quantity_name", lhs.get("quantity", "")),
            "unit": lhs.get("unit", "mm"),
            "attribute": lhs.get("attribute", ""),
        },
        "rhs": {
            "source": rhs.get("source", "parameter"),
            "param": rhs.get("parameter", ""),
            "value": rhs.get("value"),
        }
    }


def _build_parameters(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters dict with default values from parameter_bindings."""
    
    parameters = {}
    param_bindings = mapping.get("parameter_bindings", {})
    
    for param_name, param_config in param_bindings.items():
        default_value = param_config.get("default_value")
        if default_value is not None:
            parameters[param_name] = default_value
    
    return parameters


def save_converted_rules_to_custom_rules(rules: List[Dict[str, Any]], output_path: Optional[Path] = None) -> bool:
    """
    Save converted rules to custom_rules.json.
    
    Args:
        rules: List of rules in regulatory format
        output_path: Optional path to save to (default: rules_config/custom_rules.json)
    
    Returns:
        bool: Success status
    """
    try:
        if output_path is None:
            backend_dir = Path(__file__).parent
            project_root = backend_dir.parent
            output_path = project_root / "rules_config" / "custom_rules.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        payload = {
            "rules": rules,
            "saved_at": datetime.utcnow().isoformat(),
            "version": 1,
            "source": "rule_config_converter",
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(rules)} converted rules to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save converted rules: {e}")
        return False


def convert_and_save_rule_config(unified_config: Dict[str, Any], output_path: Optional[Path] = None) -> bool:
    """
    Convert Rule Config and save as custom_rules.json in one step.
    
    Args:
        unified_config: Rule Config dict
        output_path: Optional custom output path
    
    Returns:
        bool: Success status
    """
    try:
        # Convert
        rules = convert_unified_config_to_regulatory_format(unified_config)
        
        if not rules:
            logger.warning("No rules generated from Rule Config")
            return False
        
        # Save
        success = save_converted_rules_to_custom_rules(rules, output_path)
        
        if success:
            logger.info(f"Successfully prepared Rule Config for compliance checking ({len(rules)} rules)")
        
        return success
        
    except Exception as e:
        logger.error(f"Error converting and saving Rule Config: {e}")
        return False
