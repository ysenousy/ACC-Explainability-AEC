# Enhanced Compliance System - Quick Start Guide

## 🎯 What's New

Enhanced regulatory rules system with:
- ✅ Explicit IFC class targeting (IfcDoor, IfcSpace, etc.)
- ✅ QTO/PSet source differentiation
- ✅ Multi-filter selectors for complex queries
- ✅ Parameterized explanations with real values
- ✅ Complete compliance checking UI
- ✅ Export compliance reports as JSON

## 📂 Files Location

```
project-root/
├── rules_config/
│   └── enhanced-regulation-rules.json     ← 10 regulation rules (new format)
├── rule_layer/
│   └── compliance_checker.py              ← Backend compliance engine
├── backend/
│   └── app.py                             ← 5 new REST endpoints
├── frontend/src/components/
│   ├── ComplianceCheckView.js             ← Compliance UI component
│   ├── Sidebar.js                         ← Updated with compliance layer
│   └── App.js                             ← Integrated compliance check view
└── COMPLIANCE_SYSTEM_INTEGRATION.md       ← Full documentation
```

## 🚀 Quick Start

### 1. **Load an IFC File**
   - Click "Browse IFC" and select a building model
   - Wait for graph to build

### 2. **Navigate to Compliance Checking**
   - Sidebar → ⚖️ Compliance → Compliance Checking

### 3. **Run Compliance Check**
   - Click "Run Compliance Check" button
   - Wait for analysis (~5-10 seconds)
   - Results appear below

### 4. **Review Results**
   - **Green cards**: Compliance metrics (Passed/Failed/Unable/Rate)
   - **Filter buttons**: Filter by status, severity, or rule
   - **Results table**: Detailed results with explanations
   - **Export button**: Download report as JSON

## 📊 Understanding Results

| Status | Meaning | Color |
|--------|---------|-------|
| ✓ | Element passes requirement | Green |
| ✗ | Element fails requirement | Red |
| ? | Cannot evaluate (missing data) | Blue |

| Severity | Action |
|----------|--------|
| ERROR | Must fix for compliance |
| WARNING | Should address |
| INFO | For reference |

## 💡 Example: ADA Door Width Check

**What it checks:**
- All doors marked as "accessible" in the IFC model
- Their clear opening width (from QTO quantities)
- Requirement: Width ≥ 813 mm

**Result if FAILED:**
```
Door abc123def456 has clear width of 750 mm, 
below the required 813 mm.
```

**Result if PASSED:**
```
Door abc123def456 meets the ADA clear width 
requirement (850 mm ≥ 813 mm).
```

## 🔧 Regulations Included

### Accessibility Standards:
- ✅ ADA Door Width (813 mm minimum)
- ✅ ADA Corridor Width (914 mm minimum)
- ✅ UK Door Width (775 mm minimum)
- ✅ EN Corridor Width (900 mm minimum)
- ✅ NBC Door Width (750 mm minimum)

### Fire Safety:
- ✅ Fire Exit Door Height (1980 mm minimum)

### Room Dimensions:
- ✅ Bedroom Minimum Area (6.5 m²)
- ✅ Bathroom Minimum Area (3.25 m²)
- ✅ Bedroom Window Minimum (0.93 m²)

### Structural:
- ✅ Stair Minimum Width (1118 mm)

## 📈 Compliance Report

**What's included in exported report:**

```json
{
  "timestamp": "2025-11-20T14:30:00",
  "total_checks": 150,
  "passed": 120,
  "failed": 25,
  "unable": 5,
  "pass_rate": 80.0,
  "results": [
    {
      "rule_id": "ADA_DOOR_MIN_WIDTH",
      "rule_name": "ADA Door Minimum Width",
      "element_guid": "abc123",
      "passed": false,
      "severity": "ERROR",
      "explanation": "Door abc123 has clear width of 750 mm...",
      "code_reference": "ADA 2010 Standards",
      "section": "303.2"
    }
  ]
}
```

## 🔗 API Endpoints

### Check Compliance
```
POST /api/compliance/check
Body: { "graph": {...} }
Returns: Detailed compliance results
```

### Get Rules
```
GET /api/compliance/enhanced-rules
Returns: All available regulation rules
```

### Export Report
```
POST /api/compliance/export-report
Body: { "check_results": {...} }
Returns: JSON file download
```

### Get Summary
```
POST /api/compliance/summary-by-rule
Body: { "check_results": {...} }
Returns: Results grouped by rule
```

## 🎓 Key Improvements

### Before:
```json
{
  "attr": "width_mm",
  "target_type": "door",
  "op": "<",
  "description": "Door width must be at least 813mm"
}
```
❌ Vague source, generic target, confusing logic, no explanations

### After:
```json
{
  "target": { "ifc_class": "IfcDoor" },
  "condition": {
    "lhs": { "source": "qto", "quantity": "ClearWidth", "unit": "mm" },
    "rhs": { "source": "parameter", "param": "min_clear_width_mm" }
  },
  "explanation": {
    "on_fail": "Door {guid} has {lhs} mm, below required {rhs} mm."
  }
}
```
✅ Explicit IFC structure, clear logic, parameterized explanations

## 🐛 Troubleshooting

**"Unable" results appear for some elements:**
- Element missing required QTO quantities
- Element doesn't have expected PSet properties
- IFC file may be incomplete
- This is normal - not all elements have all properties

**Compliance check is slow:**
- First run extracts data from IFC - takes time
- Large buildings (1000+ elements) may take 10+ seconds
- Results are cached in memory

**Export fails:**
- Check browser download permissions
- Ensure sufficient disk space
- Try again with smaller result set

## 📖 Learn More

- See `COMPLIANCE_SYSTEM_INTEGRATION.md` for full technical details
- See `enhanced-regulation-rules.json` for rule format specification
- Check `ComplianceCheckView.js` for UI component code

## ✅ Ready to Use!

The enhanced compliance checking system is fully integrated and ready for testing with your IFC models.

**Next Steps:**
1. Load an IFC file
2. Go to Compliance Checking section
3. Click "Run Compliance Check"
4. Review results and export reports as needed

Enjoy! 🎉
