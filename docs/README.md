# ACC Explainability AEC - Documentation

## Project Structure

```
ACC-Explainability-AEC/
├── backend/                    # Python backend services
│   ├── app.py                 # Main Flask application
│   ├── unified_compliance_engine.py
│   ├── rule_config_manager.py
│   ├── requirements.txt
│   └── ...
├── data_layer/                # Data processing and graph building
│   ├── load_ifc.py           # IFC file loading
│   ├── extract_core.py       # Core data extraction
│   ├── build_graph.py        # Graph construction
│   └── services.py
├── rule_layer/                # Rule engine and compliance checking
│   ├── engine.py             # Rule execution engine
│   ├── compliance_checker.py
│   ├── models.py             # Rule models
│   └── rules/                # Individual rule implementations
├── reasoning_layer/           # Reasoning and analysis
│   ├── reasoning_engine.py
│   ├── element_analyzer.py
│   ├── solution_generator.py
│   └── reasoning_justifier.py
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── config/           # Configuration files
│   │   ├── styles/           # CSS stylesheets
│   │   ├── services/         # API services
│   │   └── App.js           # Main app component
│   ├── public/              # Static assets
│   └── package.json         # Dependencies
├── rules_config/             # Rule configurations
│   ├── enhanced-regulation-rules.json
│   ├── custom_rules.json
│   └── rules.json
├── acc-dataset/             # Sample IFC files and datasets
│   └── IFC/                 # IFC model files
├── tests/                    # Test suite
├── tools/                    # Utility scripts
├── scripts/                  # Helper scripts
└── docs/                     # Documentation
```

## Key Features

### 1. 3D Model Visualization
- **File**: `frontend/src/components/ModelVisualizationView.js`
- **Features**:
  - Interactive 3D rendering of IFC models
  - Color-coded element types (walls, doors, windows, etc.)
  - Wireframe toggle for geometric detail viewing
  - Mouse controls: rotate, zoom, pan
  - Optimized for 60 FPS performance
- **See**: `docs/PERFORMANCE_OPTIMIZATION.md` for optimization details

### 2. Centralized Color Configuration
- **Files**: 
  - `frontend/src/config/colorConfig.js` - Main color definitions
  - `frontend/src/config/colorUtils.js` - Utility functions
- **Usage**: Consistent colors across the application
- **Colors**: 9 element types with hex, RGB, and Three.js formats

### 3. Rule Engine
- **Location**: `rule_layer/engine.py`
- **Features**:
  - Compliance rule execution
  - Rule manifest loading
  - Multi-element rule checking
  - Detailed compliance reporting

### 4. Data Layer
- **Location**: `data_layer/`
- **Features**:
  - IFC file parsing and loading
  - Graph-based data structure building
  - Element relationship mapping
  - Core property extraction

### 5. Unified Compliance Engine
- **File**: `backend/unified_compliance_engine.py`
- **Features**:
  - Centralized compliance checking
  - Rule configuration management
  - Report generation
  - Multi-rule validation

## Recent Optimizations

### Performance Improvements
- Geometry caching and reuse
- Material caching by color
- 99.7% polygon reduction
- Optimized renderer settings
- Lighting simplification

**Result**: 3-5x faster 3D rendering (55-60 FPS)

See: `docs/PERFORMANCE_OPTIMIZATION.md`

## Development Workflow

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Testing
```bash
cd backend
python -m pytest tests/
```

## Configuration Files

### Rules Configuration
- **Location**: `rules_config/enhanced-regulation-rules.json`
- **Format**: JSON
- **Content**: Regulatory compliance rules and checks

### Custom Rules
- **Location**: `rules_config/custom_rules.json`
- **Purpose**: User-defined compliance rules

## Module Architecture

### Color System
```javascript
import { ELEMENT_COLORS, getColor, getAllColors } from '@/config/colorConfig';
import { getElementBadgeStyle, getColorSwatchStyle } from '@/config/colorUtils';
```

### 3D Visualization
- Geometry caching: `geometryCacheRef`
- Material caching: `materialsCacheRef`
- Optimized geometries per element type
- Shared materials per color

### Compliance Checking
- Rule loading from manifest
- Element-wise rule evaluation
- Detailed result reporting
- Compliance scoring

## Common Tasks

### Add a New Element Type
1. Update `colorConfig.js` with new color
2. Add geometry to `createOptimizedGeometry()` in `ModelVisualizationView.js`
3. Update rule definitions

### Modify Color Scheme
1. Edit `frontend/src/config/colorConfig.js`
2. Changes automatically propagate across the app

### Create Custom Rules
1. Add to `rules_config/custom_rules.json`
2. Register in rule manager
3. Load via unified compliance engine

## File Organization Best Practices

✅ **Do**:
- Keep components in `frontend/src/components/`
- Store configs in `frontend/src/config/`
- Use centralized color configuration
- Cache geometries and materials
- Document performance-critical code

❌ **Don't**:
- Store example files in source directories
- Create duplicate configurations
- Recreate geometries/materials repeatedly
- Commit large IFC files (use acc-dataset/)

## Dependencies

### Backend
- Flask (web framework)
- ifcopenshell (IFC parsing)
- numpy, pandas (data processing)

### Frontend
- React 18.2.0
- Three.js (3D graphics)
- Lucide React (icons)
- Tailwind CSS (styling)

## Performance Targets

- 3D Visualization: 60 FPS
- Page Load: < 2 seconds
- Compliance Check: < 1 second
- Memory: < 100MB frontend, < 200MB backend

## Troubleshooting

### 3D Viewer Not Loading
- Check Three.js installation: `npm list three`
- Verify WebGL support in browser
- Check browser console for errors

### Slow Performance
- Verify geometry caching is working
- Check polygon count in inspector
- Review renderer optimization settings
- See `docs/PERFORMANCE_OPTIMIZATION.md`

### Rule Engine Issues
- Validate rule JSON syntax
- Check element type mappings
- Review unified_compliance_engine logs

## Contributing

1. Follow existing code style
2. Update documentation for major changes
3. Test performance-critical code
4. Use centralized configurations
5. Cache resources when possible

## Additional Resources

- **3D Visualization**: `docs/PERFORMANCE_OPTIMIZATION.md`
- **Color Configuration**: `frontend/src/config/colorConfig.js`
- **Rule Engine**: `rule_layer/engine.py`
- **Data Layer**: `data_layer/services.py`

---

**Last Updated**: December 1, 2025
