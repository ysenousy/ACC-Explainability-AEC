# rule_layer/models.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional


class RuleStatus(str, Enum):
    """Outcome of applying a rule to a target element."""
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleSeverity(str, Enum):
    """How critical a rule violation is."""
    INFO = "INFO"         # e.g. suggestions, best practice
    WARNING = "WARNING"   # e.g. recommended, non-critical
    ERROR = "ERROR"       # e.g. code violation / non-compliance


@dataclass(slots=True)
class RuleResult:
    """
    Result of evaluating a single rule on a single target element.

    This is the core payload that the Explainability Layer will consume.
    """
    rule_id: str                  # e.g. "R1_MIN_DOOR_WIDTH"
    rule_name: str                # human-readable name of the rule
    target_type: str              # "door", "space", "building", etc.
    target_id: str                # element id / guid, or "BUILDING" for global rules
    status: RuleStatus            # PASS / FAIL / NOT_APPLICABLE
    message: str                  # short human-readable explanation

    # Optional metadata for trust & traceability
    severity: RuleSeverity = RuleSeverity.ERROR
    code_reference: Optional[str] = None   # e.g. "IBC 2018 §1010.1.1"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a JSON-serialisable dict.
        (Enums become their string values.)
        """
        data = asdict(self)
        data["status"] = self.status.value
        data["severity"] = self.severity.value
        return data


__all__ = ["RuleStatus", "RuleSeverity", "RuleResult"]