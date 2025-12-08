# PHASE 1: BACKEND DATA PIPELINE (INCREMENTAL) - DETAILED PLAN

## Overview
Convert compliance check results into incremental training samples, one at a time as users approve results.

**NOT** batch extraction of all 24 files.
**INSTEAD** gradual accumulation: 1 file → 1 approval → 1 training sample added.

---

## Architecture Flow

```
User uploads BasicHouse.ifc
        ↓
Data Layer extracts elements (door-001, room-001, etc.)
        ↓
Rule Layer runs compliance checks (55 rules)
        ↓
Shows results to user: "Door passes ADA, Room fails IBC"
        ↓
USER APPROVES/REVIEWS (Manual quality control)
        ↓
PHASE 1 TRIGGERS: Convert approved result to training sample
        ↓
INCREMENTAL UPDATE: Add to data/trm_incremental_data.json
        ↓
TRM Model (Phase 3) learns from this new sample
        ↓
User uploads next file and repeats...
```

---

## File Structure

### 1. Data Storage Location
```
data/
├─ trm_incremental_data.json  (NEW - grows over time)
│  {
│    "samples": [
│      {sample1}, {sample2}, {sample3}, ...
│    ],
│    "metadata": {
│      "total_samples": 3,
│      "train_samples": 2,
│      "val_samples": 1,
│      "test_samples": 0,
│      "last_updated": "2025-12-08T10:30:00",
│      "ifc_files_processed": ["BasicHouse.ifc", "AC20-FZK-Haus.ifc", "AC20-Institute-Var-2.ifc"]
│    }
│  }
```

---

## Components to Create

### File: `backend/trm_data_extractor.py` (NEW)

**Class 1: ComplianceResultToTRMSample**

**Purpose**: Convert ONE compliance check result into ONE training sample

**Input**:
```python
{
  "element_guid": "door-001",
  "element_data": {
    "type": "IfcDoor",
    "name": "Main Entry Door",
    "width_mm": 950,
    "height_mm": 2100,
    "clear_width_mm": 920,
    "area_m2": 2.0,
    "material": "wood",
    "fire_rating": "60",
    "ifc_file": "BasicHouse.ifc"
  },
  "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
  "rule_data": {
    "name": "Door Minimum Clear Width",
    "severity": "ERROR",
    "regulation": "ADA Standards",
    "parameters": {"min_clear_width_mm": 920}
  },
  "compliance_result": {
    "passed": true,
    "actual_value": 920,
    "required_value": 920,
    "unit": "mm"
  }
}
```

**Process**:
1. Extract element features (128-dim vector)
   - Properties: width, height, area, perimeter
   - Type encoding: IfcDoor → [0.1, 0.8, 0.0, ...]
   - Material encoding: wood → [0.5, 0.2, ...]
   - Result: 128-dimensional array

2. Extract rule features (128-dim vector)
   - Severity encoding: ERROR → [0.9, 0.1, ...]
   - Regulation encoding: ADA → [0.2, 0.8, ...]
   - Parameters encoding: min_clear_width_mm → [0.3, ...]
   - Result: 128-dimensional array

3. Extract context (64-dim vector)
   - Element type: IfcDoor
   - Rule type: dimensional_check
   - Severity level: ERROR
   - Result: 64-dimensional array

4. Create label
   - Label = 1 if passed else 0

**Output**:
```python
{
  "element_guid": "door-001",
  "element_features": [0.5, 0.2, ..., 0.8],  # 128-dim numpy array
  "rule_context": [0.1, 0.9, ..., 0.3],      # 128-dim numpy array
  "context_embedding": [0.4, 0.6, ..., 0.2], # 64-dim numpy array
  "label": 1,  # 0 or 1
  "metadata": {
    "ifc_file": "BasicHouse.ifc",
    "timestamp": "2025-12-08T10:25:00",
    "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
    "element_type": "IfcDoor"
  }
}
```

**Methods**:
```python
def extract_element_features(element_data: dict) -> np.ndarray:
    """Convert element properties to 128-dim vector"""
    # ...implementation...
    return features  # shape: (128,)

def extract_rule_features(rule_data: dict) -> np.ndarray:
    """Convert rule properties to 128-dim vector"""
    # ...implementation...
    return features  # shape: (128,)

def extract_context(element_data, rule_data) -> np.ndarray:
    """Convert context to 64-dim vector"""
    # ...implementation...
    return context  # shape: (64,)

def convert(compliance_result: dict) -> dict:
    """Main conversion function"""
    # ...calls above methods...
    return training_sample
```

---

**Class 2: IncrementalDatasetManager**

**Purpose**: Manage incremental training data file (append-only)

**Input**: Training sample from ComplianceResultToTRMSample

**Process**:
1. Load existing data from `data/trm_incremental_data.json` (or create if doesn't exist)
2. Append new sample
3. Update metadata (total count, last updated)
4. Split data: 80% train, 10% val, 10% test
5. Save back to file

**Methods**:
```python
def load_or_create(file_path: str) -> dict:
    """Load existing data or create empty structure"""
    if file_exists(file_path):
        return load_json(file_path)
    else:
        return {
            "samples": [],
            "metadata": {
                "total_samples": 0,
                "train_samples": 0,
                "val_samples": 0,
                "test_samples": 0,
                "created_at": datetime.now(),
                "last_updated": datetime.now(),
                "ifc_files_processed": []
            }
        }

def add_sample(file_path: str, sample: dict, ifc_file: str) -> dict:
    """
    Add ONE sample to incremental data file
    
    Args:
        file_path: path to trm_incremental_data.json
        sample: output from ComplianceResultToTRMSample
        ifc_file: name of IFC file this sample came from
    
    Returns:
        Updated metadata
    """
    # Load existing
    data = load_or_create(file_path)
    
    # Add sample
    data["samples"].append(sample)
    
    # Update metadata
    total = len(data["samples"])
    data["metadata"]["total_samples"] = total
    data["metadata"]["last_updated"] = datetime.now()
    
    # Track IFC files
    if ifc_file not in data["metadata"]["ifc_files_processed"]:
        data["metadata"]["ifc_files_processed"].append(ifc_file)
    
    # Re-split data (80/10/10)
    train_count = int(total * 0.8)
    val_count = int(total * 0.1)
    test_count = total - train_count - val_count
    
    data["metadata"]["train_samples"] = train_count
    data["metadata"]["val_samples"] = val_count
    data["metadata"]["test_samples"] = test_count
    
    # Save
    save_json(file_path, data)
    
    return data["metadata"]

def get_statistics(file_path: str) -> dict:
    """Get current dataset statistics"""
    data = load_or_create(file_path)
    return data["metadata"]

def get_training_data_arrays(file_path: str) -> tuple:
    """
    Return as numpy arrays (for Phase 3 training)
    
    Returns:
        (X_train, y_train, X_val, y_val, X_test, y_test)
    """
    data = load_or_create(file_path)
    samples = data["samples"]
    total = len(samples)
    
    train_count = int(total * 0.8)
    val_count = int(total * 0.1)
    
    # Split
    train_samples = samples[:train_count]
    val_samples = samples[train_count:train_count + val_count]
    test_samples = samples[train_count + val_count:]
    
    # Convert to numpy arrays
    X_train = np.array([s["element_features"] + s["rule_context"] + s["context_embedding"] for s in train_samples])
    y_train = np.array([s["label"] for s in train_samples])
    
    X_val = np.array([s["element_features"] + s["rule_context"] + s["context_embedding"] for s in val_samples])
    y_val = np.array([s["label"] for s in val_samples])
    
    X_test = np.array([s["element_features"] + s["rule_context"] + s["context_embedding"] for s in test_samples])
    y_test = np.array([s["label"] for s in test_samples])
    
    return X_train, y_train, X_val, y_val, X_test, y_test
```

---

## API Endpoint (Phase 4, but needed to understand Phase 1)

**One endpoint will trigger Phase 1**:

```python
@app.route("/api/trm/add-training-sample", methods=["POST"])
def add_training_sample():
    """
    Called AFTER user approves compliance result
    Converts compliance check → training sample → adds to incremental data
    """
    
    data = request.get_json()
    
    # Input from compliance check
    element_guid = data.get("element_guid")
    element_data = data.get("element_data")
    rule_id = data.get("rule_id")
    rule_data = data.get("rule_data")
    compliance_result = data.get("compliance_result")  # {"passed": true/false}
    ifc_file = data.get("ifc_file")  # "BasicHouse.ifc"
    
    # PHASE 1: Convert to training sample
    converter = ComplianceResultToTRMSample()
    sample = converter.convert({
        "element_guid": element_guid,
        "element_data": element_data,
        "rule_id": rule_id,
        "rule_data": rule_data,
        "compliance_result": compliance_result
    })
    
    # PHASE 1: Add to incremental data
    manager = IncrementalDatasetManager()
    metadata = manager.add_sample(
        file_path="data/trm_incremental_data.json",
        sample=sample,
        ifc_file=ifc_file
    )
    
    return jsonify({
        "success": True,
        "sample_added": True,
        "metadata": metadata,
        "message": f"Sample added. Total: {metadata['total_samples']}"
    })
```

---

## Data Flow Visualization

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: BACKEND DATA PIPELINE (INCREMENTAL)                │
└─────────────────────────────────────────────────────────────┘

USER WORKFLOW:

1. Upload BasicHouse.ifc
   ├─ Data Layer: Extract elements
   ├─ Rule Layer: Check compliance
   └─ Show results in frontend

2. USER REVIEWS & APPROVES
   ├─ "Door-001: PASS ✓"
   ├─ "Room-001: FAIL ✗"
   └─ Frontend sends approved results to backend

3. BACKEND PROCESSES (Phase 1)
   │
   ├─ For each approved result:
   │  │
   │  ├─ ComplianceResultToTRMSample:
   │  │  ├─ Extract element features (128-dim)
   │  │  ├─ Extract rule features (128-dim)
   │  │  ├─ Extract context (64-dim)
   │  │  └─ Create label (0 or 1)
   │  │
   │  └─ IncrementalDatasetManager:
   │     ├─ Load: data/trm_incremental_data.json
   │     ├─ Append: new sample
   │     ├─ Update: metadata
   │     └─ Save: updated file
   │
   └─ Response: {total_samples: 1, train: 1, val: 0, test: 0}

4. DATASET STATUS
   └─ data/trm_incremental_data.json
      ├─ Samples: 1 (Door-001 PASS)
      ├─ Train: 1, Val: 0, Test: 0
      └─ Ready for Phase 3 training

5. REPEAT FOR NEXT FILE
   ├─ Upload AC20-FZK-Haus.ifc
   ├─ Extract + Check compliance
   ├─ User approves 15 results
   ├─ Each triggers Phase 1
   └─ Dataset grows to 16 samples (1 + 15)
```

---

## Incremental Data File Example

**After 1st file (1 approval)**:
```json
{
  "samples": [
    {
      "element_guid": "door-001",
      "element_features": [0.5, 0.2, ..., 0.8],
      "rule_context": [0.1, 0.9, ..., 0.3],
      "context_embedding": [0.4, 0.6, ..., 0.2],
      "label": 1,
      "metadata": {
        "ifc_file": "BasicHouse.ifc",
        "timestamp": "2025-12-08T10:25:00",
        "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
        "element_type": "IfcDoor"
      }
    }
  ],
  "metadata": {
    "total_samples": 1,
    "train_samples": 1,
    "val_samples": 0,
    "test_samples": 0,
    "last_updated": "2025-12-08T10:25:00",
    "ifc_files_processed": ["BasicHouse.ifc"]
  }
}
```

**After 3rd file (16 total approvals)**:
```json
{
  "samples": [
    {...sample1...},
    {...sample2...},
    {...sample3...},
    ...
    {...sample16...}
  ],
  "metadata": {
    "total_samples": 16,
    "train_samples": 13,    // 80% of 16
    "val_samples": 1,       // 10% of 16
    "test_samples": 2,      // 10% of 16
    "last_updated": "2025-12-08T11:45:00",
    "ifc_files_processed": ["BasicHouse.ifc", "AC20-FZK-Haus.ifc", "AC20-Institute-Var-2.ifc"]
  }
}
```

---

## Dependencies

Add to `backend/requirements.txt`:
```
numpy>=1.24.0
torch>=2.0.0
scikit-learn>=1.3.0
```

---

## Implementation Details

### Feature Extraction (Element → 128-dim)
```
Input: {width: 950, height: 2100, area: 2.0, material: "wood", type: "IfcDoor", ...}

Extraction Steps:
1. Normalize numeric features: [0.95, 2.1, 2.0, ...]
2. Encode categorical: 
   - material: "wood" → one-hot → [1, 0, 0, ...]
   - type: "IfcDoor" → embedding → [0.2, 0.8, 0.1, ...]
3. Pad/truncate to 128-dim
4. Output: [0.95, 2.1, 2.0, ..., 1, 0, 0, ..., 0.2, 0.8, 0.1, ...]
```

### Feature Extraction (Rule → 128-dim)
```
Input: {severity: "ERROR", regulation: "ADA", min_clear_width_mm: 920, ...}

Extraction Steps:
1. Encode severity: "ERROR" → [0.9, 0.1, 0.0]
2. Encode regulation: "ADA" → [0.2, 0.8, 0.0]
3. Normalize parameters: [0.92, ...]
4. Pad to 128-dim
5. Output: 128-dimensional array
```

### Context Extraction (64-dim)
```
Input: element_type="IfcDoor", rule_type="dimensional_check", severity="ERROR"

Output: [0.8, 0.3, 0.9, ...] (64-dim)
```

---

## Success Criteria

✅ **Phase 1 is complete when**:
1. `ComplianceResultToTRMSample` class created
2. `IncrementalDatasetManager` class created
3. `data/trm_incremental_data.json` format defined
4. Sample added incrementally (1 at a time)
5. Dataset grows over time (append-only)
6. Metadata updated correctly
7. Data can be split: 80/10/10 train/val/test
8. Ready for Phase 3 (training will use this data)

---

## Timeline

- **Create files**: 5-10 min
- **Implement ComplianceResultToTRMSample**: 10-15 min
- **Implement IncrementalDatasetManager**: 10-15 min
- **Testing**: 10 min
- **Total**: ~45-50 minutes

---

## Next Phase (Phase 3)

Phase 3 will:
1. Call `IncrementalDatasetManager.get_training_data_arrays()`
2. Get (X_train, y_train, X_val, y_val, X_test, y_test)
3. Train TRM model incrementally (update after each sample or batch of samples)

---

## Questions for You

Before I implement, please confirm:

1. ✅ **Incremental approach** (add 1 sample at a time) - Correct?
2. ✅ **Feature dimensions**: element=128, rule=128, context=64 → total input=320 - OK?
3. ✅ **Data split**: 80/10/10 (train/val/test) - Correct?
4. ✅ **File location**: `data/trm_incremental_data.json` - OK?
5. ✅ **One file to create**: `backend/trm_data_extractor.py` - OK?
6. ✅ **Two classes**: ComplianceResultToTRMSample + IncrementalDatasetManager - Correct?

**Or should I modify anything before implementing?**
