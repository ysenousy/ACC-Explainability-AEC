# TRM Implementation - Decisions & Approval Gates

## Overview
This document outlines all major decisions, alternatives considered, and approval gates needed before proceeding with each phase.

---

## Phase 1: Data Extraction

### Decision 1.1: Data Source
**Question**: Where do we get training labels (pass/fail for each element-rule pair)?

**Alternatives**:
- A) Use `/api/compliance/check` endpoint results (current system)
- B) Generate synthetic labels
- C) Manual annotation

**Decision**: **A - Use compliance check endpoint**

**Rationale**:
- ✅ Already computed for every element-rule pair
- ✅ Based on actual rule definitions and IFC data
- ✅ No additional manual effort needed
- ✅ Can accumulate over time (more data = better model)
- ❌ B would be unrealistic (no domain knowledge)
- ❌ C would be slow and expensive

**Approval Gate**: 
- [ ] Confirm: Use compliance check results as training labels?

---

### Decision 1.2: Sample Filtering
**Question**: Should we filter training samples? Which ones to exclude?

**Alternatives**:
- A) Use all compliance results (500+ samples)
- B) Filter out "unable" results (where data was missing)
- C) Require perfect data quality (filter by data_status)

**Decision**: **C - Require data_status='complete'**

**Rationale**:
- ✅ Model learns from high-quality examples
- ✅ Avoids garbage-in-garbage-out
- ✅ Cleaner training signal
- ✅ Reduces bias toward "unknown" predictions
- ❌ Might reduce dataset size (estimate: 60-70% retention)
- ❌ But quality > quantity for small networks

**Impact**: 
- If 500 compliance results total
- ~50% have data_status='missing' (filtered out)
- ~100% have data_status='complete' → ~250-300 training samples
- OR: Run compliance check on more IFC files to get 500+ complete samples

**Approval Gate**:
- [ ] Confirm: Filter to data_status='complete' only?
- [ ] Should we extract from all 3 IFC files (BasicHouse, FZK-Haus, Institute-Var-2)?

---

### Decision 1.3: Data Enrichment
**Question**: Should we load full rule definitions to enrich training data?

**Alternatives**:
- A) Minimal: Just use (element, rule_id, label) → lightweight
- B) Enhanced: Load full rule with parameters, conditions, targets
- C) Maximum: Add context about regulation, jurisdiction, severity

**Decision**: **B - Enhanced with rule definitions**

**Rationale**:
- ✅ More context helps model learn what matters
- ✅ Rule parameters are important for compliance logic
- ✅ Minimal overhead (~10 extra fields per sample)
- ✅ Enables interpretability (can trace decision back to rule params)
- ❌ A would make model less interpretable

**Result**: Each sample includes:
```json
{
  "rule_context": {
    "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
    "name": "Door Minimum Clear Width",
    "target": {"ifc_class": "IfcDoor"},
    "condition": {"op": ">=", "lhs": {...}, "rhs": {...}},
    "parameters": {"min_width": 0.92},
    "severity": "ERROR",
    "regulation": "ADA Standards"
  }
}
```

**Approval Gate**:
- [ ] Confirm: Enrich with full rule definitions?

---

### Decision 1.4: Dataset Split
**Question**: How to split training data into train/val/test?

**Alternatives**:
- A) 80% train, 10% val, 10% test
- B) 70% train, 15% val, 15% test (more validation)
- C) 90% train, 5% val, 5% test (maximizes training data)

**Decision**: **A - 80/10/10**

**Rationale**:
- ✅ Standard split for deep learning
- ✅ Good balance between training and validation
- ✅ 10% test set for unbiased final evaluation
- ✅ If dataset is only 300 samples: 240 train, 30 val, 30 test (still reasonable)
- ❌ C risky if overfitting (hard to detect with small val set)
- ❌ B might slow convergence

**Approval Gate**:
- [ ] Confirm: Use 80/10/10 split?

---

## Phase 2: TRM Model Implementation

### Decision 2.1: Model Architecture
**Question**: Should we use TRM exactly as described in the paper?

**Alternatives**:
- A) Follow paper exactly: 2-layer SwiGLU, 7M params, 16 steps
- B) Simplify: 1-layer network, fewer parameters
- C) Enhance: 3-layer network, more parameters

**Decision**: **A - Follow paper exactly**

**Rationale**:
- ✅ Paper shows this works (beats 671B LLMs on structured tasks)
- ✅ 7M params appropriate for 300-500 training samples (avoid overfitting)
- ✅ 16 steps optimal (paper's finding)
- ✅ SwiGLU proven in modern architectures
- ❌ B might be too simple for complex compliance rules
- ❌ C would overfit on small dataset

**Why 7M params on 300-500 samples?**
- Rule of thumb: 100 samples per million parameters
- We have: 300-500 samples
- Estimate: 3-5M parameters needed
- Paper's 7M: slightly larger, provides safety margin
- With EMA regularization: should be fine

**Approval Gate**:
- [ ] Confirm: Use 2-layer SwiGLU architecture?
- [ ] Confirm: 16 refinement steps?

---

### Decision 2.2: Refinement Steps & Early Stopping
**Question**: How many steps? When to stop early?

**Alternatives**:
- A) Fixed 16 steps, no early stopping
- B) Early stop if confidence converges (Δconf < 0.01)
- C) Early stop if loss converges

**Decision**: **B - Early stop on confidence convergence**

**Rationale**:
- ✅ Inference is faster (12-14 steps vs 16)
- ✅ Still maintains same quality (converged solution)
- ✅ More interpretable (shows convergence point)
- ✅ Paper uses this approach
- ❌ A would waste computation
- ❌ C requires access to training loss (not available at inference)

**Convergence Criteria**:
```
Stop after step t if:
  - confidence[t] - confidence[t-1] < 0.01 AND
  - confidence[t] - confidence[t-2] < 0.01
(Two consecutive steps with < 1% change)
```

**Approval Gate**:
- [ ] Confirm: Early stop on confidence convergence?

---

### Decision 2.3: Feature Embedding
**Question**: How to embed element features and rule context?

**Alternatives**:
- A) Learned embeddings (trainable embedding layers)
- B) Hand-crafted features (domain knowledge)
- C) Hybrid: Mix of learned + hand-crafted

**Decision**: **C - Hybrid approach**

**Rationale**:
- ✅ Learned: IFC class type (categorical) → 32-dim embedding
- ✅ Hand-crafted: Numerical features (width, area) → normalized to [0,1]
- ✅ Learned: Rule severity (categorical) → 16-dim embedding
- ✅ Hand-crafted: Comparison features (actual vs required) → ratios
- ✅ Combines domain knowledge with learned patterns
- ❌ Pure learned might overfit on small dataset
- ❌ Pure hand-crafted might miss important patterns

**Element Features** (128-dim total):
- Type embedding (IfcDoor, IfcSpace, etc.): 32-dim
- Numerical features (width, area, height): 32-dim (normalized)
- Derived features (ratios, relative differences): 32-dim
- Element ID encoding: 32-dim

**Rule Features** (128-dim total):
- Rule severity embedding (ERROR, WARNING, INFO): 16-dim
- Regulation encoding (ADA, IBC, etc.): 32-dim
- Target class embedding (IfcDoor, IfcSpace): 32-dim
- Parameter encoding (min_width, min_area, etc.): 48-dim

**Context Features** (64-dim):
- Comparison operator (>=, <=, ==, etc.): 8-dim
- Data source (QTO, PSet, attribute): 16-dim
- Unit encoding (meters, square-meters, etc.): 16-dim
- Severity level: 24-dim

**Total Input**: 128 + 128 + 64 = 320-dim

**Approval Gate**:
- [ ] Confirm: Use hybrid embedding approach?

---

### Decision 2.4: Output Representation
**Question**: What information should TRM return besides pass/fail?

**Alternatives**:
- A) Just prediction: 0 or 1
- B) Prediction + confidence: (0|1, 0.0-1.0)
- C) Full trace: prediction + confidence + reasoning steps + activations

**Decision**: **C - Full trace for interpretability**

**Rationale**:
- ✅ Transparency: Users can understand why model decided
- ✅ Debugging: Can trace failures to specific steps
- ✅ Trust: Full reasoning trace is more credible
- ✅ Comparison: Can compare with traditional reasoning
- ❌ Larger response size (but still <10KB per result)
- ❌ Slower to generate (but worth it)

**TRMResult Structure**:
```json
{
  "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
  "element_guid": "door-001",
  "final_prediction": 1,
  "confidence": 0.94,
  "num_refinement_steps": 12,
  "reasoning_trace": [
    "Step 1: Detected door element with width 0.95m",
    "Step 2: Loaded ADA rule requiring minimum 0.92m",
    "Step 3: Initial comparison suggests PASS",
    ...
    "Step 12: Converged to PASS with 94% confidence"
  ],
  "refinement_steps": [
    {"step": 1, "prediction": 0, "confidence": 0.52, "activations": {...}},
    {"step": 2, "prediction": 0, "confidence": 0.61, "activations": {...}},
    ...
  ],
  "inference_time_ms": 127
}
```

**Approval Gate**:
- [ ] Confirm: Include full reasoning trace in output?

---

## Phase 3: Training Pipeline

### Decision 3.1: Loss Function
**Question**: What loss function for compliance classification?

**Alternatives**:
- A) Standard CrossEntropy (unweighted)
- B) Weighted CrossEntropy (weight failed cases higher)
- C) Focal Loss (handles class imbalance)

**Decision**: **A - Standard CrossEntropy with Deep Supervision**

**Rationale**:
- ✅ Simple and interpretable
- ✅ Paper uses this
- ✅ Most compliance datasets are balanced (50-50 pass/fail)
- ✅ Deep supervision helps (losses at steps 1, 4, 8, 16)
- ❌ B might over-penalize false positives
- ❌ C more complex (not needed if balanced)

**Deep Supervision Details**:
```
Loss = (L₁ + L₄ + L₈ + L₁₆) / 4

Where:
- L₁ = CrossEntropy(prediction_step_1, label)
- L₄ = CrossEntropy(prediction_step_4, label)
- L₈ = CrossEntropy(prediction_step_8, label)
- L₁₆ = CrossEntropy(prediction_step_16, label)

Purpose:
- Forces learning at ALL refinement levels
- Prevents collapse (all steps predicting same)
- Improves explainability (all steps meaningful)
```

**Approval Gate**:
- [ ] Confirm: Use CrossEntropy with deep supervision?

---

### Decision 3.2: Optimizer
**Question**: Which optimizer for training?

**Alternatives**:
- A) SGD with momentum
- B) Adam
- C) AdamW (Adam with weight decay)

**Decision**: **C - AdamW**

**Rationale**:
- ✅ Modern standard (better than Adam for small models)
- ✅ Weight decay: prevents overfitting on small dataset
- ✅ Works well with deep supervision
- ✅ Paper uses this
- ❌ A slower convergence
- ❌ B no weight decay regularization

**Settings**:
- Learning rate: 1e-4
- Beta1: 0.9
- Beta2: 0.999
- Weight decay: 1e-5
- Warmup: First 5% of training

**Approval Gate**:
- [ ] Confirm: Use AdamW optimizer?

---

### Decision 3.3: Regularization
**Question**: How to prevent overfitting on small dataset?

**Alternatives**:
- A) Dropout layers
- B) Early stopping on validation loss
- C) EMA (Exponential Moving Average) on weights
- D) All three

**Decision**: **D - All three**

**Rationale**:
- ✅ Dropout: 20% in hidden layers (paper recommendation)
- ✅ Early stopping: stop if val_loss increases for 3 epochs
- ✅ EMA: maintain running average of weights, use for evaluation
- ✅ Together: very effective on small datasets
- ✅ Paper uses EMA

**Implementation**:
```python
# Dropout
network = nn.Sequential(
  SwiGLUBlock(320, 256, dropout=0.2),
  SwiGLUBlock(256, 256, dropout=0.2),
  nn.Linear(256, 2)
)

# Early stopping
best_val_loss = float('inf')
patience_counter = 0
for epoch in range(num_epochs):
  train_loss = train_one_epoch()
  val_loss = validate()
  
  if val_loss < best_val_loss:
    best_val_loss = val_loss
    patience_counter = 0
    save_checkpoint()
  else:
    patience_counter += 1
    if patience_counter >= 3:
      break  # Early stop

# EMA
ema_model = EMA(network, decay=0.999)
for batch in dataloader:
  loss = train_step(network, batch)
  backward(loss)
  optimizer.step()
  ema_model.update()  # Update running average
```

**Approval Gate**:
- [ ] Confirm: Use dropout + early stopping + EMA?

---

### Decision 3.4: Training Schedule
**Question**: How long to train? How many epochs?

**Alternatives**:
- A) 20 epochs (fast, might underfit)
- B) 50 epochs (standard, good balance)
- C) 100+ epochs (slow, risk of overfitting)

**Decision**: **B - 50 epochs**

**Rationale**:
- ✅ With early stopping, will stop when validation plateaus
- ✅ Allows time to converge (small learning rate)
- ✅ ~50 epoch iterations with batches of 32 → lots of data exposure
- ✅ Early stopping prevents overfitting
- ✅ Paper uses similar schedule
- ❌ A might be too short
- ❌ C wastes time (early stop will prevent)

**Batch Processing**:
- Batch size: 32 (balance between speed and stability)
- If dataset = 300 samples:
  - Train set = 240 samples
  - Batches per epoch = 240 / 32 = 7.5 → 8 batches
  - Total forward passes = 50 epochs × 8 batches × 16 steps = 6,400
  - Training time: ~10-15 min (CPU), ~1-2 min (GPU)

**Approval Gate**:
- [ ] Confirm: 50 epochs with early stopping?
- [ ] Confirm: Batch size = 32?

---

## Phase 4: API Endpoints

### Decision 4.1: Synchronous vs Asynchronous Training
**Question**: Should /api/trm/train be blocking or non-blocking?

**Alternatives**:
- A) Synchronous: Block until training completes, return result
- B) Asynchronous: Return job ID immediately, poll for status
- C) Background: Start training, return job ID, endpoint for checking status

**Decision**: **B - Asynchronous with polling**

**Rationale**:
- ✅ Training takes 10-15 min → can't block HTTP request
- ✅ User can check progress without blocking UI
- ✅ Better UX: progress bar instead of hanging
- ✅ Can cancel training if needed
- ✅ Aligns with modern REST practices
- ❌ A doesn't work for long operations
- ❌ C requires background job system (more complex)

**Implementation**:
```
POST /api/trm/train
{
  "training_data_file": "data/trm_training_data.json",
  "num_epochs": 50
}

Response (immediate):
{
  "job_id": "trm_train_20251208_143022",
  "status": "started",
  "message": "Training started"
}

GET /api/trm/train-status/{job_id}
Response:
{
  "job_id": "trm_train_20251208_143022",
  "status": "in_progress",
  "progress": {
    "epoch": 23,
    "total_epochs": 50,
    "batch": 5,
    "total_batches": 8,
    "loss": 0.31,
    "val_loss": 0.28,
    "estimated_time_remaining_minutes": 8
  }
}

GET /api/trm/train-status/{job_id}
Response (after complete):
{
  "job_id": "trm_train_20251208_143022",
  "status": "completed",
  "result": {
    "model_path": "models/trm_compliance_v1.pt",
    "training_metrics": {...},
    "test_accuracy": 0.87
  }
}
```

**Approval Gate**:
- [ ] Confirm: Asynchronous training with polling?

---

### Decision 4.2: Model Versioning
**Question**: How many trained models to keep?

**Alternatives**:
- A) Keep only latest model (simple, but lose history)
- B) Keep all models (lots of storage, but full history)
- C) Keep last 3 models + latest (balance)

**Decision**: **C - Keep last 3 models + always latest**

**Rationale**:
- ✅ Can compare different trained models
- ✅ Can rollback if new model is worse
- ✅ Limited storage (~100 MB total for 4 models)
- ✅ Versioning: trm_compliance_v1, v2, v3, v4_latest
- ❌ A loses useful comparison data
- ❌ B storage overkill

**Model Storage Structure**:
```
models/
├── trm_compliance_v1.pt
├── trm_compliance_v1_meta.json
│   {
│     "version": 1,
│     "created_at": "2025-12-08T14:30:00",
│     "training_samples": 300,
│     "epochs_trained": 42,
│     "final_train_loss": 0.18,
│     "final_val_loss": 0.22,
│     "test_accuracy": 0.86,
│     "params": {
│       "batch_size": 32,
│       "learning_rate": 0.0001
│     }
│   }
├── trm_compliance_v2.pt
├── trm_compliance_v2_meta.json
├── trm_compliance_v3.pt
├── trm_compliance_v3_meta.json
└── trm_compliance_latest_symlink → v3.pt
```

**Approval Gate**:
- [ ] Confirm: Keep last 3 models + current?

---

### Decision 4.3: Error Handling
**Question**: What if TRM analysis fails during inference?

**Alternatives**:
- A) Return error (400/500 status)
- B) Graceful fallback to traditional reasoning
- C) Return partial result (prediction only, no trace)

**Decision**: **A - Return error with diagnostics**

**Rationale**:
- ✅ Clear signal to frontend that TRM failed
- ✅ Return helpful error message for debugging
- ✅ Don't mask problems with fallback
- ✅ Frontend can decide how to handle
- ❌ B hides real issues
- ❌ C returns inconsistent result format

**Error Responses**:
```json
{
  "success": false,
  "error": "Model file not found: models/trm_compliance_v1.pt",
  "error_type": "model_loading_error",
  "message": "Train a model first using /api/trm/train",
  "http_status": 404
}

{
  "success": false,
  "error": "Missing required field: element_features",
  "error_type": "validation_error",
  "required_fields": ["element_features", "rule_context"],
  "http_status": 400
}

{
  "success": false,
  "error": "Model inference failed: OOM",
  "error_type": "runtime_error",
  "details": "Ran out of memory during forward pass",
  "http_status": 500
}
```

**Approval Gate**:
- [ ] Confirm: Return errors with diagnostics?

---

## Phase 5: Frontend Integration

### Decision 5.1: Tab Placement
**Question**: Where to add TRM tab in ReasoningView?

**Alternatives**:
- A) Replace existing tabs with TRM
- B) Add as 4th tab (after "How To Fix")
- C) Add as modal/popup
- D) Add as sidebar panel

**Decision**: **B - Add as 4th tab**

**Rationale**:
- ✅ Consistent with existing UI (3 tabs → 4 tabs)
- ✅ Same navigation pattern
- ✅ Easy to discover
- ✅ Logical order: Why Failed → Impact → How to Fix → Reasoning Trace
- ❌ A would remove traditional reasoning (keep both!)
- ❌ C/D less discoverable

**Tab Order**:
1. Why It Failed (FailureExplainer)
2. Impact Assessment (ImpactAnalyzer)
3. How To Fix (RecommendationEngine)
4. **TRM Recursive Reasoning** (TinyRecursiveReasoner) ← NEW

**Approval Gate**:
- [ ] Confirm: Add as 4th tab?

---

### Decision 5.2: Data Loading
**Question**: When should TRM analysis run?

**Alternatives**:
- A) Automatically when compliance check completes
- B) User clicks "Run TRM Analysis" button
- C) Optional toggle in compliance check
- D) Only when explicitly requested via API

**Decision**: **B - User-initiated with button**

**Rationale**:
- ✅ TRM inference adds 100-200ms per element
- ✅ User controls when to spend that time
- ✅ Can skip if not needed (cost/benefit)
- ✅ Clear user intent
- ❌ A wastes computation if not interested
- ❌ C changes compliance check behavior (risky)
- ❌ D requires knowing about API

**UI Flow**:
```
1. Run compliance check
   ↓
2. Results show (traditional reasoning)
3. [TRM Reasoning Tab] appears (disabled/empty)
4. User clicks "Run TRM Analysis" button
   ↓
5. Loading indicator
   ↓
6. TRM results display in tab
```

**Approval Gate**:
- [ ] Confirm: User-initiated with button?

---

### Decision 5.3: Visualization Components
**Question**: What to visualize in TRM tab?

**Alternatives**:
- A) Minimal: Just reasoning trace text
- B) Standard: Trace + confidence chart + timeline
- C) Rich: B + heatmap + activation visualization
- D) Expert: C + step-by-step debugging interface

**Decision**: **B - Standard visualization**

**Rationale**:
- ✅ Covers main uses: understanding reasoning flow + confidence
- ✅ Not overwhelming for most users
- ✅ Fast to implement
- ✅ Charts are clear and interpretable
- ❌ A lacks visual understanding
- ❌ C/D more complex, diminishing returns

**TRMVisualization Components**:
```javascript
<TRMVisualization>
  ├─ <RefinementTimeline />           ← Steps 1-12 with colors
  ├─ <ConfidenceChart />              ← Line chart: confidence over steps
  ├─ <ReasoningTrace />               ← Step-by-step text
  └─ <ModelMetadata />                ← Model version, inference time
```

**Approval Gate**:
- [ ] Confirm: Include timeline + chart + trace?

---

### Decision 5.4: Model Selection UI
**Question**: How should users select which model to use?

**Alternatives**:
- A) Automatic: Always use latest trained model
- B) Dropdown: Select from available models
- C) Default to latest, allow manual override

**Decision**: **C - Default to latest with manual override**

**Rationale**:
- ✅ Most users want latest (simplest)
- ✅ Advanced users can compare models if needed
- ✅ Shows model version + metadata
- ✅ Helps debug if new model is worse
- ❌ A inflexible
- ❌ B too many choices for most users

**UI**:
```javascript
<ModelSelector defaultModel="latest">
  <select>
    <option>Latest (trm_compliance_v3) - Acc: 87%</option>
    <option>v2 - Acc: 84%</option>
    <option>v1 - Acc: 81%</option>
  </select>
</ModelSelector>
```

**Approval Gate**:
- [ ] Confirm: Default to latest with manual override?

---

## Summary of Decisions

| Phase | Decision | Chosen | Status |
|-------|----------|--------|--------|
| 1 | Data source | Compliance check results | ✓ |
| 1 | Sample filtering | data_status='complete' | ✓ |
| 1 | Data enrichment | Full rule definitions | ✓ |
| 1 | Dataset split | 80/10/10 | ✓ |
| 2 | Architecture | 2-layer SwiGLU | ✓ |
| 2 | Refinement steps | 16 with early stopping | ✓ |
| 2 | Embeddings | Hybrid learned+hand-crafted | ✓ |
| 2 | Output | Full trace | ✓ |
| 3 | Loss | CrossEntropy + deep supervision | ✓ |
| 3 | Optimizer | AdamW | ✓ |
| 3 | Regularization | Dropout + early stop + EMA | ✓ |
| 3 | Training | 50 epochs, batch 32 | ✓ |
| 4 | Training API | Asynchronous with polling | ✓ |
| 4 | Model versioning | Keep last 3 + latest | ✓ |
| 4 | Error handling | Return errors with diagnostics | ✓ |
| 5 | Tab placement | Add as 4th tab | ✓ |
| 5 | When to run | User-initiated button | ✓ |
| 5 | Visualization | Timeline + chart + trace | ✓ |
| 5 | Model selection | Default latest + override | ✓ |

---

## Approval Gates (Sequential)

```
Gate 1: Approve Phase 1 (Data Extraction)
├─ [ ] Use compliance check results as labels?
├─ [ ] Filter to complete data only?
├─ [ ] Enrich with rule definitions?
├─ [ ] Extract from all 3 IFC files?
└─ [ ] Use 80/10/10 split?

Gate 2: Approve Phase 2 (TRM Model)
├─ [ ] Use 2-layer SwiGLU architecture?
├─ [ ] Use 16 steps with early stopping?
├─ [ ] Use hybrid embeddings?
└─ [ ] Include full reasoning trace?

Gate 3: Approve Phase 3 (Training)
├─ [ ] Use CrossEntropy + deep supervision?
├─ [ ] Use AdamW optimizer?
├─ [ ] Use dropout + early stop + EMA?
└─ [ ] Use 50 epochs with batch=32?

Gate 4: Approve Phase 4 (API)
├─ [ ] Use asynchronous training?
├─ [ ] Keep 3 models + latest?
└─ [ ] Return errors with diagnostics?

Gate 5: Approve Phase 5 (Frontend)
├─ [ ] Add as 4th tab?
├─ [ ] User-initiated with button?
├─ [ ] Timeline + chart + trace?
└─ [ ] Default to latest model?
```

---

## Next Steps

1. **Review this document** - Do all decisions align with your vision?
2. **Approve/modify decisions** - Any changes to the plan?
3. **Gate 1 decision** - Should I proceed with Phase 1 (data extraction)?
4. **Sequential approval** - Each phase waits for approval before proceeding
5. **Implementation** - Once approved, implement each phase following this spec

**Estimated Timeline**:
- Phase 1 (Data): 2-3 days ✓ (once approved)
- Phase 2 (Model): 2-3 days ✓ (once approved)
- Phase 3 (Training): 2-3 days ✓ (once approved)
- Phase 4 (API): 3-4 days ✓ (once approved)
- Phase 5 (Frontend): 3-4 days ✓ (once approved)
- **Total**: 12-17 days (with sequential approval & implementation)

**Alternative Timeline** (if all approved upfront):
- All phases in parallel planning: 2 days
- Sequential implementation: 10-12 days
- **Total**: ~2 weeks

---

## Questions for You

Before proceeding:

1. **Data Strategy**: Are you comfortable using compliance check results as training labels, or prefer a different data source?

2. **Model Scope**: Should TRM enhance traditional reasoning, or replace it in certain scenarios?

3. **Frontend Priority**: Is visualization important to you, or just the predictions?

4. **Timeline**: Can wait 2-3 weeks for full implementation, or prefer MVP in 1 week?

5. **Hardware**: Do you have GPU access for faster training, or CPU-only?

6. **Rollout**: Should TRM be optional (users enable it), or default behavior?

---

**Ready to proceed when you approve the decisions and gates above!**
