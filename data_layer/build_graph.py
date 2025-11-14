# data_layer/build_graph.py

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Make sure project root is on sys.path so "data_layer" can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# 🔹 Use absolute imports, not relative
from data_layer.services import DataLayerService

_SERVICE = DataLayerService()


def build_data_graph(ifc_path: str | Path) -> Dict[str, Any]:
    """Create the canonical data-layer JSON graph for one IFC file."""
    return _SERVICE.build_graph(ifc_path)


def save_data_graph(
    ifc_path: str | Path,
    out_path: str | Path | None = None
) -> Path:
    """Build and save the JSON graph next to the IFC or to a custom location."""
    return _SERVICE.save_graph(ifc_path, out_path)


if __name__ == "__main__":
    # Optional: quick manual test if you run this file directly in VS Code.
    # 👉 Adjust this path to point to a real IFC file on your machine.
    default_ifc = PROJECT_ROOT / "acc-dataset" / "IFC" / "AC20-Institute-Var-2.ifc"
    if default_ifc.exists():
        save_data_graph(default_ifc)
    else:
        print("[INFO] No default IFC found. Edit build_graph.py '__main__' section "
              "or use build_graph_cli.py instead.")
