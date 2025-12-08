# TRM Implementation - Quick Reference

## What is TRM?
Tiny Recursive Model (arXiv:2510.04871) - a 7M parameter network that learns compliance patterns through 16-step iterative refinement. It beats 671B LLMs on structured reasoning tasks.

## Why TRM for Compliance?
- ✅ Small model (7M) learns from your 300-500 compliance samples
- ✅ Fast inference (100-200ms per element-rule pair)
- ✅ Interpretable (shows 16-step reasoning trace)
- ✅ Better than LLMs for deterministic compliance logic
- ✅ Complements traditional reasoning (why, impact, how-to-fix)

---

## Implementation Roadmap

### Phase 1: Extract Training Data (3-4 days)
**Goal**: Create labeled training dataset from compliance checks

**What**: `backend/trm_data_extractor.py`
- Convert compliance check results → training samples
- Filter to complete data only
- Combine from multiple IFC files
- Output: `data/trm_training_data.json` (500-1000 samples)

**Files to Create**:
- `backend/trm_data_extractor.py` (300 lines)

**API Endpoint**:
- `POST /api/trm/extract-training-data`

---

### Phase 2: Implement TRM Model (3-4 days)
**Goal**: Build the TRM network for compliance reasoning

**What**: `reasoning_layer/tiny_recursive_reasoner.py`
- TinyComplianceNetwork: 2-layer SwiGLU (7M params)
- RefinementStep: Track intermediate reasoning
- TinyRecursiveReasoner: Orchestrate 16-step loop
- TRMResult: Return full reasoning trace

**Files to Create**:
- `reasoning_layer/tiny_recursive_reasoner.py` (1100 lines)

**Key Features**:
- 16-step refinement with early stopping
- Reasoning trace (human-readable explanation)
- Confidence scores at each step

---

### Phase 3: Training Pipeline (3-4 days)
**Goal**: Train TRM on your compliance data

**What**: `backend/trm_trainer.py`
- ComplianceDataset: Load training data
- TRMTrainer: Deep supervision + EMA regularization
- train_trm_from_compliance_checks(): Main function
- Result: `models/trm_compliance_v1.pt` (trained model)

**Files to Create**:
- `backend/trm_trainer.py` (450 lines)

**API Endpoint**:
- `POST /api/trm/train` (asynchronous)
- `GET /api/trm/train-status/{job_id}`

**Training**:
- 50 epochs, batch size 32
- ~10-15 min on CPU, ~1-2 min on GPU
- Validation accuracy target: > 75%

---

### Phase 4: API & Model Management (3-4 days)
**Goal**: Expose TRM via REST API

**What**: `backend/trm_model_manager.py` + modifications to `app.py`

**Files to Create**:
- `backend/trm_model_manager.py` (200 lines)

**Files to Modify**:
- `backend/app.py` (+250 lines for 5 endpoints)
- `backend/requirements.txt` (+2 packages: torch, numpy)

**New Endpoints**:
1. `POST /api/trm/train` - Start training (async)
2. `GET /api/trm/train-status/{job_id}` - Check training progress
3. `POST /api/trm/analyze` - Single element analysis
4. `POST /api/trm/batch-analyze` - Multiple elements
5. `POST /api/trm/extract-training-data` - Extract labels

**Model Management**:
- Keep last 3 models + current version
- Track training metadata (date, accuracy, samples)
- Support model switching

---

### Phase 5: Frontend Integration (3-4 days)
**Goal**: Visualize TRM reasoning in UI

**Files to Create**:
- `frontend/src/components/TRMVisualization.js` (400 lines)
- `frontend/src/services/trmService.js` (150 lines)

**Files to Modify**:
- `frontend/src/components/ReasoningView.js` (+50 lines)
- `frontend/src/components/ComplianceCheckView.js` (+30 lines)

**New UI**:
1. **4th Tab in ReasoningView**: "TRM Recursive Reasoning"
2. **Visualization Components**:
   - Refinement timeline (steps 1-12)
   - Confidence chart (0.52 → 0.94)
   - Reasoning trace (step-by-step text)
   - Model metadata

3. **User Interactions**:
   - Button: "Run TRM Analysis" (in compliance check view)
   - Dropdown: Select model version
   - Loading indicator during analysis

---

## Data & File Structure

### Training Data Format
```json
{
  "training_samples": [
    {
      "element_features": {
        "guid": "door-001",
        "type": "IfcDoor",
        "name": "Main Entry Door"
      },
      "rule_context": {
        "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
        "name": "Door Minimum Clear Width",
        "severity": "ERROR"
      },
      "compliance_check": {
        "actual_value": 0.95,
        "required_value": 0.92,
        "passed": true
      },
      "trm_target_label": 1
    },
    {...}
  ]
}
```

### Model Storage
```
models/
├── trm_compliance_v1.pt          (28 MB - trained weights)
├── trm_compliance_v1_meta.json   (metadata, accuracy, etc.)
├── trm_compliance_v2.pt
├── trm_compliance_v2_meta.json
└── trm_compliance_v3.pt          (latest)
```

---

## Technology Stack

### Backend
- **Framework**: Flask (existing)
- **ML**: PyTorch (new)
- **Data**: NumPy (new)
- **Dependencies to add**:
  ```
  torch>=2.0.0
  numpy>=1.24.0
  ```

### Frontend
- **Framework**: React (existing)
- **Charts**: Any chart library (Recharts, Chart.js, etc.)
- **HTTP**: Fetch API or Axios (existing)

---

## Key Metrics & Success Criteria

### Phase 1
- ✅ Extract 500+ samples
- ✅ All samples have complete data
- ✅ Can combine multiple IFC files

### Phase 2
- ✅ Model initializes (7M params)
- ✅ 16-step inference works
- ✅ Reasoning trace generated

### Phase 3
- ✅ Training completes without errors
- ✅ Loss decreases over epochs
- ✅ Validation accuracy > 75%

### Phase 4
- ✅ /api/trm/analyze returns TRMResult
- ✅ Inference time < 200ms per element
- ✅ All endpoints working

### Phase 5
- ✅ UI displays without errors
- ✅ Responsive and interactive
- ✅ Reasoning trace readable

---

## API Quick Reference

### Training
```bash
# Start training
curl -X POST http://localhost:5000/api/trm/train \
  -H "Content-Type: application/json" \
  -d '{
    "training_data_file": "data/trm_training_data.json",
    "num_epochs": 50,
    "batch_size": 32
  }'

# Check status
curl http://localhost:5000/api/trm/train-status/trm_train_20251208_143022
```

### Inference
```bash
# Single element
curl -X POST http://localhost:5000/api/trm/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "element_features": {
      "guid": "door-001",
      "type": "IfcDoor",
      "width": 0.95
    },
    "rule_context": {
      "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
      "requirement": 0.92
    }
  }'

# Batch (50 elements)
curl -X POST http://localhost:5000/api/trm/batch-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "graph": {...},
    "rules": [...]
  }'
```

### Data Extraction
```bash
curl -X POST http://localhost:5000/api/trm/extract-training-data \
  -H "Content-Type: application/json" \
  -d '{
    "compliance_results": {...},
    "enrich_with_rules": true
  }'
```

---

## Deployment Checklist

### Before Going Live
- [ ] Train model achieves > 75% validation accuracy
- [ ] All API endpoints tested and working
- [ ] Frontend UI renders without errors
- [ ] Performance acceptable (< 200ms per inference)
- [ ] Error handling works correctly
- [ ] Documentation complete

### Optional Enhancements (Future)
- [ ] GPU support for faster training
- [ ] Model comparison UI (traditional vs TRM)
- [ ] Export reasoning traces as JSON
- [ ] Model performance dashboard
- [ ] A/B testing (when should user trust TRM vs traditional?)

---

## Troubleshooting Guide

### Training Issues
| Problem | Solution |
|---------|----------|
| "Out of memory" | Reduce batch size (32 → 16 or 8) |
| Loss not decreasing | Check learning rate (1e-4 is default) |
| Validation worse than training | Increase dropout (0.2 → 0.3) |
| Training too slow | Use GPU, or reduce dataset size for testing |

### Inference Issues
| Problem | Solution |
|---------|----------|
| Model not found | Train a model first (/api/trm/train) |
| Missing fields error | Check required fields in request |
| Slow inference | Check model is loaded in memory |
| Empty reasoning trace | Check step data is being captured |

### Frontend Issues
| Problem | Solution |
|---------|----------|
| Chart not rendering | Check data format matches Recharts spec |
| Button not responding | Verify API endpoint is reachable |
| UI frozen during analysis | Ensure loading indicator shows |

---

## File Summary

### New Files (7 total)
| File | Size | Purpose |
|------|------|---------|
| `backend/trm_data_extractor.py` | 300 lines | Data preparation |
| `reasoning_layer/tiny_recursive_reasoner.py` | 1100 lines | TRM model |
| `backend/trm_trainer.py` | 450 lines | Training pipeline |
| `backend/trm_model_manager.py` | 200 lines | Model management |
| `frontend/src/components/TRMVisualization.js` | 400 lines | UI visualization |
| `frontend/src/services/trmService.js` | 150 lines | Frontend API calls |
| `docs/[planning files]` | - | Documentation (already created) |

### Modified Files (3 total)
| File | Changes | Purpose |
|------|---------|---------|
| `backend/app.py` | +250 lines | 5 new API endpoints |
| `backend/requirements.txt` | +2 lines | Dependencies (torch, numpy) |
| `frontend/src/components/ReasoningView.js` | +50 lines | Add TRM tab |
| `frontend/src/components/ComplianceCheckView.js` | +30 lines | Add TRM button |

### Generated Files (3 total)
| File | Created by | Purpose |
|------|-----------|---------|
| `data/trm_training_data.json` | /api/trm/extract-training-data | Training samples |
| `models/trm_compliance_v1.pt` | /api/trm/train | Trained model weights |
| `models/trm_compliance_v1_meta.json` | /api/trm/train | Training metadata |

---

## Decision Tree

```
Start Here
    ↓
[Ready to proceed with Phase 1?]
    ├─ NO → Review planning docs and approve decisions
    └─ YES → Proceed to Phase 1
            ↓
        [Phase 1 Complete]
            ↓
        [Ready for Phase 2?]
        ├─ NO → Adjust decisions, restart Phase 1
        └─ YES → Proceed to Phase 2
                ↓
            [Phase 2 Complete]
                ↓
            [Ready for Phase 3?]
            ├─ NO → Modify model architecture
            └─ YES → Proceed to Phase 3
                    ↓
                [Phase 3 Complete - Model Trained!]
                    ↓
                [Ready for Phase 4 (API)?]
                ├─ NO → Test model manually first
                └─ YES → Proceed to Phase 4
                        ↓
                    [Phase 4 Complete]
                        ↓
                    [Ready for Phase 5 (UI)?]
                    ├─ NO → Use APIs directly for testing
                    └─ YES → Proceed to Phase 5
                            ↓
                        [Phase 5 Complete - Launch!]
```

---

## Contact & Support

**During Implementation**:
- If TRM architecture questions → Review tiny_recursive_reasoner.py
- If training questions → Review trm_trainer.py
- If API questions → Check app.py endpoints
- If UI questions → Review TRMVisualization.js

**After Launch**:
- Monitor model performance (test accuracy > 75%?)
- Collect user feedback on reasoning traces
- Consider retraining on new compliance data
- Compare traditional vs TRM decisions

---

## Bottom Line

**In 2-3 weeks** (with sequential approval), you'll have:
1. A trained TRM model on your compliance data
2. 5 REST APIs to use it
3. Beautiful UI visualization of reasoning traces
4. Ability to switch between traditional and TRM-based reasoning

**Cost**: Adding 7M parameters (3 MB) + 28 MB model checkpoint
**Benefit**: Better reasoning for compliance checks + user explainability

---

**Ready to start? Approve the decisions in TRM_DECISIONS_AND_APPROVAL_GATES.md and let's build!**
