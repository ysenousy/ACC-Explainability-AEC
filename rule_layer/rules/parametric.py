from __future__ import annotations

from typing import Any, Dict, List, Optional

from rule_layer.base import BaseRule
from rule_layer.models import RuleResult, RuleSeverity, RuleStatus


OP_MAP = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


class ParametricRule(BaseRule):
    """A simple rule wrapper that evaluates a manifest entry.

    The extractor emits manifest entries with a conservative shape. This
    rule interprets the `condition` as a predicate that -- when true --
    indicates a violation (i.e. the rule should report FAIL). This
    mirrors the extractor semantics where e.g. `width_mm < min_width_mm`
    indicates a problem.
    """

    id = "R_PARAMETRIC"
    name = "Parametric manifest-driven rule"

    def __init__(self, manifest_entry: Dict[str, Any]):
        self.entry = manifest_entry
        self.id = manifest_entry.get("id")
        self.name = manifest_entry.get("name") or self.id
        self.target_type = manifest_entry.get("target_type")
        self.selector = manifest_entry.get("selector", {})
        self.condition = manifest_entry.get("condition", {})
        self.parameters = manifest_entry.get("parameters", {})
        self.severity = RuleSeverity(manifest_entry.get("severity", "ERROR"))
        self.code_reference = manifest_entry.get("code_reference")
        # Polarity: 'violation' means condition true => FAIL; 'predicate' means condition true => PASS
        self.polarity = manifest_entry.get("polarity", "violation")
        self.confidence = manifest_entry.get("confidence", "medium")

    @classmethod
    def from_manifest(cls, manifest_entry: Dict[str, Any]) -> "ParametricRule":
        return cls(manifest_entry)

    def _resolve_lhs(self, lhs: Dict[str, Any], target: Dict[str, Any], graph: Dict[str, Any]) -> Optional[float]:
        # attr form: {"attr": "width_mm"}
        if "attr" in lhs:
            return target.get(lhs["attr"])  # may be None or numeric
        # expr form: support a few built-in expressions
        if "expr" in lhs:
            expr = lhs["expr"]
            if expr == "sum_spaces_occupancy":
                # compute occupancy per storey; return mapping as special case
                spaces = graph.get("elements", {}).get("spaces", []) or []
                occ_by_storey = {}
                for s in spaces:
                    storey = s.get("storey_name") or s.get("storey") or "UNKNOWN_STOREY"
                    occ = None
                    attrs = s.get("attributes", {})
                    psets = attrs.get("property_sets", {})
                    for pset_name, props in psets.items():
                        if "occupancy" in props:
                            try:
                                occ = int(props["occupancy"]) if isinstance(props["occupancy"], (int, float)) else int(float(props["occupancy"]))
                            except Exception:
                                occ = None
                            break
                    if isinstance(occ, int):
                        occ_by_storey.setdefault(storey, 0)
                        occ_by_storey[storey] += occ
                return occ_by_storey  # caller must handle dict case
        return None

    def _select_targets(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply selector to find target elements from graph.
        
        Supports:
        - by: "type" => selector.value is element type (door, space, etc.)
        - by: "id" => selector.value is specific element id
        - by: "attribute" => selector.value is attribute name; match targets with that attr set
        """
        sel = self.selector or {}
        by = sel.get("by")
        val = sel.get("value")
        targets = []
        
        if by == "type":
            key = None
            if val == "door":
                key = "doors"
            elif val == "space":
                key = "spaces"
            elif val == "building":
                key = None
            elif val:
                # generalized: treat val as element type and look for corresponding pluralized key
                key = f"{val}s" if not val.endswith("s") else val
            if key:
                targets = graph.get("elements", {}).get(key, []) or []
        
        elif by == "id":
            # Find specific element by id
            for etype, elist in graph.get("elements", {}).items():
                for el in (elist or []):
                    if el.get("id") == val or el.get("ifc_guid") == val or el.get("guid") == val:
                        targets.append(el)
        
        elif by == "attribute":
            # Find all targets that have a specific attribute set
            for etype, elist in graph.get("elements", {}).items():
                for el in (elist or []):
                    if val in el:
                        targets.append(el)
        
        return targets

    def evaluate(self, graph: Dict[str, Any]) -> List[RuleResult]:
        results: List[RuleResult] = []
        
        # Select targets once (batch optimization)
        targets = self._select_targets(graph)
        
        cond = self.condition or {}
        op = cond.get("op")
        lhs = cond.get("lhs") or {}
        rhs = cond.get("rhs") or {}
        
        comparator = OP_MAP.get(op)
        
        # Building-level special case: if lhs expr yields a mapping per storey,
        # produce a result per storey (similar to MaxOccupancyPerStoreyRule).
        for t in (targets if targets else [None]):
            # For building rules t is None and we compute storey aggregates
            current_lhs = self._resolve_lhs(lhs, t or {}, graph)

            # RHS param resolution
            if "param" in rhs:
                rhs_val = self.parameters.get(rhs["param"])
            else:
                rhs_val = rhs.get("value")

            if isinstance(current_lhs, dict):
                # Per-storey occupancy mapping
                for storey_name, occ in current_lhs.items():
                    if occ is None:
                        status = RuleStatus.NOT_APPLICABLE
                        msg = f"Storey '{storey_name}' has no occupancy data; cannot evaluate {self.name}."
                        severity = RuleSeverity.WARNING
                    else:
                        try:
                            if comparator is None or rhs_val is None:
                                status = RuleStatus.NOT_APPLICABLE
                                msg = f"Rule {self.id} missing comparator or parameter."
                                severity = RuleSeverity.WARNING
                            else:
                                violated = comparator(occ, float(rhs_val))
                                # Apply polarity
                                if self.polarity == "predicate":
                                    # condition true => PASS
                                    status = RuleStatus.PASS if violated else RuleStatus.FAIL
                                    msg = f"Storey '{storey_name}' occupancy {occ} {'meets' if violated else 'violates'} {self.name}."
                                else:
                                    # violation: condition true => FAIL
                                    status = RuleStatus.FAIL if violated else RuleStatus.PASS
                                    msg = f"Storey '{storey_name}' occupancy {occ} {'violates' if violated else 'meets'} {self.name}."
                                severity = self.severity if status == RuleStatus.FAIL else (RuleSeverity.INFO if self.severity == RuleSeverity.ERROR else self.severity)
                        except Exception:
                            status = RuleStatus.NOT_APPLICABLE
                            msg = f"Could not evaluate rule {self.id} for storey {storey_name}."
                            severity = RuleSeverity.WARNING

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
                            details={"occupancy": occ, "param": rhs_val, "confidence": self.confidence},
                        )
                    )
                continue

            # Regular scalar cases: evaluate each target individually
            target = t
            target_id = None
            if target:
                target_id = target.get("id") or target.get("ifc_guid") or target.get("guid") or "UNKNOWN"
                lhs_val = self._resolve_lhs(lhs, target, graph)
            else:
                target_id = "BUILDING"
                lhs_val = self._resolve_lhs(lhs, {}, graph)

            if lhs_val is None:
                status = RuleStatus.NOT_APPLICABLE
                msg = f"Target '{target_id}' missing lhs value for {self.name}; cannot evaluate."
                severity = RuleSeverity.WARNING
            else:
                try:
                    if comparator is None or rhs_val is None:
                        status = RuleStatus.NOT_APPLICABLE
                        msg = f"Rule {self.id} missing comparator or parameter."
                        severity = RuleSeverity.WARNING
                    else:
                        violated = comparator(float(lhs_val), float(rhs_val))
                        # Apply polarity
                        if self.polarity == "predicate":
                            # condition true => PASS
                            status = RuleStatus.PASS if violated else RuleStatus.FAIL
                            msg = f"Target '{target_id}' {'meets' if violated else 'violates'} {self.name}."
                        else:
                            # violation: condition true => FAIL
                            status = RuleStatus.FAIL if violated else RuleStatus.PASS
                            msg = f"Target '{target_id}' {'violates' if violated else 'meets'} {self.name}."
                        severity = self.severity if status == RuleStatus.FAIL else (RuleSeverity.INFO if self.severity == RuleSeverity.ERROR else self.severity)
                except Exception:
                    status = RuleStatus.NOT_APPLICABLE
                    msg = f"Could not evaluate rule {self.id} for target {target_id}."
                    severity = RuleSeverity.WARNING

            results.append(
                RuleResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    target_type=self.target_type or (self.selector.get("value") or "unknown"),
                    target_id=target_id,
                    status=status,
                    message=msg,
                    severity=severity,
                    code_reference=self.code_reference,
                    details={"lhs": lhs_val, "rhs": rhs_val, "parameters": self.parameters, "confidence": self.confidence},
                )
            )

        return results


__all__ = ["ParametricRule"]
