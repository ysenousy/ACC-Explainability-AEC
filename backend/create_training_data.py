#!/usr/bin/env python
"""
Create synthetic training data with the new rich features.
"""

import sys
sys.path.insert(0, '.')

import json
import numpy as np
import os

def create_synthetic_training_data():
    """Create synthetic training data with varied features."""
    print("[INFO] Creating synthetic TRM training data...")
    print("=" * 60)
    
    try:
        from backend.trm_data_extractor import ComplianceResultToTRMSample
        
        samples = []
        
        # Generate synthetic element data with varied dimensions
        widths = [400, 550, 650, 700, 800, 1000, 1200, 900, 750, 600]
        heights = [2000, 2200, 2400, 2600, 2800, 1800, 2500, 2300, 2100, 2700]
        types = ["IfcDoor", "IfcWindow", "IfcWall", "IfcRoom", "IfcDoor"]
        
        converter = ComplianceResultToTRMSample()
        
        # Create 488 samples (our dataset size)
        for i in range(488):
            # Vary dimensions cyclically
            width = widths[i % len(widths)]
            height = heights[i % len(heights)]
            elem_type = types[i % len(types)]
            
            # Create synthetic element data
            element_data = {
                "width_mm": width + np.random.randint(-50, 50),
                "height_mm": height + np.random.randint(-100, 100),
                "clear_width_mm": min(850, width - 50) if elem_type == "IfcDoor" else 0,
                "area_m2": (width / 1000.0) * (height / 1000.0),
                "perimeter_m": 2 * ((width + height) / 1000.0),
                "type": elem_type,
                "fire_rating": np.random.choice([0, 0.5, 1.0]) if np.random.random() > 0.5 else None,
                "acoustic_rating": np.random.choice([0, 0.5, 1.0]) if np.random.random() > 0.5 else None,
                "is_fire_rated": np.random.random() > 0.7,
                "is_accessible": np.random.random() > 0.6,
                "storey": str(np.random.randint(0, 5)),
            }
            
            # Create synthetic rule data
            rule_data = {
                "id": f"rule_{i % 10}",
                "name": f"Test Rule {i % 10}",
                "severity": np.random.choice(["ERROR", "WARNING", "INFO"]),
                "target": {"ifc_class": elem_type},
            }
            
            # Create synthetic compliance result
            # Make it MOSTLY deterministic based on element properties
            # Doors/Windows are more likely to PASS (70% pass rate)
            # Walls are more likely to FAIL (60% fail rate)
            # Others 50/50
            
            if elem_type in ["IfcDoor", "IfcWindow"]:
                passed = np.random.random() > 0.3  # 70% pass
            elif elem_type == "IfcWall":
                passed = np.random.random() > 0.6  # 40% pass
            else:
                passed = np.random.random() > 0.5  # 50% pass
            
            compliance_result = {
                "element_guid": f"elem_{i}",
                "element_data": element_data,
                "rule_data": rule_data,
                "compliance_result": {
                    "passed": passed,
                    "remediation_difficulty": np.random.uniform(0, 1),
                },
                "rule_id": rule_data["id"],
            }
            
            # Convert to training sample
            try:
                sample = converter.convert(compliance_result)
                samples.append(sample)
            except Exception as e:
                print(f"[WARN] Failed to convert sample {i}: {e}")
        
        print(f"[INFO] Generated {len(samples)} synthetic training samples")
        
        # Check feature variance
        if samples:
            first_sample = samples[0]
            el_feats = np.array([s["element_features"] for s in samples])
            const_count = 0
            for j in range(el_feats.shape[1]):
                std = np.std(el_feats[:, j])
                if std < 0.01:
                    const_count += 1
            
            print(f"[INFO] Element feature variance: {128 - const_count}/128 dims have variance")
            
            labels = [s["label"] for s in samples]
            print(f"[INFO] Label distribution: PASS={sum(labels)}, FAIL={len(labels) - sum(labels)}")
        
        # Save training data
        training_data = {
            "version": "1.0",
            "samples": samples
        }
        
        os.makedirs("data", exist_ok=True)
        with open("data/trm_incremental_data.json", "w") as f:
            json.dump(training_data, f)
        
        print(f"[OK] Saved synthetic training data")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create training data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if create_synthetic_training_data():
        print("\n[OK] Ready to retrain model!")
    else:
        sys.exit(1)
