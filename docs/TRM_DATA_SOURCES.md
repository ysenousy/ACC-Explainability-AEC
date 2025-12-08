# TRM Training Data - Input Sources Explained

## 🎯 What Data Does TRM Use as Input?

The TRM training system has **3 input sources**:

---

## 1️⃣ **Source 1: IFC Files (Your Building Models)**

### Files You Have:
```
acc-dataset/IFC/
├── BasicHouse.ifc
├── AC20-FZK-Haus.ifc
└── AC20-Institute-Var-2.ifc
```

### What's Extracted From IFC:
After parsing IFC files, the system extracts **element data**:

```json
{
  "guid": "door-001",
  "type": "IfcDoor",
  "name": "Main Entry Door",
  "ifc_class": "IfcDoor",
  
  // Quantitative properties (extracted from QTO)
  "width_mm": 950,
  "height_mm": 2100,
  "clear_width_mm": 920,
  
  // Property Sets (from PSet)
  "FireRating": "60",
  "SoundTransmissionClass": "28",
  "Acoustic": true,
  
  // Dimensions and derived properties
  "area_m2": 2.0,
  "perimeter_m": 6.2,
  
  // Attributes
  "status": "approved",
  "material": "wood"
}
```

**How Extracted**:
- QTO (Quantity Take-Off): `Qto_DoorOpeningProperties.ClearWidth` → 920mm
- PSet (Property Set): `Pset_DoorCommon.FireRating` → "60"
- Direct attributes: `width`, `height`, etc.

---

## 2️⃣ **Source 2: Compliance Rules (Your Rules Config)**

### Files You Have:
```
rules_config/
├── enhanced-regulation-rules.json (30+ rules)
├── custom_rules.json (25+ rules)
└── rules.json (basic rules)
```

### What's Extracted From Rules:

```json
{
  "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
  "name": "Door Minimum Clear Width",
  "severity": "ERROR",
  "regulation": "ADA Standards",
  "section": "303.2",
  
  // Evaluation logic
  "target": {
    "ifc_class": "IfcDoor"
  },
  
  "condition": {
    "op": ">=",
    "lhs": {
      "source": "qto",
      "qto_name": "Qto_DoorOpeningProperties",
      "quantity": "ClearWidth",
      "unit": "mm"
    },
    "rhs": {
      "source": "parameter",
      "param": "min_clear_width_mm"
    }
  },
  
  "parameters": {
    "min_clear_width_mm": 920
  }
}
```

---

## 3️⃣ **Source 3: Compliance Check Results (Pass/Fail Labels)**

### Where It Comes From:
Running your compliance checker on IFC + Rules produces:

```
POST /api/compliance/check
Body: {
  "graph": {IFC data from Source 1},
  "rules": {Rules data from Source 2}
}
```

### Response = Training Labels:
```json
{
  "results": [
    {
      "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
      "element_guid": "door-001",
      "element_type": "IfcDoor",
      "element_name": "Main Entry Door",
      "rule_name": "Door Minimum Clear Width",
      
      // THE LABEL (this is what TRM learns to predict)
      "passed": true,
      
      // The values used in evaluation
      "actual_value": 920,
      "required_value": 920,
      "unit": "mm",
      "data_source": "qto:Qto_DoorOpeningProperties.ClearWidth",
      "data_status": "complete"
    },
    {
      "rule_id": "ADA_DOOR_MIN_HEIGHT",
      "element_guid": "door-001",
      "passed": true,
      "actual_value": 2100,
      "required_value": 2032,
      ...
    },
    {
      "rule_id": "IBC_FIRE_DOOR_RATING",
      "element_guid": "door-001",
      "passed": false,  // ← This is a failure example
      "actual_value": null,
      "required_value": "60",
      "data_status": "missing"  // Skip this in training
    }
  ]
}
```

---

## 📊 Complete Data Flow

```
┌─────────────────┐
│  IFC Files (3)  │
└────────┬────────┘
         │ Parse/Extract
         ↓
┌──────────────────────────┐
│  Element Data            │
│  (door: width, height,   │
│   room: area, height)    │
└────────┬─────────────────┘
         │
         │ Combine with:
         ↓
┌──────────────────────────┐
│  Rule Definitions (55+)  │
│  (ADA, IBC, Custom)      │
└────────┬─────────────────┘
         │ Run compliance check
         ↓
┌──────────────────────────────────┐
│  Compliance Results              │
│  element + rule → pass/fail label│
└────────┬──────────────────────────┘
         │ Filter (only complete)
         ↓
┌────────────────────────────────────────┐
│  TRM TRAINING DATA                     │
│  500+ samples of:                      │
│  (element_features,                    │
│   rule_context,                        │
│   pass/fail_label)                     │
└────────┬─────────────────────────────────┘
         │ Train TRM
         ↓
┌────────────────────────────┐
│  TRAINED TRM MODEL (7M)    │
│  trm_compliance_v1.pt      │
└────────────────────────────┘
```

---

## 🔄 How It Works Step-by-Step

### Step 1: Load IFC File
```python
# Your IFC file is loaded
graph = load_ifc("BasicHouse.ifc")
# Returns: graph with all elements extracted
# Elements: [door1, door2, space1, space2, space3, ...]
```

### Step 2: Run Compliance Check
```python
# You run compliance check (existing system)
POST /api/compliance/check
{
  "graph": graph,
  "rules": [all 55+ rules]
}

# Response: 500 results
# Each result: element_guid + rule_id → passed/failed
```

### Step 3: Extract Training Data
```python
# Extract training samples from compliance results
converter = ComplianceCheckToTRMConverter()
training_data = converter.convert(compliance_results)

# Each sample contains:
{
  "element_features": {
    "guid": "door-001",
    "type": "IfcDoor",
    "width": 950,
    "height": 2100,
    ...
  },
  "rule_context": {
    "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
    "requirement": 920,
    ...
  },
  "trm_target_label": 1  # 1=pass, 0=fail (this is what to predict)
}
```

### Step 4: Train TRM
```python
# Train model on extracted data
trainer = TRMTrainer()
trainer.train(training_data_file)

# Model learns: given (element features + rule) → predict pass/fail
```

---

## 📝 Summary: What TRM Uses As Input

| Input Type | Source | Contains |
|---|---|---|
| **Element Data** | IFC files | Dimensions, properties, type (door width, room area, etc.) |
| **Rule Data** | Rules config | Requirements, parameters, evaluation logic (min width, max occupancy) |
| **Labels** | Compliance check | Pass/fail results (ground truth for learning) |

---

## ✅ What You Already Have (Ready to Use)

- ✅ **IFC Files**: BasicHouse.ifc, AC20-FZK-Haus.ifc, AC20-Institute-Var-2.ifc
- ✅ **Rules**: 55+ rules in enhanced-regulation-rules.json
- ✅ **Compliance Checker**: `/api/compliance/check` endpoint
- ✅ **System to Extract**: We'll create the converter

**All you need to do**: Run `/api/compliance/check` on your IFC files, and TRM will use the results to train.

---

## 🎯 The Appendable Part

When you add a **new IFC file** (e.g., `NewBuilding.ifc`):

1. Run compliance check on new file → 150 new results
2. Extract training samples from new results → 150 samples
3. **Append** to existing training_data.json
4. Retrain model → trm_v2.pt (better with more data)

**So yes, training data is fully appendable and can grow over time!**

---

## Example: Full Training Cycle

### Day 1: BasicHouse.ifc
```
Load BasicHouse.ifc
Run /api/compliance/check
Extract 100 samples
Save → data/trm_training_data.json
```

### Day 5: AC20-FZK-Haus.ifc
```
Load AC20-FZK-Haus.ifc
Run /api/compliance/check
Extract 150 samples
APPEND → data/trm_training_data.json (now 250 samples)
Retrain → trm_v1.5.pt
```

### Day 10: New IFC File from Client
```
Load ClientBuilding.ifc (new file)
Run /api/compliance/check
Extract 80 samples
APPEND → data/trm_training_data.json (now 330 samples)
Retrain → trm_v2.pt (even better!)
```

---

## 🚀 Next Question

Should I update the plan to explicitly include:
- [ ] Auto-append after each compliance check (with toggle)?
- [ ] Separate endpoint `/api/trm/append-training-data`?
- [ ] Keep current batch approach (user manually combines)?

Let me know your preference!
