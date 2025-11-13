# rule_layer/io.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import RuleResult, RuleStatus

logger = logging.getLogger(__name__)


def _summarise_by_rule(results: List[RuleResult]) -> Dict[str, Dict[str, Any]]:
    """
    Compute a simple summary per rule_id:
      { "R1": {"rule_name": "...", "PASS": n, "FAIL": n, "NOT_APPLICABLE": n}, ... }
    """
    summary: Dict[str, Dict[str, Any]] = {}

    for r in results:
        rule_entry = summary.setdefault(
            r.rule_id,
            {
                "rule_name": r.rule_name,
                RuleStatus.PASS.value: 0,
                RuleStatus.FAIL.value: 0,
                RuleStatus.NOT_APPLICABLE.value: 0,
            },
        )
        rule_entry[r.status.value] += 1

    return summary


def _load_graph_metadata(graph_path: Path) -> Dict[str, Any]:
    try:
        with graph_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:  # pragma: no cover - depends on filesystem
        logger.warning("Could not read graph metadata from %s: %s", graph_path, exc)
    return {}


def save_results(
    results: List[RuleResult],
    graph_path: str | Path,
    out_path: Optional[str | Path] = None,
    ruleset_id: str = "default_ruleset_v1",
    *,
    graph_metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Save rule evaluation results to a JSON file.

    Parameters
    ----------
    results : List[RuleResult]
        All rule results produced by the RuleEngine.
    graph_path : str | Path
        Path to the *_dataLayer.json file used as input.
    out_path : Optional[str | Path]
        Optional custom output path. If None, a default
        "<graph_stem>_rules.json" is used next to the graph.
    ruleset_id : str
        Identifier for the active ruleset (for traceability).
    graph_metadata : Optional[Dict[str, Any]]
        Optional in-memory graph payload to avoid re-reading the JSON file.

    Returns
    -------
    Path
        The path of the JSON file that was written.
    """
    graph_path = Path(graph_path)

    if out_path is None:
        # If graph is "BasicHouse_dataLayer.json" → "BasicHouse_dataLayer_rules.json"
        out_path = graph_path.with_name(f"{graph_path.stem}_rules.json")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = _summarise_by_rule(results)

    metadata = graph_metadata or _load_graph_metadata(graph_path)
    building_id = metadata.get("building_id") or graph_path.stem.replace("_dataLayer", "")

    payload: Dict[str, Any] = {
        "building_id": building_id,
        "graph_file": str(graph_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ruleset_id": ruleset_id,
        "summary": summary,
        "results": [r.to_dict() for r in results],
    }

    if metadata:
        payload["graph_meta"] = {
            "schema": metadata.get("meta", {}).get("schema"),
            "coverage": metadata.get("meta", {}).get("coverage"),
        }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def load_results(results_path: str | Path) -> Dict[str, Any]:
    """
    Load a rule-layer results JSON file.

    Returns the raw dict payload, which includes:
      - building_id
      - graph_file
      - generated_at
      - ruleset_id
      - summary
      - results (list of dicts)
    """
    results_path = Path(results_path)
    with results_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_all_rule_entries(results_path: str | Path) -> List[Dict[str, Any]]:
    """
    Convenience helper: load a results JSON and return just the
    list of rule result entries (as plain dicts).

    This is useful if you want to analyse all rule applications,
    build dataframes, etc.
    """
    payload = load_results(results_path)
    results = payload.get("results", [])
    if not isinstance(results, list):
        return []
    return results
