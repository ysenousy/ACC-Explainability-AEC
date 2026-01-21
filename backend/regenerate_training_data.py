#!/usr/bin/env python
"""
Regenerate TRM training data by running compliance checks on sample IFC models.
"""

import sys
sys.path.insert(0, '.')

import json
import os
from pathlib import Path

def regenerate_training_data():
    """Regenerate training data from IFC models."""
    print("[INFO] Regenerating TRM training data...")
    print("=" * 60)
    
    try:
        from backend.rule_compliance_checker import RuleComplianceChecker
        from backend.trm_data_extractor import ComplianceResultToTRMSample
        
        # Find IFC files
        ifc_dir = Path("acc-dataset/IFC")
        ifc_files = list(ifc_dir.glob("*.ifc")) if ifc_dir.exists() else []
        
        if not ifc_files:
            print("[ERROR] No IFC files found in acc-dataset/IFC/")
            return False
        
        print(f"[INFO] Found {len(ifc_files)} IFC files")
        
        # Run compliance checks
        checker = RuleComplianceChecker()
        all_compliance_results = []
        
        for ifc_file in ifc_files[:5]:  # Process first 5 files for now
            print(f"[INFO] Processing {ifc_file.name}...")
            try:
                compliance_results = checker.check_file(str(ifc_file))
                all_compliance_results.extend(compliance_results)
                print(f"  - Generated {len(compliance_results)} compliance results")
            except Exception as e:
                print(f"  - Error: {e}")
        
        print(f"\n[INFO] Total compliance results: {len(all_compliance_results)}")
        
        # Convert to training samples
        converter = ComplianceResultToTRMSample()
        training_samples = []
        
        for comp_result in all_compliance_results:
            try:
                sample = converter.convert(comp_result)
                training_samples.append(sample)
            except Exception as e:
                print(f"[WARN] Failed to convert sample: {e}")
        
        print(f"[INFO] Generated {len(training_samples)} training samples")
        
        # Save training data
        training_data = {
            "version": "1.0",
            "samples": training_samples
        }
        
        os.makedirs("data", exist_ok=True)
        with open("data/trm_incremental_data.json", "w") as f:
            json.dump(training_data, f)
        
        print(f"[OK] Saved training data to data/trm_incremental_data.json")
        
        # Check feature variance
        if training_samples:
            import numpy as np
            first_sample = training_samples[0]
            el_feat = np.array(first_sample["element_features"])
            const_dims = sum(1 for feat in [np.array(s["element_features"]) for s in training_samples] if len(set(feat)) < 3)
            print(f"[INFO] Element feature variance: {128 - const_dims}/128 dims have variance")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to regenerate training data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if regenerate_training_data():
        print("\n[OK] Ready to retrain model!")
    else:
        sys.exit(1)
