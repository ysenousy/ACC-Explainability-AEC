# Cleanup and Organization Guide

## Files to Archive or Remove

### Temporary Test Files (Root Directory)

These files were used for quick testing during development:

- **`test_trm_api_quick.py`** - Quick API test script (development only) - ✅ REMOVED
- **`check_dataset.py`** - Dataset inspection script (development only) - ✅ REMOVED

**Status**: Tests are properly organized in `/tests` folder

### Phase Status Documents

These planning/status documents are now superseded by the main README:

- **`PHASE_5_COMPLETE.md`** - Phase 5 completion summary
- **`TRM_FINAL_STATUS.md`** - Final project status
- **`TRM_SYSTEM_COMPLETE.md`** - System completion summary

**Status**: Archived to `/docs/archive` (keeping for historical reference)

---

## Documentation Organization

### Keep in Root
- **`README.md`** ✅ - Main documentation (updated)

### Organized in `/docs`
- `TRM_ARCHITECTURE_OVERVIEW.md` - System design
- `TRM_EXECUTIVE_SUMMARY.md` - High-level overview
- `TRM_QUICK_REFERENCE.md` - Quick reference
- `TRM_IMPLEMENTATION_PLAN.md` - Implementation details
- `TRM_DECISIONS_AND_APPROVAL_GATES.md` - Decision framework
- `TRM_DATA_SOURCES.md` - Data source documentation
- `TRM_MODEL_OUTPUT.md` - Model output specifications
- `PHASE_1_DETAILED_PLAN.md` - Phase 1 details
- `README_TRM_PLANNING.md` - TRM planning notes

### Archive (Historical Reference)
- `PHASE_5_COMPLETE.md` - Archived
- `TRM_FINAL_STATUS.md` - Archived
- `TRM_SYSTEM_COMPLETE.md` - Archived

---

## Active Test Files to Keep

Located in `/tests` directory:

- ✅ `test_trm_trainer.py` - Model training tests
- ✅ `test_trm_data_extractor.py` - Data extraction tests
- ✅ `test_trm_model_manager.py` - Version management tests
- ✅ `test_rule_engine.py` - Rule engine tests
- ✅ `test_data_layer_service.py` - Data layer tests
- ✅ `test_extract_rules.py` - Rule extraction tests
- ✅ `test_preview_ifc_unit.py` - IFC preview tests
- ✅ `test_phase5_integration.py` - Integration tests
- ✅ `test_tiny_recursive_reasoner.py` - TRM model tests
- ✅ `test_trm_api.py` - API endpoint tests

**Total**: 134 tests passing (100%)

---

## Project Structure After Cleanup

```
ACC-Explainability-AEC/
├── README.md                          # Main documentation
├── backend/
│   ├── app.py
│   ├── trm_api.py
│   ├── trm_trainer.py
│   ├── trm_data_extractor.py
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── styles/
│   │   └── App.js
│   ├── package.json
│   └── ...
├── data_layer/
├── rule_layer/
├── reasoning_layer/
├── tests/                             # Organized test suite
├── acc-dataset/                       # Sample data
├── docs/                              # Documentation
│   ├── TRM_ARCHITECTURE_OVERVIEW.md
│   ├── TRM_EXECUTIVE_SUMMARY.md
│   ├── TRM_QUICK_REFERENCE.md
│   └── archive/                       # Historical files
│       ├── PHASE_5_COMPLETE.md
│       ├── TRM_FINAL_STATUS.md
│       └── TRM_SYSTEM_COMPLETE.md
├── rules_config/
├── scripts/
├── tools/
└── .gitignore                         # Git configuration
```

---

## Cleanup Commands

### Remove Temporary Files
```powershell
# Remove quick test files
Remove-Item "test_trm_api_quick.py" -Force
Remove-Item "check_dataset.py" -Force

# Remove old image if not needed
Remove-Item "CFW_Explainability.png" -Force
```

### Archive Phase Documents (Optional)
```powershell
# Create archive folder if not exists
New-Item -ItemType Directory -Path "docs\archive" -Force

# Move phase completion documents
Move-Item "PHASE_5_COMPLETE.md" -Destination "docs\archive\" -Force
Move-Item "TRM_FINAL_STATUS.md" -Destination "docs\archive\" -Force
Move-Item "TRM_SYSTEM_COMPLETE.md" -Destination "docs\archive\" -Force
```

---

## Files to Keep (DO NOT DELETE)

### Source Code
- All Python files in: `backend/`, `data_layer/`, `rule_layer/`, `reasoning_layer/`
- All JavaScript files in: `frontend/src/`
- All test files in: `tests/`

### Configuration
- `package.json` - Node dependencies
- `backend/requirements.txt` - Python dependencies
- `.gitignore` - Git configuration
- Configuration files in `rules_config/`

### Data
- `acc-dataset/` - Sample IFC files
- `data/` - Training data (if any)

### Documentation
- `README.md` - Main documentation
- All files in `docs/` folder

---

## Verification Checklist

After cleanup:

- ✅ Main README.md is comprehensive and up-to-date
- ✅ All documentation organized in /docs
- ✅ Test files organized in /tests (134 tests)
- ✅ No duplicate documentation in root
- ✅ Source code intact
- ✅ Configuration files preserved
- ✅ Sample data intact

---

**Last Updated**: December 8, 2025
