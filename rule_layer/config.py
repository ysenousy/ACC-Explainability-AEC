"""Configuration utilities for the rule layer."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from .models import RuleSeverity


def _coerce_severity(value: Any, default: RuleSeverity) -> RuleSeverity:
    if isinstance(value, RuleSeverity):
        return value
    if isinstance(value, str):
        try:
            return RuleSeverity[value.upper()]
        except KeyError:
            try:
                return RuleSeverity(value.upper())
            except ValueError:
                pass
    return default


@dataclass
class DoorRuleConfig:
    min_width_mm: float = 900.0
    severity: RuleSeverity = RuleSeverity.ERROR
    code_reference: str = "IBC 2018 §1010.1.1"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DoorRuleConfig":
        default = cls()
        return cls(
            min_width_mm=float(data.get("min_width_mm", default.min_width_mm)),
            severity=_coerce_severity(data.get("severity"), default.severity),
            code_reference=str(data.get("code_reference", default.code_reference)),
        )


@dataclass
class SpaceRuleConfig:
    min_area_m2: float = 6.0
    severity: RuleSeverity = RuleSeverity.ERROR
    code_reference: str = "IBC 2018 §1204.2"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SpaceRuleConfig":
        default = cls()
        return cls(
            min_area_m2=float(data.get("min_area_m2", default.min_area_m2)),
            severity=_coerce_severity(data.get("severity"), default.severity),
            code_reference=str(data.get("code_reference", default.code_reference)),
        )


@dataclass
class BuildingRuleConfig:
    max_occupancy_per_storey: int = 50
    severity: RuleSeverity = RuleSeverity.WARNING
    code_reference: str = "IBC 2018 §1004"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "BuildingRuleConfig":
        default = cls()
        return cls(
            max_occupancy_per_storey=int(data.get("max_occupancy_per_storey", default.max_occupancy_per_storey)),
            severity=_coerce_severity(data.get("severity"), default.severity),
            code_reference=str(data.get("code_reference", default.code_reference)),
        )


@dataclass
class RuleConfig:
    door: DoorRuleConfig = field(default_factory=DoorRuleConfig)
    space: SpaceRuleConfig = field(default_factory=SpaceRuleConfig)
    building: BuildingRuleConfig = field(default_factory=BuildingRuleConfig)
    ruleset_id: str = "default_ruleset_v1"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RuleConfig":
        return cls(
            door=DoorRuleConfig.from_mapping(data.get("door", {})),
            space=SpaceRuleConfig.from_mapping(data.get("space", {})),
            building=BuildingRuleConfig.from_mapping(data.get("building", {})),
            ruleset_id=str(data.get("ruleset_id", cls.ruleset_id)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "door": {
                "min_width_mm": self.door.min_width_mm,
                "severity": self.door.severity.value,
                "code_reference": self.door.code_reference,
            },
            "space": {
                "min_area_m2": self.space.min_area_m2,
                "severity": self.space.severity.value,
                "code_reference": self.space.code_reference,
            },
            "building": {
                "max_occupancy_per_storey": self.building.max_occupancy_per_storey,
                "severity": self.building.severity.value,
                "code_reference": self.building.code_reference,
            },
            "ruleset_id": self.ruleset_id,
        }


def load_rule_config(source: Optional[str | Path | Mapping[str, Any]] = None) -> RuleConfig:
    """
    Load rule configuration from a JSON file, mapping, or environment variable.

    If `source` is None, looks for `RULE_LAYER_CONFIG` environment variable,
    falling back to defaults defined in `RuleConfig`.
    """
    if isinstance(source, RuleConfig):
        return source

    if source is None:
        env_path = os.environ.get("RULE_LAYER_CONFIG")
        if env_path:
            source = Path(env_path)
        else:
            return RuleConfig()

    if isinstance(source, Mapping):
        return RuleConfig.from_mapping(source)

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Rule config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, Mapping):
        raise ValueError("Rule config file must contain a JSON object at the top level.")

    return RuleConfig.from_mapping(data)


__all__ = [
    "DoorRuleConfig",
    "SpaceRuleConfig",
    "BuildingRuleConfig",
    "RuleConfig",
    "load_rule_config",
]

