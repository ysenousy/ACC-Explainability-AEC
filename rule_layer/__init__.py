from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Sequence

from rule_layer.base import BaseRule
from rule_layer.config import RuleConfig, load_rule_config
from rule_layer.rules.doors import MinDoorWidthRule
from rule_layer.rules.spaces import MinSpaceAreaRule
from rule_layer.rules.building import MaxOccupancyPerStoreyRule


def get_all_rules(config: Optional[RuleConfig | Mapping[str, object] | str] = None) -> List[BaseRule]:
    """Instantiate the configured rule objects."""
    cfg = load_rule_config(config)

    rules: List[BaseRule] = [
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
