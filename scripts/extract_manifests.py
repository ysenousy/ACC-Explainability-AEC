#!/usr/bin/env python
"""Extract rules manifests from all IFC files in a folder and produce a summary."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from data_layer.services import DataLayerService
from data_layer.extract_rules import write_manifest
from rule_layer.loader import validate_manifest

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s - %(message)s",
)
log = logging.getLogger(__name__)


def extract_manifests_from_folder(
    ifc_folder: Path,
    out_folder: Optional[Path] = None,
    validate: bool = True,
) -> dict:
    """Extract manifests from all IFCs in a folder.
    
    Args:
        ifc_folder: folder containing .ifc files.
        out_folder: optional output folder for manifests (defaults to ifc_folder).
        validate: whether to validate manifests.
    
    Returns:
        Summary dict with counts and per-file status.
    """
    out_folder = out_folder or ifc_folder
    out_folder.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "ifc_folder": str(ifc_folder),
        "out_folder": str(out_folder),
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "files": [],
        "total_ifcs": 0,
        "total_rules": 0,
        "validation_errors": [],
    }
    
    ifc_files = sorted(ifc_folder.glob("*.ifc"))
    if not ifc_files:
        log.warning("No .ifc files found in %s", ifc_folder)
        return summary
    
    svc = DataLayerService()
    
    for ifc_path in ifc_files:
        log.info("Processing %s...", ifc_path.name)
        summary["total_ifcs"] += 1
        
        try:
            graph = svc.build_graph(str(ifc_path), include_rules=True)
            manifest = graph.get("meta", {}).get("rules_manifest")
            
            if not manifest:
                log.warning("No manifest extracted from %s", ifc_path.name)
                summary["files"].append({
                    "ifc_file": ifc_path.name,
                    "status": "no_manifest",
                    "rules_count": 0,
                })
                continue
            
            num_rules = len(manifest.get("rules", []))
            
            # Validate manifest if requested
            validation_ok = True
            if validate:
                is_valid, errors = validate_manifest(manifest)
                if not is_valid:
                    validation_ok = False
                    for err in errors:
                        summary["validation_errors"].append({
                            "ifc_file": ifc_path.name,
                            "error": err,
                        })
                    log.warning("Validation errors in manifest from %s: %s", ifc_path.name, errors)
            
            # Write manifest to file
            manifest_path = out_folder / f"{ifc_path.stem}_rules_manifest.json"
            write_manifest(manifest, manifest_path)
            log.info("Wrote manifest (%d rules) to %s", num_rules, manifest_path.name)
            
            summary["files"].append({
                "ifc_file": ifc_path.name,
                "status": "success" if validation_ok else "success_with_errors",
                "rules_count": num_rules,
                "manifest_file": manifest_path.name,
            })
            summary["total_rules"] += num_rules
            
        except Exception as exc:
            log.exception("Failed to process %s: %s", ifc_path.name, exc)
            summary["files"].append({
                "ifc_file": ifc_path.name,
                "status": "error",
                "error": str(exc),
            })
    
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract rules manifests from all IFC files in a folder."
    )
    parser.add_argument(
        "folder",
        help="Folder containing .ifc files",
    )
    parser.add_argument(
        "--out-folder",
        help="Output folder for manifests (defaults to input folder)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip manifest validation",
    )
    parser.add_argument(
        "--summary-file",
        help="Write summary JSON to this file (defaults to <folder>/manifests_summary.json)",
    )
    args = parser.parse_args()
    
    ifc_folder = Path(args.folder).resolve()
    if not ifc_folder.is_dir():
        print(f"Error: {ifc_folder} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    out_folder = Path(args.out_folder).resolve() if args.out_folder else ifc_folder
    summary_file = args.summary_file or str(ifc_folder / "manifests_summary.json")
    
    log.info("Extracting manifests from %s", ifc_folder)
    summary = extract_manifests_from_folder(
        ifc_folder,
        out_folder=out_folder,
        validate=not args.no_validate,
    )
    
    # Write summary
    summary_path = Path(summary_file)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info("Summary written to %s", summary_path)
    
    # Print summary to console
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
