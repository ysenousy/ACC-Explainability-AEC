from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rule_layer import get_all_rules, get_ruleset_metadata, load_rule_config  # noqa: E402
from rule_layer.engine import RuleEngine  # noqa: E402
from rule_layer.io import save_results  # noqa: E402


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s - %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rule layer checks against a data-layer JSON graph.")
    parser.add_argument(
        "--graph",
        default=str(PROJECT_ROOT / "acc-dataset" / "IFC" / "BasicHouse_dataLayer.json"),
        help="Path to the data-layer JSON file.",
    )
    parser.add_argument(
        "--out",
        help="Optional output path for the rules JSON. Defaults to <graph>_rules.json",
    )
    parser.add_argument(
        "--config",
        help="Optional path to a rule configuration JSON file. "
             "Overrides RULE_LAYER_CONFIG environment variable when provided.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Raise exceptions when a rule fails instead of recording NOT_APPLICABLE.",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("RULE_LAYER_LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    args = parser.parse_args()

    _configure_logging(args.log_level)
    log = logging.getLogger("rule_layer.run")

    graph_path = Path(args.graph).resolve()
    if not graph_path.exists():
        raise FileNotFoundError(f"Data-layer JSON not found: {graph_path}")

    cfg = load_rule_config(args.config)
    rules = get_all_rules(cfg)
    engine = RuleEngine(rules, strict=args.strict, logger=log)

    graph = engine.load_graph(graph_path)
    results = engine.run(graph)

    ruleset_meta = get_ruleset_metadata(cfg)

    out_file = save_results(
        results,
        graph_path,
        out_path=args.out,
        ruleset_id=ruleset_meta["ruleset_id"],
        graph_metadata=graph,
    )

    print(json.dumps({
        "ruleset_id": ruleset_meta["ruleset_id"],
        "results_file": str(out_file),
        "num_results": len(results),
    }, indent=2))


if __name__ == "__main__":
    main()
