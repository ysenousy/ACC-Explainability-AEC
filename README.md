# ACC-Explainability-AEC: Building Compliance AI System

> An intelligent system for analyzing building codes and predicting compliance violations using IFC models and machine learning.

## 🎯 Project Overview

This system integrates three core layers to provide comprehensive building code compliance analysis:

1. **Data Layer** - Extracts building information from IFC models
2. **Rule Layer** - Applies regulatory rules to evaluate compliance
3. **Reasoning Layer** - Predicts violations and provides explanations using TRM (Tiny Recursive Model)

## 🚀 Key Features

- **IFC Model Analysis** - Parse and extract data from Building Information Models
- **Compliance Checking** - Apply regulatory rules to building elements
- **AI Predictions** - Machine learning model trained on compliance patterns
- **Model Management** - Version control and performance tracking for trained models
- **Interactive Dashboard** - React-based UI for viewing results and managing models
- **REST API** - Complete API for programmatic access

## 📁 Project Structure

```
ACC-Explainability-AEC/
├── backend/              # Flask API and business logic
│   ├── app.py           # Main application entry point
│   ├── trm_api.py       # TRM model training endpoints
│   ├── trm_trainer.py   # Training engine
│   ├── trm_data_extractor.py  # Feature extraction
│   └── requirements.txt  # Python dependencies
│
├── frontend/            # React application
│   ├── src/
│   │   ├── components/  # React components
│   │   │   ├── TRMDashboard.jsx    # Model management interface
│   │   │   ├── ComplianceReportView.jsx
│   │   │   └── ...
│   │   ├── styles/      # CSS stylesheets
│   │   └── App.js       # Main app component
│   └── package.json     # Node dependencies
│
├── data_layer/          # Building data extraction
│   ├── load_ifc.py      # IFC file parsing
│   ├── extract_core.py  # Core element extraction
│   ├── extract_rules.py # Rule data extraction
│   └── models.py        # Data models
│
├── rule_layer/          # Compliance rule engine
│   ├── engine.py        # Rule evaluation engine
│   ├── loader.py        # Rule loading
│   ├── models.py        # Rule models
│   └── compliance_checker.py
│
├── reasoning_layer/     # Explanation and reasoning
│   ├── reasoning_engine.py
│   ├── failure_explainer.py
│   └── recommendation_engine.py
│
├── tests/               # Test suite (134 tests passing)
│   ├── test_trm_trainer.py
│   ├── test_trm_data_extractor.py
│   ├── test_rule_engine.py
│   └── ...
│
├── acc-dataset/         # Sample IFC files and data
│   └── IFC/            # Building model files
│
└── docs/               # Documentation and planning
    ├── TRM_ARCHITECTURE_OVERVIEW.md
    ├── TRM_EXECUTIVE_SUMMARY.md
    ├── TRM_QUICK_REFERENCE.md
    └── ...
```

## ⚙️ Installation

### Prerequisites
- Python 3.8+
- Node.js 14+
- pip and npm

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

## 🎬 Running the Application

### Start Backend Server

```bash
cd backend
python app.py
```

Server runs on `http://localhost:5000`

### Start Frontend Development Server

```bash
cd frontend
npm start
```

Dashboard available at `http://localhost:3000`

## 📚 Core Components

### TRM Model (Tiny Recursive Model)

An advanced neural network for compliance prediction:
- **Architecture**: Multi-stream network with attention mechanisms
- **Parameters**: 5.9M trainable parameters
- **Input**: 320-dimensional feature vectors
- **Output**: Binary classification (Pass/Fail)
- **Training**: Supervised learning with validation/test splits

### Data Pipeline

Process for converting compliance data to training samples:
1. Load IFC building model
2. Extract building elements and properties
3. Apply compliance rules (Pass/Fail)
4. Generate compliance report
5. Convert results to training samples
6. Train TRM model on accumulated data

### API Endpoints

#### Training & Model Management
- `POST /api/trm/add-sample` - Add training sample
- `POST /api/trm/train` - Train model on accumulated data
- `GET /api/trm/versions` - List all model versions
- `GET /api/trm/versions/best` - Get best performing version
- `GET /api/trm/models` - Get model information

#### Compliance Analysis
- `POST /api/compliance/check` - Check building compliance
- `POST /api/compliance/report` - Generate compliance report
- `GET /api/compliance/rules` - Get available rules

#### IFC Processing
- `POST /api/ifc/load` - Load IFC model
- `GET /api/ifc/preview` - Get model visualization data
- `GET /api/ifc/elements` - Extract building elements

## 🧠 How It Works

### Workflow

1. **Load IFC Model** → Import building information from design files
2. **Extract Data** → Extract building elements and their properties
3. **Check Compliance** → Apply regulatory rules (Pass/Fail)
4. **Generate Report** → Summarize results and violations
5. **Train Model** → Feed compliance data to TRM for learning patterns
6. **Predict Issues** → Model learns to predict violations early

### Feature Extraction

The system extracts 320-dimensional feature vectors from:
- Element properties (type, dimensions, materials)
- Rule context (regulatory requirements, jurisdiction)
- Spatial relationships (location in building)
- Semantic embeddings (contextual information)

### Training Configuration

- **Optimizer**: Adam
- **Loss Function**: Binary Cross-Entropy
- **Learning Rate**: 0.001
- **Epochs**: 10-30 (configurable)
- **Data Split**: 80% train, 10% validation, 10% test
- **Batch Size**: 16

## 📊 Performance Metrics

The system tracks:
- **Accuracy**: Percentage of correct predictions
- **Validation Loss**: Model prediction error
- **Training Time**: Time to complete training
- **Best Version**: Automatically selects best performing model

## 🧪 Testing

Run the complete test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_trm_trainer.py -v

# Run with coverage
python -m pytest tests/ --cov=backend --cov=data_layer --cov=rule_layer
```

**Status**: ✅ 134 tests passing (100%)

## 📖 Documentation

Comprehensive documentation available in the `/docs` folder:

- **TRM_ARCHITECTURE_OVERVIEW.md** - System architecture and design
- **TRM_EXECUTIVE_SUMMARY.md** - High-level overview and business case
- **TRM_QUICK_REFERENCE.md** - Quick reference guide
- **TRM_IMPLEMENTATION_PLAN.md** - Detailed implementation specifications
- **TRM_DECISIONS_AND_APPROVAL_GATES.md** - Decision framework

## 🔧 Configuration

### Model Training Config

Edit `rules_config/execution-config.json`:

```json
{
  "training": {
    "epochs": 20,
    "batch_size": 16,
    "learning_rate": 0.001,
    "validation_split": 0.1,
    "early_stopping": true,
    "patience": 5
  }
}
```

### Rule Configuration

Rules defined in:
- `rules_config/rules.json` - Core compliance rules
- `rules_config/custom_rules.json` - Custom rules
- `rules_config/enhanced-regulation-rules.json` - Enhanced rules

## 💾 Data Management

### Dataset Storage

Training data stored in `data/trm_incremental_data.json`:
- Automatically manages train/validation/test splits (80/10/10)
- Deduplicates samples by element GUID
- Incremental updates without data loss

### Model Versions

Model checkpoints stored in `backend/model_versions/`:
- Each training creates a new version
- Versions include performance metrics
- Best model automatically selected
- Version history for comparison

## 🚨 Troubleshooting

### Model accuracy too high/too low
- Check data quality in dataset
- Verify feature extraction is working correctly
- Review training configuration (epochs, learning rate)

### API errors
- Ensure backend server is running on port 5000
- Check Python dependencies are installed
- Review backend logs for error details

### Frontend not loading
- Verify Node dependencies installed (`npm install`)
- Check frontend server running on port 3000
- Clear browser cache

## 📝 License

This project is part of the ACC-Explainability-AEC research initiative.

## 👥 Contributors

Built with research and development by the team at the American Construction Council.

## 📧 Support

For issues and questions, refer to the documentation in `/docs` or check the GitHub issues page.

---

**Last Updated**: December 8, 2025
**Status**: ✅ Production Ready (Phases 1-5 Complete)
