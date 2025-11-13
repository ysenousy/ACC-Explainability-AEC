# rule_layer/rules/doors.py
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from rule_layer.base import BaseRule
from rule_layer.models import RuleResult, RuleSeverity, RuleStatus


class MinDoorWidthRule(BaseRule):
    id = "R1_MIN_DOOR_WIDTH"
    name = "Minimum door width requirement"

    def __init__(
        self,
        min_width_mm: float = 900.0,
        *,
        severity: RuleSeverity = RuleSeverity.ERROR,
        code_reference: str | None = None,
    ) -> None:
        self.min_width_mm = float(min_width_mm)
        self.severity = severity if isinstance(severity, RuleSeverity) else RuleSeverity(str(severity))
        self.code_reference = code_reference or "IBC 2018 §1010.1.1"

    def evaluate(self, graph: Dict[str, Any]) -> List[RuleResult]:
        results: List[RuleResult] = []
        doors: Sequence[Dict[str, Any]] = graph.get("elements", {}).get("doors", []) or []

        for door in doors:
            door_id = door.get("id") or door.get("ifc_guid") or "UNKNOWN"
            width = door.get("width_mm")
            name = door.get("name") or door_id
            connected_spaces = door.get("connected_spaces") or []
            connected_space_ids = [c.get("space_id") for c in connected_spaces if isinstance(c, dict)]

            if width is None:
                status = RuleStatus.NOT_APPLICABLE
                msg = (
                    f"Door '{name}' ({door_id}) has no width information; "
                    f"cannot verify minimum {self.min_width_mm:.1f} mm."
                )
                severity = RuleSeverity.WARNING
            elif float(width) >= self.min_width_mm:
                status = RuleStatus.PASS
                msg = (
                    f"Door '{name}' ({door_id}) width {width:.1f} mm "
                    f"meets minimum requirement {self.min_width_mm:.1f} mm."
                )
                severity = RuleSeverity.INFO if self.severity == RuleSeverity.ERROR else self.severity
            else:
                status = RuleStatus.FAIL
                msg = (
                    f"Door '{name}' ({door_id}) width {width:.1f} mm "
                    f"is less than required {self.min_width_mm:.1f} mm."
                )
                severity = self.severity

            results.append(
                RuleResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    target_type="door",
                    target_id=str(door_id),
                    status=status,
                    message=msg,
                    severity=severity,
                    code_reference=self.code_reference,
                    details={
                        "width_mm": width,
                        "min_required_width_mm": self.min_width_mm,
                        "door_name": name,
                        "connected_space_ids": connected_space_ids,
                    },
                )
            )

        return results
