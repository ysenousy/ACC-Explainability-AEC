# data_layer/preview_ifc.py
from __future__ import annotations

import sys
from pathlib import Path

# --- Make sure project root is importable when run directly (VS Code Run) ---
ROOT = Path(__file__).resolve().parents[1]   # project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import logging

# --- Import service layer (works as script OR module) ---
try:
    from data_layer.services import DataLayerService
except Exception:
    from .services import DataLayerService

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Preview IFC metadata and element counts.")
    ap.add_argument("--ifc", default=r"acc-dataset/IFC/AC20-FZK-Haus.ifc", help="Path to the IFC file to preview")
    ap.add_argument("--summary", help="Optional path to write the preview summary JSON")
    ap.add_argument("--export-rules", action="store_true", help="Extract rules from the IFC and write rules_manifest JSON")
    ap.add_argument("--rules-out", help="Optional path to write extracted rules manifest JSON")
    ap.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s %(name)s - %(message)s",
    )

    service = DataLayerService(logging.getLogger("data_layer.preview"))

    ifc_path = Path(args.ifc)
    if args.summary:
        summary_path = Path(args.summary)
    else:
        out_dir = ROOT / "acc-dataset" / "IFC"
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = out_dir / f"{ifc_path.stem}_summary.json"

    summary = service.preview(ifc_path, save_path=summary_path)
    print(json.dumps(summary, indent=2))

    # Optionally export extracted rules manifest
    if args.export_rules:
        # Build graph with rules embedded and write manifest to a separate file
        graph = service.build_graph(ifc_path, include_rules=True)
        manifest = graph.get("meta", {}).get("rules_manifest")
        if manifest is None:
            print("No rules manifest found in graph (no rule-like property sets detected).")
        else:
            if args.rules_out:
                rules_path = Path(args.rules_out)
            else:
                out_dir = ROOT / "acc-dataset" / "IFC"
                rules_path = out_dir / f"{ifc_path.stem}_rules_manifest.json"
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            rules_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"Rules manifest written to {rules_path}")
