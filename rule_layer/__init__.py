from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Sequence

from rule_layer.base import BaseRule
from rule_layer.config import RuleConfig, load_rule_config
from rule_layer.rules.doors import MinDoorWidthRule
from rule_layer.rules.spaces import MinSpaceAreaRule
from rule_layer.rules.building import MaxOccupancyPerStoreyRule


def _instantiate_rule(rule_config: Mapping[str, object]) -> Optional[BaseRule]:
    """Instantiate a rule based on its configuration."""
    rule_type = rule_config.get("type")
    rule_id = rule_config.get("id", "unknown")
    enabled = rule_config.get("enabled", True)
    params = rule_config.get("parameters", {})
    
    # Skip disabled rules
    if not enabled:
        return None
    
    try:
        if rule_type == "door":
            return MinDoorWidthRule(
                min_width_mm=float(params.get("min_width_mm", 900.0)),
                severity=rule_config.get("severity", "ERROR"),
                code_reference=rule_config.get("code_reference", "IBC 2018 §1010.1.1"),
            )
        elif rule_type == "space":
            return MinSpaceAreaRule(
                min_area_m2=float(params.get("min_area_m2", 6.0)),
                severity=rule_config.get("severity", "ERROR"),
                code_reference=rule_config.get("code_reference", "IBC 2018 §1204.2"),
            )
        elif rule_type == "building":
            return MaxOccupancyPerStoreyRule(
                max_occupancy=int(params.get("max_occupancy_per_storey", 50)),
                severity=rule_config.get("severity", "WARNING"),
                code_reference=rule_config.get("code_reference", "IBC 2018 §1004"),
            )
        else:
            print(f"Warning: Unknown rule type '{rule_type}' for rule '{rule_id}'")
            return None
    except Exception as e:
        print(f"Error instantiating rule '{rule_id}': {e}")
        return None


def get_all_rules(config: Optional[RuleConfig | Mapping[str, object] | str] = None) -> List[BaseRule]:
    """Instantiate the configured rule objects from configuration file."""
    cfg = load_rule_config(config)
    
    # Build rules from configuration
    rules: List[BaseRule] = []
    
    # If config has explicit rule definitions, use them
    if hasattr(cfg, '_raw_config') and isinstance(cfg._raw_config, dict):
        raw_rules = cfg._raw_config.get("rules", [])
        for rule_config in raw_rules:
            rule = _instantiate_rule(rule_config)
            if rule:
                rules.append(rule)
    else:
        # Fall back to default rule instantiation from RuleConfig
        rules = [
            MinDoorWidthRule(
                min_width_mm=cfg.door.min_width_mm,
                severity=cfg.door.severity,
                code_reference=cfg.door.code_reference,
            ),
            MinSpaceAreaRule(
                min_area_m2=cfg.space.min_area_m2,
                severity=cfg.space.severity,
                code_reference=cfg.space.code_reference,
            ),
            MaxOccupancyPerStoreyRule(
                max_occupancy=cfg.building.max_occupancy_per_storey,
                severity=cfg.building.severity,
                code_reference=cfg.building.code_reference,
            ),
        ]
    
    return rules


def get_ruleset_metadata(config: Optional[RuleConfig | Mapping[str, object] | str] = None) -> dict[str, object]:
    cfg = load_rule_config(config)
    return {
        "ruleset_id": cfg.ruleset_id,
        "rules": [rule.describe() for rule in get_all_rules(cfg)],
    }


__all__ = [
    "BaseRule",
    "RuleConfig",
    "get_all_rules",
    "get_ruleset_metadata",
    "load_rule_config",
]
