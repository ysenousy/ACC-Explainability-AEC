# rule_layer/rules/spaces.py
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from rule_layer.base import BaseRule
from rule_layer.models import RuleResult, RuleSeverity, RuleStatus


class MinSpaceAreaRule(BaseRule):
    id = "R2_MIN_SPACE_AREA"
    name = "Minimum space area requirement"

    def __init__(
        self,
        min_area_m2: float = 6.0,
        *,
        severity: RuleSeverity = RuleSeverity.ERROR,
        code_reference: str | None = None,
    ) -> None:
        self.min_area_m2 = float(min_area_m2)
        self.severity = severity if isinstance(severity, RuleSeverity) else RuleSeverity(str(severity))
        self.code_reference = code_reference or "IBC 2018 §1204.2"

    def evaluate(self, graph: Dict[str, Any]) -> List[RuleResult]:
        results: List[RuleResult] = []
        spaces: Sequence[Dict[str, Any]] = graph.get("elements", {}).get("spaces", []) or []

        for space in spaces:
            space_id = space.get("id") or space.get("ifc_guid") or "UNKNOWN"
            name = space.get("name") or space_id
            area = space.get("area_m2")
            storey = space.get("storey_name") or space.get("storey") or "UNKNOWN_STOREY"

            if area is None:
                status = RuleStatus.NOT_APPLICABLE
                msg = (
                    f"Space '{name}' ({space_id}) has no area; "
                    f"cannot verify minimum {self.min_area_m2:.1f} m²."
                )
                severity = RuleSeverity.WARNING
            elif float(area) >= self.min_area_m2:
                status = RuleStatus.PASS
                msg = (
                    f"Space '{name}' ({space_id}) area {area:.2f} m² "
                    f"meets minimum {self.min_area_m2:.2f} m²."
                )
                severity = RuleSeverity.INFO if self.severity == RuleSeverity.ERROR else self.severity
            else:
                status = RuleStatus.FAIL
                msg = (
                    f"Space '{name}' ({space_id}) area {area:.2f} m² "
                    f"is less than required {self.min_area_m2:.2f} m²."
                )
                severity = self.severity

            results.append(
                RuleResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    target_type="space",
                    target_id=str(space_id),
                    status=status,
                    message=msg,
                    severity=severity,
                    code_reference=self.code_reference,
                    details={
                        "area_m2": area,
                        "min_required_area_m2": self.min_area_m2,
                        "space_name": name,
                        "storey": storey,
                    },
                )
            )

        return results
