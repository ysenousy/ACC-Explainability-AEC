# rule_layer/engine.py

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .base import BaseRule
from .models import RuleResult, RuleSeverity, RuleStatus

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    RuleEngine: runs a collection of rules on a data-layer building graph.

    Typical usage:
        engine = RuleEngine([rule1, rule2, ...])
        graph = engine.load_graph("BasicHouse_dataLayer.json")
        results = engine.run(graph)

    Or directly from file:
        results = engine.run_from_file("BasicHouse_dataLayer.json")
    """

    def __init__(
        self,
        rules: Iterable[BaseRule],
        *,
        strict: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._rules: List[BaseRule] = list(rules)
        self._strict = strict
        self._log = logger or logging.getLogger(self.__class__.__name__)

    @staticmethod
    def load_graph(graph_path: str | Path) -> Dict[str, Any]:
        """
        Load a data-layer JSON graph from disk.

        Parameters
        ----------
        graph_path : str | Path
            Path to the *_dataLayer.json file produced by the Data Layer.

        Returns
        -------
        Dict[str, Any]
            Parsed JSON content as a Python dictionary.
        """
        graph_path = Path(graph_path)
        with graph_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_graph(self, graph: Dict[str, Any]) -> None:
        if not isinstance(graph, dict):
            raise TypeError("Graph must be a dictionary produced by the data layer.")
        elements = graph.get("elements")
        if not isinstance(elements, dict):
            raise ValueError("Graph is missing 'elements' section.")
        if "spaces" not in elements:
            self._log.warning("Graph has no 'spaces' collection; some rules may be skipped.")
        if "doors" not in elements:
            self._log.warning("Graph has no 'doors' collection; some rules may be skipped.")

    def run(self, graph: Dict[str, Any]) -> List[RuleResult]:
        """
        Run all configured rules against an in-memory building graph.

        Parameters
        ----------
        graph : Dict[str, Any]
            The canonical building graph from the Data Layer.

        Returns
        -------
        List[RuleResult]
            Flat list of all RuleResult objects from all rules.
        """
        self._validate_graph(graph)

        results: List[RuleResult] = []
        for rule in self._rules:
            try:
                self._log.debug("Evaluating rule %s (%s)", rule.id, rule.name)
                rule_results = rule.evaluate(graph)
                self._log.info("Rule %s produced %d result(s)", rule.id, len(rule_results))
                results.extend(rule_results)
            except Exception as exc:  # pragma: no cover - depends on rule failures
                self._log.exception("Rule %s failed: %s", rule.id, exc)
                if self._strict:
                    raise
                results.append(
                    RuleResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        target_type="rule_engine",
                        target_id="GLOBAL",
                        status=RuleStatus.NOT_APPLICABLE,
                        message=f"Rule '{rule.name}' could not be evaluated: {exc}",
                        severity=RuleSeverity.ERROR,
                        details={"exception": repr(exc)},
                    )
                )
        return results

    def run_from_file(self, graph_path: str | Path) -> List[RuleResult]:
        """
        Convenience method: load graph from file and run all rules.

        Parameters
        ----------
        graph_path : str | Path
            Path to the *_dataLayer.json file.

        Returns
        -------
        List[RuleResult]
            Flat list of all RuleResult objects.
        """
        graph = self.load_graph(graph_path)
        return self.run(graph)
