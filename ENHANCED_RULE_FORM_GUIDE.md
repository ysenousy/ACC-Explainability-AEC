# Enhanced Rule Form - Complete Guide

## 📋 Overview

The new **Enhanced Add Rule Form** provides a comprehensive interface for creating sophisticated compliance rules in the enhanced rule format. It supports:

- **Multi-section form** with collapsible sections
- **IFC class targeting** with proper element filtering
- **Multiple data sources** (QTO, PSet, Attributes)
- **Complex conditions** with parameterized comparisons
- **Templated explanations** with variable substitution

## 🎯 Form Sections

### 1. **Basic Section**

Captures fundamental rule information:

| Field | Type | Required | Example |
|-------|------|----------|---------|
| **Rule ID** | Text | ✓ | `ADA_CORRIDOR_MIN_WIDTH_1` |
| **Name** | Text | ✓ | `ADA Corridor Minimum Width` |
| **Description** | Textarea | - | "Accessible corridors must meet ADA width standards..." |
| **Severity** | Dropdown | ✓ | ERROR, WARNING, INFO |
| **Regulation** | Text | - | `Americans with Disabilities Act (ADA)` |
| **Code Reference** | Text | - | `§403.5.1` or `Section 303.2` |

**Example Input:**
```
Rule ID: ADA_CORRIDOR_MIN_WIDTH_1
Name: ADA Corridor Minimum Width
Severity: ERROR
Regulation: Americans with Disabilities Act (ADA)
Code Reference: §403.5.1
```

### 2. **Target Section**

Defines which IFC elements the rule applies to:

**IFC Class Selection:**
- IfcDoor
- IfcSpace ← (Most common for dimensions)
- IfcWindow
- IfcWall
- IfcSlab
- IfcStairFlight
- IfcColumn
- IfcBeam

**Filters (Optional):**
Add multiple conditions to narrow element selection:

| Column | Values | Example |
|--------|--------|---------|
| **Type** | Property / Attribute | Property |
| **Pset Name** | Property Set name | `Pset_SpaceCommon` |
| **Property** | Property name | `Category` |
| **Operator** | = / != / > / < | `=` |
| **Value** | Specific value | `Corridor` |

**Example Setup:**
```
IFC Class: IfcSpace

Filter Row:
  Type: Property
  Pset: Pset_SpaceCommon
  Property: Category
  Operator: =
  Value: Corridor
```

This selects only Space elements where the Category property equals "Corridor"

### 3. **Condition Section**

Defines the comparison logic:

#### Left Hand Side (LHS) - What to Measure

**Source Type Options:**

| Type | Use Case | Fields |
|------|----------|--------|
| **Quantity (QTO)** | Measured dimensions (width, area, height) | QTO Name, Quantity Name, Unit |
| **Property Set (PSet)** | Named properties | PSet Name, Property Name, Unit |
| **Attribute** | Direct element attributes | Attribute Name, Unit |

**Example - Using QTO (Most Common):**
```
Source Type: Quantity (Qto)
QTO Name: Qto_SpaceBaseQuantities
Quantity Name: Width
Unit: mm
```

#### Operator

Choose the comparison logic:
- **≥** (greater than or equal) - Most common for minimums
- **>** (greater than)
- **≤** (less than or equal) - For maximums
- **<** (less than)
- **=** (equals)
- **≠** (not equals)

#### Right Hand Side (RHS) - The Requirement

**Type Options:**

| Type | Use | Example |
|------|-----|---------|
| **Constant** | Fixed requirement value | `914` (mm) |
| **Parameter** | Create parameterized rule | `min_corridor_width_mm` |

**When using Constant:**
```
RHS Type: Constant
Value: 914
Unit: mm
```

**When using Parameter:**
```
RHS Type: Parameter
Parameter: min_corridor_width_mm
(Parameter value gets added to rule.parameters)
```

**Full Condition Example:**
```
LHS: Qto_SpaceBaseQuantities → Width (mm)
≥
RHS: Constant → 914 mm
```
Meaning: Width must be ≥ 914 mm

### 4. **Explanation & Messaging Section**

Defines user-friendly output messages:

#### Short Message
Brief description of what the rule checks:
```
"Accessible corridors must be at least 914 mm wide."
```

#### On Fail Message
Shown when element fails the check. Supports template variables:

**Available Variables:**
- `{guid}` - Element GUID/ID
- `{lhs}` - Actual measured value
- `{rhs}` - Required value
- `{unit}` - Measurement unit

**Example:**
```
"Corridor {guid} has width {lhs} mm, below required {rhs} mm."
```

Result: `"Corridor abc123def has width 800 mm, below required 914 mm."`

#### On Pass Message
Shown when element passes. Same template variables available:

**Example:**
```
"Corridor {guid} meets the ADA width requirement ({lhs} mm ≥ {rhs} mm)."
```

Result: `"Corridor xyz789 meets the ADA width requirement (950 mm ≥ 914 mm)."`

## 📝 Complete Example: ADA Corridor Width

### Step 1: Basic Tab
```
Rule ID:        ADA_CORRIDOR_MIN_WIDTH_1
Name:           ADA Corridor Minimum Width
Description:    Checks that accessible corridors meet minimum width requirements
Severity:       ERROR
Regulation:     Americans with Disabilities Act (ADA)
Code Reference: §403.5.1
```

### Step 2: Target Tab
```
IFC Class: IfcSpace

Filter:
  Type:      Property
  Pset:      Pset_SpaceCommon
  Property:  Category
  Operator:  =
  Value:     Corridor
```

### Step 3: Condition Tab
```
LHS:
  Source Type:  Quantity (Qto)
  QTO Name:     Qto_SpaceBaseQuantities
  Quantity:     Width
  Unit:         mm

Operator: ≥

RHS:
  Type:  Constant
  Value: 914
  Unit:  mm
```

### Step 4: Explanation Tab
```
Short Message:
  "Accessible corridors must be at least 914 mm wide."

On Fail Message:
  "Corridor {guid} has width {lhs} mm, below required {rhs} mm."

On Pass Message:
  "Corridor {guid} meets ADA width requirements ({lhs} mm ≥ {rhs} mm)."
```

### Result

Generates this rule in enhanced format:
```json
{
  "id": "ADA_CORRIDOR_MIN_WIDTH_1",
  "name": "ADA Corridor Minimum Width",
  "rule_type": "attribute_comparison",
  "description": "Checks that accessible corridors meet minimum width requirements",
  "target": {
    "ifc_class": "IfcSpace",
    "selector": {
      "filters": [
        {
          "pset": "Pset_SpaceCommon",
          "property": "Category",
          "op": "=",
          "value": "Corridor"
        }
      ]
    }
  },
  "condition": {
    "op": ">=",
    "lhs": {
      "source": "qto",
      "qto_name": "Qto_SpaceBaseQuantities",
      "quantity": "Width",
      "unit": "mm"
    },
    "rhs": {
      "source": "constant",
      "value": 914,
      "unit": "mm"
    }
  },
  "parameters": {},
  "severity": "ERROR",
  "explanation": {
    "short": "Accessible corridors must be at least 914 mm wide.",
    "on_fail": "Corridor {guid} has width {lhs} mm, below required {rhs} mm.",
    "on_pass": "Corridor {guid} meets ADA width requirements ({lhs} mm ≥ {rhs} mm)."
  },
  "provenance": {
    "source": "regulation",
    "regulation": "Americans with Disabilities Act (ADA)",
    "section": "§403.5.1",
    "jurisdiction": "US"
  }
}
```

## 🎯 Common Rule Patterns

### Pattern 1: Minimum Dimension (Door Width)
```
Target:    IfcDoor + IsAccessible=true filter
LHS:       Qto_DoorBaseQuantities → ClearWidth (mm)
Operator:  >=
RHS:       813 (ADA requirement)
```

### Pattern 2: Room Area
```
Target:    IfcSpace + Category=Bedroom filter
LHS:       Qto_SpaceBaseQuantities → FloorArea (m2)
Operator:  >=
RHS:       6.5 (Minimum bedroom area)
```

### Pattern 3: Window Size
```
Target:    IfcWindow + IsExternal=true filter
LHS:       Qto_WindowBaseQuantities → Area (m2)
Operator:  >=
RHS:       0.93 (Minimum window area)
```

### Pattern 4: Parameterized Rule
```
Target:    IfcSpace
LHS:       Qto_SpaceBaseQuantities → Width (mm)
Operator:  >=
RHS:       Parameter: min_space_width_mm
(Makes rule reusable with different values)
```

## 🔄 Workflow

1. **Click "Create New Rule"** in Rule Management panel
2. **Fill Basic Information** - Rule ID, Name, Severity
3. **Define Target** - Select IFC Class and add filters
4. **Set Condition** - LHS source, operator, RHS value
5. **Write Messages** - Explain to users what was checked
6. **Save Rule** - Rule is stored and can be used immediately

## ✅ Validation

Form validates:
- ✓ Rule ID and Name are required
- ✓ IFC Class is required
- ✓ At least one LHS source is specified
- ✓ RHS value or parameter is provided
- ✓ All operator selections are valid

## 🎨 UI Features

**Collapsible Sections:** Click header to expand/collapse
**Color Coding:**
- Green: Add/Save buttons
- Red: Delete buttons
- Gray: Cancel/Secondary actions
- Blue: Primary actions

**Inline Help:**
- Placeholder text shows examples
- Small text describes template variables
- Clear field labels

## 📱 Responsive Design

Form adapts to container width:
- Full width on desktop
- Single column on mobile
- Scrollable content area

## 🚀 Future Enhancements

Potential additions:
- Rule templates (copy existing rules)
- Import from JSON
- Rule testing/preview
- Batch rule creation
- Custom parameter names
- Advanced logical operators (AND/OR)
