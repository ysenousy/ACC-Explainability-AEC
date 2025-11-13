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
