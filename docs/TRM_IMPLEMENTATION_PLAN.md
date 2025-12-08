# TRM Implementation Plan - Detailed Architecture

## Executive Summary
Integrate Tiny Recursive Model (TRM) from arXiv:2510.04871 into the ACC-Explainability-AEC framework. TRM will add iterative refinement reasoning to compliance checking, enabling the system to learn compliance patterns and provide multi-step reasoning explanations.

---

## 1. BACKEND ARCHITECTURE

### 1.1 Data Pipeline (Phase 1)

**Location**: `backend/trm_data_extractor.py` (NEW)

**Purpose**: Convert compliance check results into TRM training format

**Components**:
- `ComplianceCheckToTRMConverter`: Single compliance check → training samples
  - Input: `/api/compliance/check` JSON output
  - Output: Standardized training samples with element features, rule context, pass/fail labels
  - Filters: Only use samples with complete data (data_status='complete')

- `ComplianceDatasetBuilder`: Multiple compliance results → full training dataset
  - Accumulate samples from multiple compliance checks (different IFC files, rule sets)
  - Split into train/val/test (80/10/10)
  - Save as `data/trm_training_data.json`

**Data Structure**:
```json
{
  "training_samples": [
    {
      "element_features": {
        "guid": "door-001",
        "type": "IfcDoor",
        "name": "Main Entry Door",
        "ifc_class": "IfcDoor"
      },
      "rule_context": {
        "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
        "name": "Door Minimum Clear Width",
        "severity": "ERROR",
        "regulation": "ADA Standards",
        "target": {...},
        "condition": {...},
        "parameters": {...}
      },
      "compliance_check": {
        "actual_value": 0.95,
        "required_value": 0.92,
        "unit": "m",
        "passed": true,
        "data_source": "qto:Qto_DoorOpeningProperties.ClearOpeningWidth"
      },
      "trm_target_label": 1
    }
  ],
  "metadata": {...}
}
```

**Dependencies to add to requirements.txt**:
- `torch>=2.0.0` (PyTorch for model)
- `numpy>=1.24.0` (Array operations)

---

### 1.2 TRM Model Implementation (Phase 2)

**Location**: `reasoning_layer/tiny_recursive_reasoner.py` (NEW)

**Purpose**: Core TRM model for iterative compliance reasoning

**Components**:

**A. `TinyComplianceNetwork`** (2-layer SwiGLU network)
- Input: [element_embedding (128), rule_embedding (128), context_embedding (64)]
  = 320-dim input vector
- Layer 1: 320 → 256 (SwiGLU with gating)
- Layer 2: 256 → 2 (logits for pass/fail)
- Parameters: ~7M (matches paper)
- Output: Class probabilities + intermediate activations for explainability

**B. `RefinementStep`** (Single iteration state)
- Tracks: input, output, attention weights, activation maps
- Purpose: Explainability - show reasoning evolution over iterations
- Storage: All 16 steps kept for visualization

**C. `TinyRecursiveReasoner`** (Main inference engine)
- Orchestrates 16 iterative refinement steps
- Each step: network(previous_output, element, rule)
- Convergence: Early stop if confidence stabilizes (< 0.01 change)
- Outputs: `TRMResult` with:
  - `final_prediction`: 0 or 1 (pass/fail)
  - `confidence`: 0.0-1.0 (certainty score)
  - `refinement_steps`: List of 16 RefinementStep objects
  - `reasoning_trace`: Human-readable step-by-step reasoning

**D. `TRMResult`** (Return type)
```python
{
  'rule_id': 'ADA_DOOR_MIN_CLEAR_WIDTH',
  'element_guid': 'door-001',
  'final_prediction': 1,  # 0=fail, 1=pass
  'confidence': 0.95,
  'num_refinement_steps': 12,  # Early stopped at step 12
  'reasoning_trace': [
    "Step 1: Initial assessment - door width 0.95m detected",
    "Step 2: Comparing with requirement 0.92m",
    "Step 3: Refined understanding - actual > required",
    ...
    "Step 12: High confidence in pass - converged"
  ],
  'refinement_steps': [...],  # Full intermediate states
  'inference_time_ms': 125
}
```

---

### 1.3 TRM Training Pipeline (Phase 3)

**Location**: `backend/trm_trainer.py` (NEW)

**Purpose**: Train TRM model on compliance data

**Components**:

**A. `ComplianceDataset`** (PyTorch Dataset)
- Input: training_data.json from Phase 1
- Output: Batches of (element_tensor, rule_tensor, label)
- Features extraction:
  - Element: [area, perimeter, dimensions, properties, type_encoding] → 128-dim
  - Rule: [parameters, severity_encoding, regulation_encoding] → 128-dim
  - Context: [element_type, rule_type, severity] → 64-dim

**B. `TRMTrainer`** (Training orchestrator)
- Loss: Deep supervision (losses at steps 1, 4, 8, 16)
- Optimizer: AdamW with LR=1e-4
- Regularization: EMA (exponential moving average) on weights
- Batch size: 32
- Epochs: 50 (with early stopping on validation)
- Validation: Run on val_set every epoch

**C. `train_trm_from_compliance_checks()`** (Main training function)
```python
def train_trm_from_compliance_checks(
    training_data_file: str,
    output_model_path: str = 'models/trm_compliance_v1.pt',
    num_epochs: int = 50,
    batch_size: int = 32,
    device: str = 'cpu'
) -> Dict[str, Any]
```

- Returns: `{'success': bool, 'model_path': str, 'metrics': {...}}`

**Training Flow**:
1. Load training data from JSON
2. Create PyTorch Dataset with train/val/test splits
3. Initialize TinyRecursiveReasoner + TinyComplianceNetwork
4. For each epoch:
   - Forward pass with 16-step recursion
   - Compute deep supervision losses
   - Backward pass with EMA update
   - Validate on val_set
   - Save best model (by val loss)
5. Final test on test_set
6. Save model checkpoint with metadata

---

### 1.4 API Endpoints (Phase 4)

**Location**: `backend/app.py` (MODIFICATIONS)

**A. New Endpoint: `/api/trm/train`**
```
POST /api/trm/train
Body: {
  "training_data_file": "path/to/training_data.json",
  "num_epochs": 50,
  "batch_size": 32,
  "device": "cpu" | "cuda"
}
Response: {
  "success": bool,
  "message": str,
  "model_path": str,
  "training_metrics": {...},
  "estimated_time_remaining_seconds": int
}
```

**B. New Endpoint: `/api/trm/analyze`**
```
POST /api/trm/analyze
Body: {
  "element_features": {...},    # from IFC element
  "rule_context": {...},         # from rule definition
  "model_path": "models/trm_compliance_v1.pt"
}
Response: TRMResult JSON
{
  "rule_id": str,
  "element_guid": str,
  "final_prediction": 0|1,
  "confidence": float,
  "refinement_steps": int,
  "reasoning_trace": [str],
  "inference_time_ms": float
}
```

**C. New Endpoint: `/api/trm/batch-analyze`**
```
POST /api/trm/batch-analyze
Body: {
  "graph": {...},                    # IFC graph
  "rules": [...],                    # Rule definitions
  "model_path": "models/trm_compliance_v1.pt"
}
Response: {
  "success": bool,
  "results": [TRMResult, ...],
  "statistics": {
    "total_analyzed": int,
    "average_confidence": float,
    "total_time_ms": int
  }
}
```

**D. New Endpoint: `/api/trm/extract-training-data`**
```
POST /api/trm/extract-training-data
Body: {
  "compliance_results": {...},   # from /api/compliance/check
  "enrich_with_rules": bool      # Load full rule definitions
}
Response: {
  "success": bool,
  "training_samples": [{...}],
  "samples_created": int,
  "samples_filtered": int,
  "metadata": {...}
}
```

**E. Modified Endpoint: `/api/reasoning/enrich-compliance` (ENHANCEMENT)**
- Add optional `include_trm_analysis: bool`
- If true, run TRM analysis and include in response
- Return both traditional reasoning + TRM iterative refinement

---

### 1.5 Model Checkpoint Management (Phase 5)

**Location**: `backend/trm_model_manager.py` (NEW)

**Purpose**: Load, save, and version control TRM models

**Components**:
- `TRMModelManager`
  - `load_model(path)`: Load saved TRM from checkpoint
  - `save_model(model, path, metadata)`: Save with training metrics
  - `list_available_models()`: Show all trained models
  - `get_model_info(path)`: Return training metadata
  - `delete_model(path)`: Clean up old models

**Model Storage**:
```
models/
├── trm_compliance_v1.pt        # Actual weights
├── trm_compliance_v1_meta.json # Metadata (creation date, accuracy, etc.)
├── trm_compliance_v2.pt
├── trm_compliance_v2_meta.json
└── ...
```

---

## 2. FRONTEND ARCHITECTURE

### 2.1 UI Components

**Location**: `frontend/src/components/TRMVisualization.js` (NEW)

**Purpose**: Display TRM refinement trace and reasoning evolution

**Features**:
1. **Refinement Steps Timeline**
   - Visual timeline showing 16 steps
   - Each step: step number, confidence score, key reasoning
   - Color coding: red (fail) → green (pass)
   - Interactive: hover to see full step details

2. **Confidence Progression Chart**
   - Line chart: confidence over 16 steps
   - Show convergence point (where early-stop occurred)
   - Highlight: final confidence level

3. **Reasoning Trace Text**
   - Step-by-step natural language explanation
   - Example:
     ```
     Step 1: Initial assessment - door width 0.95m detected
     Step 2: Rule context loaded - ADA standard requires 0.92m
     Step 3: Comparison starts - evaluating 0.95m vs 0.92m
     Step 4: First refinement - actual exceeds requirement
     ...
     Step 12: Convergence achieved - very confident in PASS
     ```

4. **Intermediate Activations Heatmap**
   - Show which rule features were most important
   - Attention weights visualization
   - Help explain "why" the model reached this conclusion

---

### 2.2 Integration Points

**A. In `ReasoningView.js`** (MODIFICATION)
- Add 4th tab: "TRM Recursive Reasoning" (after "How To Fix")
- New tab content: `<TRMVisualization />`
- Toggle: Show/hide TRM analysis

**B. New Component: `TRMComparisonPanel.js` (OPTIONAL)**
- Side-by-side comparison: Traditional reasoning vs TRM reasoning
- Show how both approaches reach same/different conclusions
- Useful for validation and understanding model behavior

**C. In `ComplianceCheckView.js`** (MODIFICATION)
- Add button: "Run TRM Analysis" (if model is trained)
- Checkbox: "Include TRM reasoning in results"
- Loading indicator during TRM inference

---

### 2.3 Service Layer

**Location**: `frontend/src/services/trmService.js` (NEW)

```javascript
class TRMService {
  // Training
  async trainTRM(trainingDataFile, epochs, batchSize, device)
  async getTrainingStatus()
  async cancelTraining()
  
  // Inference
  async analyzeWithTRM(elementFeatures, ruleContext, modelPath)
  async batchAnalyzeWithTRM(graph, rules, modelPath)
  
  // Model Management
  async listAvailableModels()
  async getModelInfo(modelPath)
  async deleteModel(modelPath)
  
  // Data Extraction
  async extractTrainingData(complianceResults, enrichWithRules)
}
```

---

## 3. DATA FLOW DIAGRAMS

### 3.1 Training Data Flow
```
IFC Files (3 files)
    ↓
[Run compliance check on each file]
    ↓
Compliance Results (pass/fail for each element-rule pair)
    ↓
[/api/trm/extract-training-data endpoint]
    ↓
Training Samples (element + rule + label)
    ↓
[Combine from all files → train/val/test split]
    ↓
training_data.json (500-1000 samples)
    ↓
[/api/trm/train endpoint]
    ↓
TRM Model (7M params) + Checkpoint
```

### 3.2 Inference Flow (Single Element-Rule Pair)
```
Element Properties (width, area, etc.)
Rule Definition (parameters, requirements)
    ↓ [Embed]
Element Vector (128-dim) + Rule Vector (128-dim)
    ↓ [16-step recursion]
Step 1: Initial prediction + confidence
Step 2: Refined with attention
Step 3: Updated understanding
... (early stop if converged)
    ↓
TRMResult {
  prediction: 0|1,
  confidence: 0.95,
  steps: 12,
  trace: ["Step 1: ...", "Step 2: ..."],
  reasoning: {...}
}
    ↓ [Send to Frontend]
Visualization: Timeline + Trace
```

### 3.3 Full Compliance Check with TRM
```
IFC Graph + Rules
    ↓ [/api/compliance/check]
Compliance Results (traditional: passed, failed, unable)
    ↓ (Optional) [Run TRM on each result]
For each (element, rule) pair:
  → /api/trm/analyze
  → TRMResult
    ↓
Enhanced Response {
  compliance_results: [...],
  trm_analysis: [TRMResult, ...],
  comparison: {
    agreed: int,
    disagreed: int,
    confidence_avg: float
  }
}
```

---

## 4. IMPLEMENTATION PHASES

### Phase 1: Data Extraction (Week 1)
**Deliverables**:
- `backend/trm_data_extractor.py`
- `/api/trm/extract-training-data` endpoint
- `data/trm_training_data.json` (sample extracted data)

**Tasks**:
1. Create ComplianceCheckToTRMConverter class
2. Create ComplianceDatasetBuilder class
3. Add endpoint to app.py
4. Test on BasicHouse.ifc compliance results

**Success Criteria**:
- Extract 100+ training samples from 1 IFC file
- Samples have complete data (no missing values)
- Can batch multiple IFC files together

---

### Phase 2: TRM Model Implementation (Week 2)
**Deliverables**:
- `reasoning_layer/tiny_recursive_reasoner.py`
- TinyComplianceNetwork, RefinementStep, TinyRecursiveReasoner classes
- Unit tests for inference

**Tasks**:
1. Implement TinyComplianceNetwork (2-layer SwiGLU)
2. Implement 16-step refinement loop
3. Add early stopping logic
4. Create RefinementStep tracking
5. Test on dummy data (10 samples)

**Success Criteria**:
- Model runs inference on element-rule pair in <500ms
- Produces reasoning trace
- Tracks all 16 steps
- Early stops when converged

---

### Phase 3: Training Pipeline (Week 2-3)
**Deliverables**:
- `backend/trm_trainer.py`
- `/api/trm/train` endpoint
- First trained model checkpoint

**Tasks**:
1. Create ComplianceDataset class
2. Create TRMTrainer class with deep supervision
3. Implement train_trm_from_compliance_checks() function
4. Add training endpoint to app.py
5. Train on extracted data (100-500 samples)

**Success Criteria**:
- Model trains without errors
- Loss decreases over epochs
- Validation accuracy > 75%
- Model saved as checkpoint
- Training takes <5 min on CPU (10-20 min on large dataset)

---

### Phase 4: API Endpoints (Week 3)
**Deliverables**:
- `/api/trm/analyze` endpoint
- `/api/trm/batch-analyze` endpoint
- `backend/trm_model_manager.py`

**Tasks**:
1. Create TRMModelManager class
2. Add analyze endpoint
3. Add batch-analyze endpoint
4. Add model listing/info endpoints
5. Test endpoints with trained model

**Success Criteria**:
- Single element analysis returns TRMResult
- Batch analysis processes graph of 50 elements
- Model can be loaded from checkpoint
- Response time <200ms per element

---

### Phase 5: Frontend Integration (Week 3-4)
**Deliverables**:
- `frontend/src/components/TRMVisualization.js`
- `frontend/src/services/trmService.js`
- Modified `ReasoningView.js` with TRM tab
- Modified `ComplianceCheckView.js` with TRM button

**Tasks**:
1. Create TRMVisualization component
2. Create TRMService
3. Add TRM tab to ReasoningView
4. Add TRM analysis button to ComplianceCheckView
5. Connect endpoints and test UI flow

**Success Criteria**:
- TRM tab shows refinement timeline
- Confidence chart renders correctly
- Reasoning trace displays step-by-step
- Loading indicator during analysis
- No UI errors

---

### Phase 6: Enhancements (Week 4)
**Optional/Future**:
- TRMComparisonPanel (traditional vs TRM reasoning)
- Export reasoning traces as JSON
- Model versioning UI
- Model performance dashboard
- Batch training on multiple IFC files

---

## 5. INTEGRATION CHECKLIST

### Backend
- [ ] Add torch, numpy to requirements.txt
- [ ] Create trm_data_extractor.py
- [ ] Create tiny_recursive_reasoner.py
- [ ] Create trm_trainer.py
- [ ] Create trm_model_manager.py
- [ ] Add 5 new API endpoints to app.py
- [ ] Test all endpoints

### Frontend
- [ ] Create TRMVisualization.js component
- [ ] Create trmService.js service
- [ ] Modify ReasoningView.js (add tab)
- [ ] Modify ComplianceCheckView.js (add button)
- [ ] Test all components
- [ ] Style TRM components

### Data
- [ ] Extract training data from BasicHouse.ifc
- [ ] Extract training data from AC20-FZK-Haus.ifc
- [ ] Extract training data from AC20-Institute-Var-2.ifc
- [ ] Save to data/trm_training_data.json
- [ ] Train first model: trm_compliance_v1.pt

### Testing
- [ ] Unit tests for TRM components
- [ ] Integration tests for API endpoints
- [ ] End-to-end test: IFC → compliance → TRM analysis → visualization

---

## 6. DEPLOYMENT CONSIDERATIONS

### Model Storage
- Store trained models in `models/` directory
- Include metadata: training date, accuracy, dataset size
- Support multiple model versions for comparison

### Performance
- TRM inference: ~100-200ms per element (16 steps)
- Batch processing: 10 elements/sec on CPU
- Consider GPU support for faster training (10x speedup)

### Scalability
- Current approach: train on 500-1000 compliance samples
- Scaling: Can train on 10K+ samples (ADA, IBC rules)
- Future: Fine-tune on domain-specific rules

### Error Handling
- Missing element properties → skip sample during training
- Failed inference → return error with diagnostics
- Model not found → graceful fallback to traditional reasoning

---

## 7. SUCCESS METRICS

**Training Success**:
- [ ] Extract 500+ training samples
- [ ] Model converges (loss decreases >10%)
- [ ] Validation accuracy > 75%

**Inference Success**:
- [ ] Single element analysis < 200ms
- [ ] Batch analysis < 2s for 10 elements
- [ ] Reasoning trace makes sense to users

**Integration Success**:
- [ ] Frontend displays TRM results correctly
- [ ] No backend errors in logs
- [ ] API response times acceptable
- [ ] Users can trigger TRM analysis

---

## 8. TECHNICAL DECISIONS & RATIONALE

### Why 7M Parameters?
- Paper shows 7M TRM beats 671B LLMs on structured reasoning
- Small enough to train on compliance data (500-1000 samples)
- Fast inference (~100ms per element)

### Why 16 Refinement Steps?
- Paper's sweet spot: more steps = better reasoning, with diminishing returns
- 16 steps: good balance between accuracy and speed
- Early stopping: stop if converged before step 16

### Why Deep Supervision?
- Losses at steps 1, 4, 8, 16 force learning at all refinement levels
- Prevents collapse (all steps predicting same thing)
- Improves explanation quality

### Why EMA (Exponential Moving Average)?
- Stabilizes training
- Reduces overfitting
- Standard in modern deep learning

### Why SwiGLU Activation?
- Better than ReLU for small networks
- Improves learning efficiency on small datasets
- Used in language models (e.g., PaLM)

---

## 9. ROLLBACK PLAN

If TRM implementation causes issues:

1. **Frontend**: Remove TRM tab from ReasoningView - 5 min
2. **Backend**: Disable TRM endpoints - 5 min
3. **Models**: Delete model checkpoints - 1 min
4. **Data**: Keep training data extraction as utility (useful standalone)

No modifications to compliance checking, so main system unaffected.

---

## 10. NEXT STEPS (AWAITING PERMISSION)

1. **Phase 1 Approval**: Can I create data extraction components?
2. **Phase 2 Approval**: Can I implement TRM model?
3. **Phase 3 Approval**: Can I create training pipeline?
4. **Phase 4+ Approval**: Can I add API endpoints and frontend?

Each phase can proceed independently once approved.
