from __future__ import annotations

import argparse
from pathlib import Path

from data_layer.services import DataLayerService


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild data-layer JSON for an IFC file.")
    parser.add_argument("ifc", help="Path to IFC file")
    parser.add_argument("--out", help="Optional output path for data-layer JSON")
    parser.add_argument("--include-rules", action="store_true", help="Run rule extraction and embed rules manifest into graph meta")
    args = parser.parse_args()

    svc = DataLayerService()
    out = args.out
    if out is None:
        ifc_path = Path(args.ifc)
        out = str(ifc_path.with_name(f"{ifc_path.stem}_dataLayer.json"))

    print(f"Rebuilding graph for {args.ifc} -> {out}")
    svc.save_graph(args.ifc, out_path=out, include_rules=bool(args.include_rules))


if __name__ == "__main__":
    main()
