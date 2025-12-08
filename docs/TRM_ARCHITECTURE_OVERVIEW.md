# TRM Architecture - Visual Overview

## System Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                             │
├─────────────────────────────────────────────────────────────────┤
│  ReasoningView.js                                               │
│  ├── Tab 1: Why It Failed (Traditional)                         │
│  ├── Tab 2: Impact Assessment (Traditional)                     │
│  ├── Tab 3: How To Fix (Traditional)                            │
│  └── Tab 4: TRM Recursive Reasoning (NEW)                       │
│      └── TRMVisualization.js                                    │
│          ├── Refinement Steps Timeline                          │
│          ├── Confidence Progression Chart                       │
│          ├── Reasoning Trace Text                               │
│          └── Activation Heatmap                                 │
│                                                                  │
│  trmService.js (NEW) ←→ Backend APIs                            │
└─────────────────────────────────────────────────────────────────┘
         ↑                                         ↓
         │                                         │
    HTTP GET/POST                            HTTP Responses
         │                                         │
         ↓                                         ↑
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask/Python)                       │
├─────────────────────────────────────────────────────────────────┤
│  app.py (Modified)                                              │
│  ├── /api/trm/train                    (POST)                   │
│  ├── /api/trm/analyze                  (POST)                   │
│  ├── /api/trm/batch-analyze            (POST)                   │
│  ├── /api/trm/extract-training-data    (POST)                   │
│  └── /api/reasoning/enrich-compliance  (ENHANCED)               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ CORE COMPONENTS (NEW FILES)                                │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                                                             │ │
│  │  reasoning_layer/tiny_recursive_reasoner.py               │ │
│  │  ├── TinyComplianceNetwork (7M params, 2 layers)          │ │
│  │  ├── RefinementStep (tracks intermediate states)          │ │
│  │  ├── TinyRecursiveReasoner (16-step refinement)           │ │
│  │  └── TRMResult (output dataclass)                         │ │
│  │                                                             │ │
│  │  backend/trm_trainer.py                                    │ │
│  │  ├── ComplianceDataset (PyTorch Dataset)                  │ │
│  │  ├── TRMTrainer (training orchestration)                  │ │
│  │  └── train_trm_from_compliance_checks() (main function)   │ │
│  │                                                             │ │
│  │  backend/trm_data_extractor.py                             │ │
│  │  ├── ComplianceCheckToTRMConverter (single check)          │ │
│  │  └── ComplianceDatasetBuilder (multiple checks)           │ │
│  │                                                             │ │
│  │  backend/trm_model_manager.py                              │ │
│  │  └── TRMModelManager (load, save, version control)        │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ EXISTING COMPONENTS (Unchanged)                            │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ - UnifiedComplianceEngine                                 │ │
│  │ - ReasoningEngine                                         │ │
│  │ - FailureExplainer, ImpactAnalyzer, RecommendationEngine │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         ↑                                         ↓
         │                                         │
      Models/Data                          Saved Checkpoints
         │                                         │
         ↓                                         ↑
┌─────────────────────────────────────────────────────────────────┐
│                    FILE SYSTEM                                  │
├─────────────────────────────────────────────────────────────────┤
│  data/                                                           │
│  └── trm_training_data.json (500-1000 samples)                  │
│                                                                  │
│  models/                                                         │
│  ├── trm_compliance_v1.pt (trained model weights)               │
│  ├── trm_compliance_v1_meta.json (training metadata)            │
│  ├── trm_compliance_v2.pt                                       │
│  └── trm_compliance_v2_meta.json                                │
│                                                                  │
│  acc-dataset/IFC/                                               │
│  ├── BasicHouse.ifc                                             │
│  ├── AC20-FZK-Haus.ifc                                          │
│  └── AC20-Institute-Var-2.ifc                                   │
│                                                                  │
│  rules_config/                                                  │
│  ├── enhanced-regulation-rules.json (55+ rules)                 │
│  └── custom_rules.json (25+ rules)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Training

```
Input IFC Files (3)
    │
    ├─→ BasicHouse.ifc
    │       │
    │       v
    │   [Run /api/compliance/check]
    │       │
    │       v
    │   Compliance Results
    │   {results: [{rule_id, element_guid, passed, actual_value, required_value}, ...]}
    │
    ├─→ AC20-FZK-Haus.ifc ──→ [Check] ──→ Results
    │
    └─→ AC20-Institute-Var-2.ifc ──→ [Check] ──→ Results
            │
            v
        (Combine all results)
            │
            v
    [/api/trm/extract-training-data]
            │
            v
    ComplianceCheckToTRMConverter
    {
      element_features: {guid, type, name, ifc_class},
      rule_context: {id, name, severity, parameters},
      compliance_check: {actual, required, passed},
      trm_target_label: 0|1
    }
            │
            v
    ComplianceDatasetBuilder
    (Accumulate 500-1000 samples)
            │
            v
    train/val/test split
    (80% / 10% / 10%)
            │
            v
    data/trm_training_data.json
            │
            v
    [/api/trm/train] with TRMTrainer
    ├─ Load training data
    ├─ Create PyTorch DataLoader
    ├─ Initialize TinyRecursiveReasoner
    ├─ For each epoch:
    │  ├─ Forward pass (16-step recursion)
    │  ├─ Deep supervision loss (steps 1,4,8,16)
    │  ├─ Backward pass + EMA update
    │  ├─ Validation on val_set
    │  └─ Save best model
    ├─ Test on test_set
    └─ Return metrics
            │
            v
    models/trm_compliance_v1.pt (7M params)
    models/trm_compliance_v1_meta.json (metadata)
```

---

## Data Flow: Inference (Single Element)

```
Input:
├─ Element Features: {guid: "door-001", type: "IfcDoor", width: 0.95, ...}
├─ Rule Context: {id: "ADA_DOOR_MIN_CLEAR_WIDTH", requirement: 0.92, ...}
└─ Model Path: "models/trm_compliance_v1.pt"
    │
    v
[/api/trm/analyze] Endpoint
    │
    v
Load Model (TRMModelManager)
    │
    v
Feature Extraction & Embedding
├─ Element Vector (128-dim): embed(element_features)
├─ Rule Vector (128-dim): embed(rule_context)
└─ Context Vector (64-dim): severity + regulation encoding
    │
    v
TinyRecursiveReasoner (16-step loop)

┌─────────────────────────────────────────────────────────┐
│ Step 1:  Initial input → Network → pred₁, conf₁       │
│         RefinementStep {input, output, attention}      │
│                                                          │
│ Step 2:  pred₁ + refined input → Network → pred₂      │
│         RefinementStep tracking                        │
│                                                          │
│ Step 3:  pred₂ + refined input → Network → pred₃      │
│         Confidence: 0.72                               │
│                                                          │
│ Step 4:  pred₃ + refined input → Network → pred₄      │
│         Deep supervision loss computed here            │
│         Confidence: 0.81                               │
│                                                          │
│ ...                                                     │
│                                                          │
│ Step 12: pred₁₁ + refined → Network → pred₁₂          │
│         Confidence: 0.94                               │
│         ΔConfidence = |0.94 - 0.93| = 0.01             │
│         Early stop (converged)                         │
│                                                          │
│ Return at Step 12 (not 16)                             │
└─────────────────────────────────────────────────────────┘
    │
    v
TRMResult
{
  rule_id: "ADA_DOOR_MIN_CLEAR_WIDTH",
  element_guid: "door-001",
  final_prediction: 1,           ← PASS
  confidence: 0.94,              ← Very confident
  num_refinement_steps: 12,      ← Early stopped
  reasoning_trace: [
    "Step 1: Initial assessment - door width 0.95m",
    "Step 2: Rule context loaded - ADA standard requires 0.92m",
    ...
    "Step 12: Converged - PASS with 94% confidence"
  ],
  refinement_steps: [
    {step: 1, prediction: 0, confidence: 0.52, ...},
    {step: 2, prediction: 0, confidence: 0.61, ...},
    ...
    {step: 12, prediction: 1, confidence: 0.94, ...}
  ],
  inference_time_ms: 127
}
    │
    v
[Response to Frontend]
    │
    v
TRMVisualization.js
├─ Timeline: Show steps 1-12 (visual)
├─ Chart: Confidence 0.52 → 0.94 (curve)
├─ Trace: Step-by-step reasoning text
└─ Heatmap: Feature importance (attention)
```

---

## Data Flow: Batch Inference

```
Input: IFC Graph (50 elements) + Rules (10 rules)
    │
    v
[/api/trm/batch-analyze]
    │
    ├─→ For each element-rule pair (500 total):
    │       │
    │       v
    │   [/api/trm/analyze] (via loop)
    │       │
    │       v
    │   TRMResult {pred, confidence, steps}
    │       │
    │       └─→ Accumulate results
    │
    v
Aggregate Response
{
  success: true,
  results: [TRMResult, TRMResult, ...],  ← 500 results
  statistics: {
    total_analyzed: 500,
    average_confidence: 0.87,
    passed_predictions: 420,
    failed_predictions: 80,
    total_time_ms: 58000
  }
}
```

---

## Component Dependencies

```
Frontend
├── ReasoningView.js
│   ├── TRMVisualization.js (NEW)
│   └── trmService.js
│       ├── /api/trm/analyze
│       ├── /api/trm/batch-analyze
│       └── /api/trm/train (optional)
│
└── ComplianceCheckView.js (MODIFIED)
    └── trmService.js
        ├── /api/trm/analyze
        └── /api/trm/extract-training-data


Backend (app.py)
├── /api/trm/train
│   └── trm_trainer.py (NEW)
│       ├── TRMTrainer
│       ├── ComplianceDataset
│       └── tiny_recursive_reasoner.py (NEW)
│           └── TinyRecursiveReasoner
│
├── /api/trm/analyze
│   ├── trm_model_manager.py (NEW)
│   └── tiny_recursive_reasoner.py
│       ├── TinyComplianceNetwork
│       └── TinyRecursiveReasoner
│
├── /api/trm/batch-analyze
│   └── [Same as analyze, looped]
│
├── /api/trm/extract-training-data
│   └── trm_data_extractor.py (NEW)
│       └── ComplianceCheckToTRMConverter
│
└── /api/reasoning/enrich-compliance (ENHANCED)
    └── TinyRecursiveReasoner (optional)


Data Files
├── data/trm_training_data.json
│   └── Created by: /api/trm/extract-training-data
│
└── models/trm_compliance_v*.pt
    └── Created by: /api/trm/train
```

---

## TRM Model Architecture

```
Input (320-dim)
├─ Element Vector: 128-dim
├─ Rule Vector: 128-dim
└─ Context Vector: 64-dim
    │
    v
SwiGLU Block 1
├─ W1: 320 × 256 + Bias
├─ Gate: σ(W_gate: 320 × 256)
├─ Output: (W1 × input) ⊗ Gate
└─ Residual: input + output (if compatible)
    │
    v
SwiGLU Block 2
├─ W2: 256 × 256 + Bias
├─ Gate: σ(W_gate: 256 × 256)
└─ Output: (W2 × hidden) ⊗ Gate
    │
    v
Output Layer
├─ Linear: 256 × 2
└─ Output: logits for [FAIL, PASS]
    │
    v
Softmax → Probabilities [0.3, 0.7]
    │
    v
Prediction + Confidence
├─ Prediction: argmax = 1 (PASS)
└─ Confidence: max = 0.7


[Repeat 16 times with previous output feeding into next iteration]

16-Step Refinement Loop:
Step 1: input → network → pred₁
Step 2: [pred₁, input, attention] → network → pred₂
Step 3: [pred₂, input, updated_attention] → network → pred₃
...
Step 16: [pred₁₅, input, refined_attention] → network → pred₁₆

Early Stop: If |conf_t - conf_{t-1}| < 0.01 for 2 consecutive steps
```

---

## Training Process Visualization

```
Epoch 1
├─ Batch 1 (32 samples)
│  ├─ Forward: 16-step refinement for each sample
│  ├─ Loss at steps 1,4,8,16 (deep supervision)
│  ├─ Total loss: L = (L₁ + L₄ + L₈ + L₁₆) / 4
│  ├─ Backward: Compute gradients
│  ├─ Update: AdamW optimizer
│  └─ EMA: Update exponential moving average weights
│
├─ Batch 2-N: [Repeat]
│
├─ Validation
│  ├─ Run on val_set (50 samples)
│  ├─ Compute validation loss
│  └─ If val_loss < best_val_loss: Save checkpoint
│
└─ Metrics: Loss=0.42, Val_Loss=0.38, Accuracy=78%

Epoch 2
├─ Batch 1-N: [Repeat with updated weights]
└─ Metrics: Loss=0.35, Val_Loss=0.33, Accuracy=82%

...

Epoch 50
├─ Batch 1-N
└─ Metrics: Loss=0.18, Val_Loss=0.22, Accuracy=88%

Final Test
├─ Run on test_set (100 samples)
├─ Compute test metrics
└─ Report: Accuracy=87%, Precision=0.89, Recall=0.85
```

---

## Integration Points with Existing System

```
Existing Compliance Flow
IFC Graph → UnifiedComplianceEngine → Results
            └─ No TRM

New Integrated Flow
IFC Graph → UnifiedComplianceEngine → Results
            └─ (Optional) TinyRecursiveReasoner → Enhanced Results

Usage Control:
- /api/compliance/check: Returns traditional results
- /api/compliance/check?include_trm=true: Returns traditional + TRM
- /api/trm/analyze: Standalone TRM analysis

Frontend Control:
- ReasoningView: 4 tabs, last tab is TRM (optional)
- ComplianceCheckView: Checkbox to enable TRM
```

---

## File Structure After Implementation

```
acc-explainability-aec/
├── reasoning_layer/
│   ├── tiny_recursive_reasoner.py        ← NEW (1100 lines)
│   ├── reasoning_engine.py               (unchanged)
│   └── ...
│
├── backend/
│   ├── trm_data_extractor.py            ← NEW (300 lines)
│   ├── trm_trainer.py                   ← NEW (450 lines)
│   ├── trm_model_manager.py             ← NEW (200 lines)
│   ├── app.py                           (MODIFIED: +250 lines for 5 endpoints)
│   ├── requirements.txt                 (MODIFIED: +2 packages)
│   └── ...
│
├── frontend/src/
│   ├── components/
│   │   ├── TRMVisualization.js          ← NEW (400 lines)
│   │   ├── ReasoningView.js             (MODIFIED: +50 lines)
│   │   ├── ComplianceCheckView.js       (MODIFIED: +30 lines)
│   │   └── ...
│   │
│   └── services/
│       ├── trmService.js                ← NEW (150 lines)
│       └── ...
│
├── data/
│   └── trm_training_data.json          ← AUTO-GENERATED
│
├── models/
│   ├── trm_compliance_v1.pt            ← AUTO-GENERATED
│   └── trm_compliance_v1_meta.json     ← AUTO-GENERATED
│
└── docs/
    ├── TRM_IMPLEMENTATION_PLAN.md      (this file)
    ├── ARCHITECTURE_OVERVIEW.md        (visual guide)
    └── ...
```

---

## Performance Expectations

```
Training (500 samples):
├─ Data preparation: 5 sec
├─ 50 epochs × 16 batches/epoch:
│  └─ 800 forward passes (16 refinement steps each)
│  └─ 12,800 network forward passes total
├─ CPU (Intel i7): ~10-15 minutes
├─ GPU (Tesla T4): ~1-2 minutes
└─ Output: trm_compliance_v1.pt (28 MB)

Inference (Single Element):
├─ Load model: 100 ms (first call)
├─ Feature extraction: 2 ms
├─ 16-step refinement: 80 ms (or early stop at step 12: 60 ms)
├─ Prepare response: 5 ms
└─ Total: 100-200 ms (with model caching)

Inference (Batch 50 elements):
├─ Load model: 100 ms (first call, cached)
├─ Process 50 elements: 50 × 70 ms = 3,500 ms
├─ Overhead: 500 ms
└─ Total: ~4 seconds

Batch 500 elements:
└─ ~40 seconds (10 elements/sec on CPU)
```

---

## Success Criteria Checklist

```
Phase 1: Data Extraction
☐ Extract 500+ training samples from IFC files
☐ Samples have complete data (no missing values)
☐ Can combine multiple compliance checks
☐ /api/trm/extract-training-data works

Phase 2: TRM Model
☐ Network initializes (7M params)
☐ Inference runs (16 steps)
☐ Reasoning trace generated
☐ Early stopping works

Phase 3: Training
☐ Model trains without errors
☐ Loss decreases over epochs
☐ Validation accuracy > 75%
☐ Model saves as checkpoint

Phase 4: API Endpoints
☐ /api/trm/analyze returns valid TRMResult
☐ /api/trm/batch-analyze processes 50 elements < 5s
☐ /api/trm/train completes training
☐ /api/trm/extract-training-data works

Phase 5: Frontend
☐ TRM tab displays in ReasoningView
☐ Refinement timeline renders
☐ Confidence chart shows curve
☐ Reasoning trace displays
☐ No console errors

Integration
☐ All components work together
☐ No conflicts with existing code
☐ Can roll back (5 minutes)
☐ Performance acceptable
```
