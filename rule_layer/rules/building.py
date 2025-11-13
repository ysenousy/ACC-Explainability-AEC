# rule_layer/rules/building.py
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Sequence

from rule_layer.base import BaseRule
from rule_layer.models import RuleResult, RuleSeverity, RuleStatus


class MaxOccupancyPerStoreyRule(BaseRule):
    id = "R3_MAX_OCCUPANCY_PER_STOREY"
    name = "Maximum occupancy per storey"

    def __init__(
        self,
        max_occupancy: int = 50,
        *,
        severity: RuleSeverity = RuleSeverity.WARNING,
        code_reference: str | None = None,
    ) -> None:
        self.max_occupancy = int(max_occupancy)
        self.severity = severity if isinstance(severity, RuleSeverity) else RuleSeverity(str(severity))
        self.code_reference = code_reference or "IBC 2018 §1004"

    def evaluate(self, graph: Dict[str, Any]) -> List[RuleResult]:
        results: List[RuleResult] = []
        spaces: Sequence[Dict[str, Any]] = graph.get("elements", {}).get("spaces", []) or []

        # For now, assume each space has "attributes" with an "occupancy" value
        occupancy_by_storey: Dict[str, int] = defaultdict(int)
        spaces_with_unknown_occupancy: Dict[str, List[str]] = defaultdict(list)

        for space in spaces:
            storey_name = space.get("storey_name") or space.get("storey") or "UNKNOWN_STOREY"
            attrs = space.get("attributes", {})
            psets = attrs.get("property_sets", {})
            occ = None

            # Example: look for an "Occupancy" value in some pset
            for pset_name, props in psets.items():
                if "Occupancy" in props:
                    occ = props["Occupancy"]
                    break

            if isinstance(occ, (int, float)):
                occupancy_by_storey[storey_name] += int(occ)
            else:
                spaces_with_unknown_occupancy[storey_name].append(space.get("id") or space.get("name") or "UNKNOWN_SPACE")

        # Evaluate per storey
        for storey_name, total_occ in occupancy_by_storey.items():
            if total_occ <= self.max_occupancy:
                status = RuleStatus.PASS
                msg = (
                    f"Storey '{storey_name}' occupancy {total_occ} "
                    f"≤ maximum allowed {self.max_occupancy}."
                )
                severity = RuleSeverity.INFO if self.severity == RuleSeverity.ERROR else self.severity
            else:
                status = RuleStatus.FAIL
                msg = (
                    f"Storey '{storey_name}' occupancy {total_occ} "
                    f"> maximum allowed {self.max_occupancy}."
                )
                severity = self.severity

            results.append(
                RuleResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    target_type="storey",
                    target_id=storey_name,
                    status=status,
                    message=msg,
                    severity=severity,
                    code_reference=self.code_reference,
                    details={
                        "occupancy": total_occ,
                        "max_occupancy": self.max_occupancy,
                        "spaces_missing_occupancy": spaces_with_unknown_occupancy.get(storey_name, []),
                    },
                )
            )

        # Emit NOT_APPLICABLE results for storeys with no measurable occupancy
        known_storeys = set(occupancy_by_storey.keys())
        for storey_name, missing_space_ids in spaces_with_unknown_occupancy.items():
            if storey_name in known_storeys:
                continue
            results.append(
                RuleResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    target_type="storey",
                    target_id=storey_name,
                    status=RuleStatus.NOT_APPLICABLE,
                    message=(
                        f"Storey '{storey_name}' has no occupancy data; "
                        "cannot evaluate maximum occupancy requirement."
                    ),
                    severity=RuleSeverity.WARNING,
                    code_reference=self.code_reference,
                    details={
                        "spaces_missing_occupancy": missing_space_ids,
                        "max_occupancy": self.max_occupancy,
                    },
                )
            )

        return results
