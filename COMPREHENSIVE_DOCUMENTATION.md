# ACC-Explainability-AEC: Comprehensive Application Documentation

**Last Updated:** January 22, 2026

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Technology Stack](#technology-stack)
5. [Installation & Setup](#installation--setup)
6. [API Reference](#api-reference)
7. [Data Flow](#data-flow)
8. [Key Features](#key-features)
9. [Configuration](#configuration)
10. [Development Guide](#development-guide)
11. [Troubleshooting](#troubleshooting)

---

## Project Overview

**ACC-Explainability-AEC** is an intelligent Building Compliance Checking and Explainability System designed for Architecture, Engineering & Construction (AEC) professionals. The application analyzes IFC (Industry Foundation Classes) building models, validates them against regulatory compliance rules, and provides explainable AI-driven insights into why buildings pass or fail compliance checks.

### Key Objectives

- **Automated Compliance Checking**: Validate building designs against regulatory rules automatically
- **Explainability**: Provide clear, understandable explanations for compliance failures
- **Trainable Model**: Learn from compliance patterns using the TinyRecursiveReasoner (TRM) model
- **Rule Management**: Support both built-in and custom compliance rules
- **Version Control**: Track model and rule versions for reproducibility

### Problem Solved

The application addresses the "70% Accuracy Problem"—where machine learning models were predicting identical accuracy across all building files due to missing dimensional data in training features. The solution involves ensuring that the complete graph (with accurate element dimensions) is included when adding training samples, enabling the model to learn real patterns.

---

## Architecture

The system is built on a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React)                            │
│  - IFC File Viewer & Inspector                                  │
│  - Compliance Results Dashboard                                 │
│  - Explanation & Reasoning Display                              │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────────┐
│              Backend API Layer (Flask)                           │
│  - /api/ifc/* → IFC Processing                                  │
│  - /api/compliance/* → Rule Execution                           │
│  - /api/reasoning/* → Explainability                            │
│  - /api/trm/* → Model Training & Inference                      │
│  - /api/rules/* → Rule Management                               │
│  - /api/versions/* → Version Control                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬────────────────┐
        │                │                │                │
┌───────▼────┐  ┌────────▼────────┐  ┌───▼──────┐  ┌─────▼─────────┐
│  Data      │  │  Rule Layer     │  │ Reasoning│  │  TRM Model    │
│  Layer     │  │  Engine         │  │  Layer   │  │  Manager      │
└────────────┘  └─────────────────┘  └──────────┘  └───────────────┘
```

### Layer Descriptions

#### 1. **Data Layer** (`data_layer/`)
Responsible for parsing and extracting building information from IFC files.

- **IFC Loading**: Parses IFC files using `ifcopenshell`
- **Element Extraction**: Extracts spaces, doors, windows, walls, columns, slabs, stairs
- **Graph Building**: Creates normalized JSON representation of building data
- **Graph Persistence**: Saves/loads graphs for processing

**Key Components:**
- `load_ifc.py`: IFC file loading and parsing
- `extract_core.py`: Element extraction logic
- `services.py`: High-level workflow orchestration
- `models.py`: Data models for building elements

#### 2. **Rule Layer** (`rule_layer/`)
Validates building against compliance rules.

- **Rule Definition**: Defines compliance rules using JSON schema
- **Rule Execution**: Runs rules against building graphs
- **Result Aggregation**: Collects and structures rule results
- **Rule Management**: Load, save, and manage rule sets

**Key Components:**
- `engine.py`: Rule execution engine
- `base.py`: Base rule class for custom rules
- `loader.py`: Load rules from JSON
- `models.py`: Result/status models

#### 3. **Reasoning Layer** (`reasoning_layer/`)
Provides explainability for compliance results using AI reasoning.

- **Failure Explanation**: Why did this element fail?
- **Impact Analysis**: How many elements are affected?
- **Recommendation Generation**: What should be fixed?
- **AI Assistant Integration**: Uses TRM for intelligent reasoning

**Key Components:**
- `reasoning_engine.py`: Main orchestrator
- `failure_explainer.py`: Analyzes failure causes
- `impact_analyzer.py`: Calculates impact metrics
- `recommendation_engine.py`: Generates recommendations
- `ai_assistant.py`: TRM-based explanations
- `tiny_recursive_reasoner.py`: TRM model implementation

#### 4. **TRM Model Layer** (`backend/`)
Trainable ML model for learning compliance patterns.

- **Model Training**: Train on compliance examples
- **Version Management**: Track model versions and performance
- **Inference**: Predict compliance using learned patterns
- **Incremental Learning**: Add new training samples

**Key Components:**
- `trm_model_manager.py`: Version and lifecycle management
- `trm_trainer.py`: Training logic
- `trm_api.py`: API endpoints
- `trm_model_management_api.py`: Version management endpoints

#### 5. **Backend API Layer** (`backend/`)
Flask REST API providing all functionality to frontend.

- **IFC Upload & Processing**: `/api/ifc/*`
- **Compliance Checking**: `/api/compliance/*`
- **Reasoning & Explanation**: `/api/reasoning/*`
- **Model Management**: `/api/trm/*`
- **Rule Management**: `/api/rules/*`
- **Version Control**: `/api/versions/*`

---

## Core Components

### Data Layer Components

#### IFC File Processing
```python
# Load IFC file
model = load_ifc('building.ifc')

# Extract elements
spaces, doors = extract_elements(model)

# Build normalized graph
graph = build_graph('building.ifc')
# Output: {
#   "building_id": "building",
#   "elements": {
#     "spaces": [...],
#     "doors": [...],
#     "windows": [...],
#     "walls": [...]
#   },
#   "meta": {...}
# }
```

**Extracted Elements:**
- **Spaces**: Rooms with area, level, connectivity
- **Doors**: Door objects with width, height, location
- **Windows**: Window objects with dimensions
- **Walls**: Wall objects with layers and materials
- **Columns**: Structural columns with properties
- **Slabs**: Floor/roof slabs with thickness
- **Stairs**: Stair elements with properties

### Rule Layer Components

#### Rule Structure
```json
{
  "id": "DOOR_WIDTH_MIN",
  "name": "Minimum Door Width",
  "description": "All egress doors must be at least 750mm wide",
  "rule_type": "element_attribute",
  "severity": "ERROR",
  "applies_to": ["doors"],
  "conditions": {
    "attribute": "width_mm",
    "operator": ">=",
    "threshold": 750
  }
}
```

#### Rule Execution
```python
engine = RuleEngine(rules)
results = engine.run(graph)
# Returns:
# [
#   {
#     "rule_id": "DOOR_WIDTH_MIN",
#     "status": "FAIL",
#     "failing_elements": ["door_001", "door_002"],
#     "affected_count": 2,
#     "severity": "ERROR"
#   }
# ]
```

### Reasoning Layer Components

#### Failure Analysis
- **Root Cause Identification**: Why did element fail?
- **Contributing Factors**: What aspects contributed?
- **Impact Scope**: How many elements affected?
- **Recommendation Priority**: What to fix first?

#### AI-Powered Explanations
```python
explanation = ai_assistant.explain_with_ai(
    element={"id": "door_001", "width_mm": 600},
    failure={"rule_id": "DOOR_WIDTH_MIN", "severity": "ERROR"},
    rule={"threshold": 750, "description": "Min door width 750mm"}
)
# Returns:
# {
#   "success": true,
#   "prediction": "FAIL",
#   "confidence": 0.95,
#   "explanation": "Door is too narrow for egress",
#   "reasoning_steps": [...],
#   "steps_taken": 8
# }
```

### TRM Model Components

#### Model Training
```python
# Add training samples
requests.post('/api/trm/add-samples-from-compliance', json={
    'compliance_results': results,
    'graph': graph,  # Critical: must include graph!
    'ifc_file': 'building.ifc'
})

# Train model
response = requests.post('/api/trm/train', json={
    'epochs': 10,
    'learning_rate': 0.001,
    'batch_size': 32
})
```

#### Model Inference
```python
# Get prediction for element
prediction = trm.predict(features)
# Returns: {
#   "prediction": "PASS" or "FAIL",
#   "confidence": 0.92,
#   "feature_importance": {...}
# }
```

---

## Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Flask | 3.0.0 |
| CORS | flask-cors | 4.0.0 |
| IFC Parsing | ifcopenshell | 0.8.0 |
| Validation | jsonschema | 4.20.0 |
| ML/Deep Learning | PyTorch | ≥2.0.0 |
| Numerical Computing | NumPy | ≥1.24.0 |
| String Processing | inflect | 7.0.0 |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | Latest |
| 3D Viewer | web-ifc-viewer | 1.0.218 |
| Styling | CSS3 | Latest |

### Data Format
| Format | Use Case |
|--------|----------|
| JSON | Graph representation, configuration |
| IFC | Building model input |

### Infrastructure
- **OS**: Cross-platform (Windows/Linux/macOS)
- **Python**: 3.8+
- **Node.js**: 14+ (for frontend build)

---

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Node.js 14 or higher
- Git

### Backend Setup

```bash
# 1. Navigate to workspace
cd "c:\Research Work\ACC-Explainability-AEC"

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r backend/requirements.txt

# 5. Verify installation
python -c "import torch, ifcopenshell; print('OK')"
```

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm start
# Server runs on http://localhost:3000
```

### Running the Application

```bash
# Terminal 1: Backend
cd backend
python app.py
# Backend runs on http://localhost:5000

# Terminal 2: Frontend
cd frontend
npm start
# Frontend runs on http://localhost:3000
```

### Verification

```bash
# Test IFC upload
curl -X POST http://localhost:5000/api/ifc/upload \
  -F "file=@sample.ifc"

# Test compliance check
curl -X POST http://localhost:5000/api/compliance/check \
  -H "Content-Type: application/json" \
  -d '{"graph": {...}}'
```

---

## API Reference

### IFC Management APIs

#### Upload IFC File
```
POST /api/ifc/upload
Content-Type: multipart/form-data

Parameters:
  file: IFC file (binary)

Response:
  {
    "success": true,
    "building_id": "filename",
    "graph": {...},
    "preview": {...}
  }
```

#### Preview IFC
```
POST /api/ifc/preview
Content-Type: application/json

Request:
  {
    "file_path": "path/to/file.ifc"
  }

Response:
  {
    "success": true,
    "building_id": "filename",
    "elements_summary": {
      "total_elements": 150,
      "spaces": 25,
      "doors": 45,
      "windows": 60
    }
  }
```

### Compliance APIs

#### Check Compliance
```
POST /api/compliance/check
Content-Type: application/json

Request:
  {
    "graph": {...},
    "rule_ids": ["DOOR_WIDTH_MIN", "SPACE_AREA_MIN"]  // optional
  }

Response:
  {
    "success": true,
    "results": [
      {
        "rule_id": "DOOR_WIDTH_MIN",
        "status": "FAIL",
        "failing_elements": ["door_001"],
        "affected_count": 1,
        "severity": "ERROR",
        "message": "Door width below minimum"
      }
    ],
    "summary": {
      "total_rules": 5,
      "passed": 4,
      "failed": 1
    }
  }
```

#### Generate Report
```
POST /api/compliance/report
Content-Type: application/json

Request:
  {
    "graph": {...},
    "include_reasoning": true
  }

Response:
  {
    "report_id": "report_20260122_001",
    "generated_at": "2026-01-22T10:30:00Z",
    "building_id": "building",
    "compliance_status": "FAIL",
    "summary": {...},
    "violations": [...],
    "recommendations": [...]
  }
```

### Reasoning APIs

#### Get Explanation
```
POST /api/reasoning/explain
Content-Type: application/json

Request:
  {
    "element": {...},
    "failure": {...},
    "rule": {...}
  }

Response:
  {
    "success": true,
    "explanation": "Human-readable explanation",
    "factors": ["factor1", "factor2"],
    "confidence": 0.92,
    "recommendations": [...]
  }
```

#### Analyze Impact
```
POST /api/reasoning/impact
Content-Type: application/json

Request:
  {
    "failure": {...},
    "graph": {...}
  }

Response:
  {
    "affected_elements": ["elem1", "elem2"],
    "affected_count": 2,
    "impact_scope": "localized",
    "downstream_effects": [...]
  }
```

### TRM Model APIs

#### Add Training Samples
```
POST /api/trm/add-samples-from-compliance
Content-Type: application/json

Request:
  {
    "compliance_results": [...],
    "graph": {...},  // CRITICAL: Must include graph!
    "ifc_file": "building.ifc"
  }

Response:
  {
    "success": true,
    "samples_added": 25,
    "dataset_size": 150
  }
```

#### Train Model
```
POST /api/trm/train
Content-Type: application/json

Request:
  {
    "epochs": 10,
    "learning_rate": 0.001,
    "batch_size": 32,
    "validation_split": 0.2,
    "description": "Training run 1"
  }

Response:
  {
    "success": true,
    "version_id": "v1.0",
    "training_duration_seconds": 45.32,
    "metrics": {
      "accuracy": 0.92,
      "loss": 0.18,
      "f1_score": 0.89
    }
  }
```

#### Get Model Versions
```
GET /api/trm/versions

Response:
  {
    "versions": [
      {
        "version_id": "v1.0",
        "created_at": "2026-01-22T10:00:00Z",
        "metrics": {...},
        "is_active": true
      }
    ]
  }
```

#### Make Prediction
```
POST /api/trm/predict
Content-Type: application/json

Request:
  {
    "element": {...},
    "rule": {...}
  }

Response:
  {
    "prediction": "PASS" or "FAIL",
    "confidence": 0.92,
    "reasoning": "Element meets specification"
  }
```

### Rule Management APIs

#### Get All Rules
```
GET /api/rules

Response:
  {
    "rules": [
      {
        "id": "DOOR_WIDTH_MIN",
        "name": "Minimum Door Width",
        "description": "...",
        "severity": "ERROR"
      }
    ]
  }
```

#### Add Custom Rule
```
POST /api/rules/custom
Content-Type: application/json

Request:
  {
    "id": "CUSTOM_RULE_1",
    "name": "Custom Rule",
    "description": "Custom compliance rule",
    "rule_type": "element_attribute",
    "applies_to": ["doors"],
    "conditions": {...}
  }

Response:
  {
    "success": true,
    "rule_id": "CUSTOM_RULE_1"
  }
```

#### Delete Rule
```
DELETE /api/rules/custom/{rule_id}

Response:
  {
    "success": true,
    "deleted_rule": "CUSTOM_RULE_1"
  }
```

### Version Management APIs

#### Get Rule Versions
```
GET /api/versions/rules

Response:
  {
    "current_version": "2026-01-22",
    "versions": [
      {
        "version_id": "2026-01-22",
        "created_at": "2026-01-22T10:00:00Z",
        "rule_count": 25
      }
    ]
  }
```

#### Compare Versions
```
GET /api/versions/rules/compare?v1=2026-01-22&v2=2026-01-21

Response:
  {
    "added_rules": [...],
    "removed_rules": [...],
    "modified_rules": [...]
  }
```

---

## Data Flow

### Complete Workflow: IFC to Compliance Report

```
1. User uploads IFC file
   ↓
2. Backend: Parse IFC → Extract elements → Build graph
   ↓
3. Backend: Run compliance rules against graph
   ↓
4. Backend: Analyze failures → Generate reasoning
   ↓
5. Backend: Query TRM model for AI predictions
   ↓
6. Backend: Aggregate results → Generate report
   ↓
7. Frontend: Display results, explanations, recommendations
   ↓
8. User: Review findings, identify fixes
   ↓
9. Backend: (Optional) Add results to training data
   ↓
10. Backend: (Optional) Retrain TRM model
```

### Critical Data Fix: The "70% Accuracy Problem"

**Problem:** Feature vectors identical across all samples → Model can't learn

**Root Cause:** Element dimensions (width_mm, height_mm) missing from training data
- Without dimensions: Uses defaults (1200mm, 2400mm)
- Defaults normalize to exactly 0.5
- Result: All samples → [0.5, 0.5, 0.5, ...]

**Solution:** Include complete graph when adding training samples

```python
# BEFORE (Broken - 70% accuracy on all files)
requests.post('/api/trm/add-samples-from-compliance',
    json={'compliance_results': results})  # ❌ No graph

# AFTER (Fixed - Model learns real patterns)
requests.post('/api/trm/add-samples-from-compliance',
    json={
        'compliance_results': results,
        'graph': graph,  # ✓ Include graph for real dimensions!
        'ifc_file': 'building.ifc'
    })
```

**Impact:**
- Narrow door (400mm) → feature = 0.0625 (not 0.5)
- Standard door (700mm) → feature = 0.1875 (not 0.5)
- Wide door (1000mm) → feature = 0.375 (not 0.5)
- Result: Model receives varied signals and learns patterns!

---

## Key Features

### 1. **Automated Compliance Checking**
- Parses IFC building models
- Validates against regulatory rules
- Generates compliance reports
- Tracks compliance history

### 2. **Explainable AI Reasoning**
- Explains why elements fail compliance
- Identifies root causes
- Analyzes impact scope
- Generates recommendations

### 3. **Trainable ML Model (TRM)**
- TinyRecursiveReasoner neural network
- Learns from compliance patterns
- Provides confidence scores
- Supports incremental learning
- Version tracking and rollback

### 4. **Rule Management**
- Built-in regulatory rules
- Custom rule support
- Rule versioning
- Rule synchronization
- Import/export capabilities

### 5. **Version Control**
- Model versioning with history
- Rule versioning
- Performance tracking
- Lineage tracking
- Rollback capability

### 6. **3D Visualization**
- Interactive IFC model viewer
- Element inspection
- Failure highlighting
- Spatial navigation

### 7. **Batch Processing**
- Process multiple IFC files
- Parallel compliance checking
- Aggregate reporting
- Performance metrics

---

## Configuration

### Backend Configuration

#### Main Config Files

**`backend/app.py`**: Flask application setup
- CORS configuration
- API route registration
- Service initialization
- Logging setup

**`data_layer/extraction_config.json`**: Element extraction settings
```json
{
  "extractions": [
    {
      "entity_type": "IfcDoor",
      "output_key": "doors",
      "properties": ["width_mm", "height_mm", "position"]
    }
  ]
}
```

**`reasoning_layer/config.py`**: Reasoning engine settings
```python
class ReasoningConfig:
    # Impact thresholds
    IMPACT_THRESHOLD_HIGH = 50  # affects > 50 elements
    IMPACT_THRESHOLD_MEDIUM = 10  # affects 10-50 elements
    
    # Recommendation priority levels
    PRIORITY_CRITICAL = "critical"
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
```

#### Rule Configuration

**`rules_config/rules.json`**: Regulatory rules
```json
{
  "rules": [
    {
      "id": "DOOR_WIDTH_MIN",
      "name": "Minimum Door Width",
      "severity": "ERROR",
      "applies_to": ["doors"],
      "conditions": {
        "attribute": "width_mm",
        "operator": ">=",
        "threshold": 750
      }
    }
  ]
}
```

**`rules_config/custom_rules.json`**: User-defined rules
- Same structure as built-in rules
- Can override defaults
- Applied alongside regulatory rules

#### Environment Variables

```bash
# Flask
FLASK_ENV=development
FLASK_DEBUG=1

# Logging
LOG_LEVEL=INFO

# Model
TRM_MODEL_DIR=backend/model_versions
TRM_CHECKPOINT_DIR=checkpoints/trm

# Data
DATA_DIR=data
DATASET_FILE=data/trm_incremental_data.json
```

---

## Development Guide

### Project Structure

```
root/
├── backend/                 # Flask API & core logic
│   ├── app.py              # Flask application
│   ├── *_api.py            # API blueprints
│   ├── requirements.txt     # Python dependencies
│   └── __pycache__/        # Compiled Python
├── data_layer/             # IFC parsing & extraction
│   ├── load_ifc.py         # IFC loading
│   ├── extract_core.py     # Element extraction
│   ├── services.py         # Service layer
│   └── models.py           # Data models
├── rule_layer/             # Compliance rule execution
│   ├── engine.py           # Rule engine
│   ├── base.py             # Base rule class
│   ├── loader.py           # Rule loading
│   └── rules/              # Rule implementations
├── reasoning_layer/        # AI reasoning & explanations
│   ├── reasoning_engine.py # Main orchestrator
│   ├── failure_explainer.py # Failure analysis
│   ├── impact_analyzer.py  # Impact analysis
│   ├── ai_assistant.py     # AI explanations
│   └── tiny_recursive_reasoner.py # TRM model
├── frontend/               # React application
│   ├── public/             # Static files
│   ├── src/                # React components
│   └── package.json        # JS dependencies
├── rules_config/           # Rule configuration
│   ├── rules.json          # Built-in rules
│   ├── custom_rules.json   # Custom rules
│   └── versions/           # Rule versions
├── data/                   # Runtime data
│   ├── trm_incremental_data.json # Training data
│   └── debug_features.txt  # Feature debugging
├── checkpoints/            # Model checkpoints
│   └── trm/                # TRM model versions
└── tests/                  # Test files
```

### Adding a New Rule

```python
# 1. Create rule class in rule_layer/rules/
from rule_layer.base import BaseRule
from rule_layer.models import RuleResult, RuleSeverity, RuleStatus

class CustomRule(BaseRule):
    def __init__(self):
        super().__init__(
            rule_id="CUSTOM_001",
            name="Custom Compliance Rule",
            severity=RuleSeverity.WARNING
        )
    
    def check(self, graph):
        """Check compliance against graph"""
        results = []
        spaces = graph.get("elements", {}).get("spaces", [])
        
        for space in spaces:
            if space.get("area_m2", 0) < 10:  # Example threshold
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    element_id=space.get("id"),
                    status=RuleStatus.FAIL,
                    message=f"Space too small: {space['area_m2']}m²"
                ))
        
        return results

# 2. Register in rule_layer/engine.py
from rule_layer.rules.custom_rule import CustomRule

rules = [
    CustomRule(),
    # ... other rules
]
```

### Extending the Reasoning Layer

```python
# 1. Create new analyzer in reasoning_layer/
class CustomAnalyzer:
    def analyze(self, failure, graph):
        """Custom analysis logic"""
        return {
            "finding": "...",
            "severity": "high",
            "impact": 25
        }

# 2. Integrate with ReasoningEngine
reasoning_engine = ReasoningEngine()
reasoning_engine.custom_analyzer = CustomAnalyzer()

# 3. Use in reasoning process
result = reasoning_engine.reason(failure, graph)
```

### Training the TRM Model

```python
# Step 1: Collect training data with complete graphs
import requests

for ifc_file in ifc_files:
    r = requests.post('http://localhost:5000/api/ifc/upload',
                     files={'file': open(ifc_file, 'rb')})
    graph = r.json()['graph']
    
    r = requests.post('http://localhost:5000/api/compliance/check',
                     json={'graph': graph})
    results = r.json()['results']
    
    # CRITICAL: Include graph in training data!
    requests.post('http://localhost:5000/api/trm/add-samples-from-compliance',
                 json={
                     'compliance_results': results,
                     'graph': graph,  # Must include!
                     'ifc_file': ifc_file
                 })

# Step 2: Train model
response = requests.post('http://localhost:5000/api/trm/train', json={
    'epochs': 10,
    'learning_rate': 0.001,
    'batch_size': 32,
    'description': 'Training with complete graph data'
})

print(f"Model version: {response.json()['version_id']}")
print(f"Accuracy: {response.json()['metrics']['accuracy']}")
```

### Debugging

**Enable Debug Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In Flask app
app.logger.setLevel(logging.DEBUG)
```

**Inspect Training Data:**
```bash
python -c "
import json
with open('data/trm_incremental_data.json') as f:
    data = json.load(f)
    print(f'Samples: {len(data)}')
    print(f'Feature dimensions: {len(data[0][\"features\"])}')
    print(f'Feature values: {data[0][\"features\"][:5]}')
"
```

**Test Rule Execution:**
```python
from rule_layer.engine import RuleEngine
from rule_layer.loader import load_rules_from_file

rules = load_rules_from_file('rules_config/rules.json')
engine = RuleEngine(rules)
results = engine.run_from_file('sample_graph.json')

for result in results:
    print(f"{result.rule_id}: {result.status}")
```

---

## Troubleshooting

### Common Issues

#### 1. "Model shows 70% accuracy on every file"

**Cause:** Graph not included in training data → missing dimensions

**Solution:**
```python
# Add graph parameter
requests.post('/api/trm/add-samples-from-compliance',
    json={
        'compliance_results': results,
        'graph': graph,  # ← Add this!
        'ifc_file': 'building.ifc'
    })
```

#### 2. IFC Upload Fails

**Cause:** File corrupted or unsupported IFC version

**Solution:**
```bash
# Verify IFC file
python -c "
import ifcopenshell
model = ifcopenshell.open('file.ifc')
print(f'Schema: {model.schema}')
print(f'Entities: {len(list(model.entities))}')
"
```

#### 3. Rule Execution Too Slow

**Cause:** Large graph or inefficient rule logic

**Solution:**
- Cache extracted elements
- Use indexed lookups instead of linear search
- Run rules in parallel for independent checks

```python
from concurrent.futures import ThreadPoolExecutor

def run_parallel_rules(rules, graph):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(rule.check, graph) 
            for rule in rules
        ]
        results = []
        for future in futures:
            results.extend(future.result())
    return results
```

#### 4. Frontend Not Loading Results

**Cause:** CORS issue or API error

**Solution:**
```bash
# Check backend is running
curl http://localhost:5000/api/health

# Check CORS headers
curl -i http://localhost:5000/api/ifc/upload

# Check frontend console for errors
# Browser → F12 → Console tab
```

#### 5. Out of Memory During Training

**Cause:** Batch size too large for available memory

**Solution:**
```python
# Reduce batch size
response = requests.post('/api/trm/train', json={
    'epochs': 10,
    'batch_size': 8,  # Reduce from 32
    'learning_rate': 0.001
})
```

### Performance Optimization

#### Profile Execution
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run expensive operation
results = engine.run(graph)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10
```

#### Monitor Memory Usage
```python
import psutil
import os

process = psutil.Process(os.getpid())
info = process.memory_info()
print(f"RSS: {info.rss / 1024 / 1024:.2f} MB")
print(f"VMS: {info.vms / 1024 / 1024:.2f} MB")
```

### Support & Logs

**Backend Logs:**
```bash
# Real-time logging
tail -f backend.log

# Search for errors
grep ERROR backend.log

# Check specific time range
grep "2026-01-22" backend.log
```

**Frontend Logs:**
```javascript
// Browser console
console.log(response);

// Network tab
// F12 → Network → Click request → See response/error
```

---

## Best Practices

### Data Management
1. **Always include graphs** when adding training samples
2. **Validate IFC files** before processing
3. **Cache extracted graphs** to avoid re-parsing
4. **Clean old training data** periodically

### Model Training
1. **Use varied datasets** with different building types
2. **Monitor metrics** during training (loss, accuracy)
3. **Save checkpoints** at regular intervals
4. **Version all models** for reproducibility
5. **Test on holdout set** before deployment

### Rule Management
1. **Version rule changes** for audit trail
2. **Test custom rules** before deployment
3. **Document rule rationale** in descriptions
4. **Review rule performance** regularly

### Production Deployment
1. **Use environment variables** for configuration
2. **Enable request logging** for debugging
3. **Monitor API response times**
4. **Implement rate limiting** for API
5. **Backup training data** regularly
6. **Test disaster recovery** procedures

---

## Conclusion

ACC-Explainability-AEC provides a comprehensive platform for building compliance checking with explainable AI reasoning. The layered architecture ensures clean separation of concerns, while the TRM model learns from compliance patterns to improve predictions over time.

The key innovation—including complete graphs in training data—resolves the accuracy plateau and enables meaningful model learning. Regular version control and reproducible experiments ensure reliability and auditability.

For questions or issues, refer to this documentation or check the test files for usage examples.

**Happy Compliance Checking! ✅**
