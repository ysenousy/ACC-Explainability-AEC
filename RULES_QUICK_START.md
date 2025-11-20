# Regulation Rules - Quick Start Guide

## What Are Regulation Rules?

Regulation rules are JSON-based compliance checks that verify your IFC building model against building codes and standards (ADA, IBC, etc.).

## File Location

- **Template**: `common-regulation-rules.json` (ready to use)
- **Full Guide**: `REGULATION_RULES_GUIDE.md` (detailed documentation)

## Quick Usage

### Step 1: Get the Rules File

Use the provided `common-regulation-rules.json` which includes:
- ✅ ADA Accessibility Standards (US)
- ✅ IBC 2018 Building Code (US)
- ✅ UK Building Regulations
- ✅ EU EN Standards
- ✅ Canadian NBC Standards

### Step 2: Import Rules into Application

1. Open the ACC-Explainability application
2. Navigate to **Rule Layer → Rules → View Catalogue**
3. Click **Import** button
4. Select `common-regulation-rules.json`
5. Rules now appear in your catalogue

### Step 3: Check Your IFC Model

1. Upload your IFC file (via "Browse IFC" button)
2. Go to **Rule Layer → Check Rules**
3. Select which rules to check
4. Click **Analyze**
5. View violations and warnings

### Step 4: Export Results

- View detailed compliance report
- Export violations to JSON
- Generate summary document

---

## Rule Categories

### 🚪 Accessibility Rules
- Door minimum widths (ADA, UK, EU, Canada)
- Corridor minimum widths
- Accessible route requirements

### 🔥 Fire Safety Rules
- Exit door heights
- Stairway widths
- Emergency access requirements

### 🏠 Room Dimension Rules
- Bedroom minimum areas
- Bathroom minimum areas
- Window size requirements

---

## Rule Structure (Quick Reference)

Each rule contains:

```
ID                 → Unique identifier (e.g., ADA_DOOR_MIN_WIDTH)
Name               → What the rule checks
Description        → Why it matters
Target Type        → What it applies to (door, space, window, etc.)
Condition          → The actual check (e.g., width < 813mm)
Parameters         → The values used (e.g., min_clear_width_mm: 813)
Severity           → ERROR, WARNING, or INFO
Code Reference     → Which regulation (e.g., "ADA Section 303.2")
```

---

## Creating Custom Regulation Rules

### Template for Your Own Rule

```json
{
  "id": "YOUR_CODE_RULE_ID",
  "name": "Your Rule Name",
  "description": "What this rule checks",
  "target_type": "door|space|window|building|stair",
  "selector": {
    "by": "type",
    "value": "element_type"
  },
  "condition": {
    "op": "<",
    "lhs": {"attr": "width_mm"},
    "rhs": {"param": "min_width_mm"}
  },
  "parameters": {
    "min_width_mm": 800
  },
  "severity": "ERROR",
  "code_reference": "Your Building Code Section X.Y.Z",
  "provenance": {
    "source": "regulation",
    "regulation": "Your Regulation Name",
    "section": "X.Y.Z",
    "country": "Country"
  }
}
```

### Steps to Create Custom Rules

1. Copy `common-regulation-rules.json`
2. Rename to `your-rules.json`
3. Keep the outer structure: `{ "rules": [...], "metadata": {...} }`
4. Add your custom rules to the `rules` array
5. Update `metadata` section
6. Save and import into the application

---

## Supported Attributes for Checking

### Door/Window Attributes
- `width_mm` - Width in millimeters
- `height_mm` - Height in millimeters
- `area_m2` - Area in square meters
- `clear_width_mm` - Clear opening width
- `sill_height_mm` - Window sill height

### Space Attributes
- `area_m2` - Floor area in square meters
- `width_mm` - Room width
- `length_mm` - Room length
- `height_mm` - Ceiling height
- `perimeter_m` - Room perimeter

---

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **ERROR** | Code violation - must be fixed | Critical - Fix before submission |
| **WARNING** | Best practice - should review | Important - Address if possible |
| **INFO** | Informational only | FYI - No action required |

---

## Example Regulations Included

### ADA (Americans with Disabilities Act)
- Door Minimum Width: 813mm (32")
- Corridor Minimum Width: 914mm (36")

### IBC (International Building Code 2018)
- Exit Door Height: 1980mm (78")
- Stair Width: 1118mm (44")
- Bedroom Area: 6.5m² (70 sq ft)
- Bathroom Area: 3.25m² (35 sq ft)

### UK Building Regulations
- Accessible Door Width: 775mm

### EU Standards (EN 17210:2021)
- Corridor Width: 900mm

### Canada (NBC 2020)
- Accessible Door Width: 750mm

---

## Workflow Example

```
1. Upload IFC File
   ↓
2. Review Data Layer (see spaces, doors, etc.)
   ↓
3. Go to Rule Layer → Rules
   ↓
4. Import regulation rules (or generate from IFC)
   ↓
5. Go to Rule Layer → Check Rules
   ↓
6. Select rules to verify
   ↓
7. View compliance report
   ↓
8. Export violations as JSON
   ↓
9. Fix issues in model
   ↓
10. Re-check for compliance
```

---

## Tips & Tricks

### Organizing Rules
- Group by jurisdiction (US, UK, EU, CA)
- Group by category (accessibility, fire, etc.)
- Version control your rule files

### Updating Rules
- When building codes change, update parameters
- Add new rules as standards evolve
- Keep old versions for historical reference

### Sharing Rules
- Export your custom rules
- Share with team members
- Build organization-wide rule library

### Troubleshooting
- **No violations found**: Rules may not match element types in your IFC
- **Too many violations**: Check rule parameters are correct
- **Rules won't import**: Verify JSON format is valid

---

## Next Steps

1. **Import** `common-regulation-rules.json` into the app
2. **Upload** your IFC model
3. **Check** compliance against regulations
4. **Review** violations and warnings
5. **Export** results for reporting
6. **Create** custom rules for your project/jurisdiction

See `REGULATION_RULES_GUIDE.md` for detailed information!
