# Creating Regulation-Based Rules for IFC Compliance Checking

## Overview

This guide shows how to create common compliance rules based on building regulations that can be checked against IFC files.

## Rule JSON Structure

Each rule has this complete structure:

```json
{
  "id": "UNIQUE_RULE_ID",
  "name": "Human-readable rule name",
  "description": "What this rule checks and why it matters",
  "target_type": "door|space|window|building|stair",
  "selector": {
    "by": "type|property|custom",
    "value": "value_to_match",
    "operator": "equals|contains|greater_than|less_than"
  },
  "condition": {
    "op": "<|>|<=|>=|==|!=",
    "lhs": {
      "attr": "width_mm|height_mm|area_m2|etc"
    },
    "rhs": {
      "param": "parameter_name"
    }
  },
  "parameters": {
    "min_width_mm": 900,
    "max_height_mm": 2400
  },
  "severity": "ERROR|WARNING|INFO",
  "code_reference": "Building Code Section 1.2.3",
  "provenance": {
    "source": "regulation",
    "regulation": "Building Code 2020",
    "section": "1.2.3",
    "country": "US",
    "state": "CA"
  }
}
```

## Common Regulation Rules Examples

### 1. Accessibility Rules (ADA Compliance)

#### Door Width Requirement
```json
{
  "id": "ADA_DOOR_MIN_WIDTH",
  "name": "ADA Door Minimum Width",
  "description": "All doors must have minimum 32 inches (813mm) clear opening width for wheelchair accessibility",
  "target_type": "door",
  "selector": {
    "by": "type",
    "value": "door"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "width_mm"
    },
    "rhs": {
      "param": "min_clear_width_mm"
    }
  },
  "parameters": {
    "min_clear_width_mm": 813
  },
  "severity": "ERROR",
  "code_reference": "ADA 2010 Standards Section 303.2",
  "provenance": {
    "source": "regulation",
    "regulation": "Americans with Disabilities Act (ADA)",
    "section": "303.2",
    "country": "US"
  }
}
```

#### Corridor Width Requirement
```json
{
  "id": "ADA_CORRIDOR_MIN_WIDTH",
  "name": "ADA Corridor Minimum Width",
  "description": "All accessible routes and corridors must be at least 36 inches (914mm) wide",
  "target_type": "space",
  "selector": {
    "by": "property",
    "value": "corridor"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "width_mm"
    },
    "rhs": {
      "param": "min_corridor_width_mm"
    }
  },
  "parameters": {
    "min_corridor_width_mm": 914
  },
  "severity": "ERROR",
  "code_reference": "ADA 2010 Standards Section 304",
  "provenance": {
    "source": "regulation",
    "regulation": "Americans with Disabilities Act (ADA)",
    "section": "304",
    "country": "US"
  }
}
```

### 2. Fire Safety Rules (Building Code)

#### Exit Door Height
```json
{
  "id": "FIRE_EXIT_DOOR_HEIGHT",
  "name": "Fire Exit Door Minimum Height",
  "description": "All exit doors must have minimum height of 78 inches (1980mm)",
  "target_type": "door",
  "selector": {
    "by": "property",
    "value": "exit"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "height_mm"
    },
    "rhs": {
      "param": "min_exit_height_mm"
    }
  },
  "parameters": {
    "min_exit_height_mm": 1980
  },
  "severity": "ERROR",
  "code_reference": "IBC 2018 Section 1005.1",
  "provenance": {
    "source": "regulation",
    "regulation": "International Building Code (IBC)",
    "section": "1005.1",
    "country": "US"
  }
}
```

#### Stairway Width
```json
{
  "id": "IBC_STAIR_MIN_WIDTH",
  "name": "Stair Minimum Width",
  "description": "All stairs must have minimum width of 44 inches (1118mm)",
  "target_type": "stair",
  "selector": {
    "by": "type",
    "value": "stair"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "width_mm"
    },
    "rhs": {
      "param": "min_stair_width_mm"
    }
  },
  "parameters": {
    "min_stair_width_mm": 1118
  },
  "severity": "ERROR",
  "code_reference": "IBC 2018 Section 1003.3.1.1",
  "provenance": {
    "source": "regulation",
    "regulation": "International Building Code (IBC)",
    "section": "1003.3.1.1",
    "country": "US"
  }
}
```

### 3. Room Size Requirements

#### Bedroom Minimum Area
```json
{
  "id": "BUILD_BEDROOM_MIN_AREA",
  "name": "Bedroom Minimum Area",
  "description": "Bedrooms must have minimum floor area of 70 square feet (6.5 m²)",
  "target_type": "space",
  "selector": {
    "by": "property",
    "value": "bedroom"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "area_m2"
    },
    "rhs": {
      "param": "min_bedroom_area_m2"
    }
  },
  "parameters": {
    "min_bedroom_area_m2": 6.5
  },
  "severity": "ERROR",
  "code_reference": "IBC 2018 Section 1205.2.1",
  "provenance": {
    "source": "regulation",
    "regulation": "International Building Code (IBC)",
    "section": "1205.2.1",
    "country": "US"
  }
}
```

#### Bathroom Minimum Area
```json
{
  "id": "BUILD_BATHROOM_MIN_AREA",
  "name": "Bathroom Minimum Area",
  "description": "Bathrooms must have minimum floor area of 35 square feet (3.25 m²)",
  "target_type": "space",
  "selector": {
    "by": "property",
    "value": "bathroom"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "area_m2"
    },
    "rhs": {
      "param": "min_bathroom_area_m2"
    }
  },
  "parameters": {
    "min_bathroom_area_m2": 3.25
  },
  "severity": "ERROR",
  "code_reference": "IBC 2018 Section 1205.2.2",
  "provenance": {
    "source": "regulation",
    "regulation": "International Building Code (IBC)",
    "section": "1205.2.2",
    "country": "US"
  }
}
```

### 4. Window Requirements

#### Window Size in Bedrooms
```json
{
  "id": "BUILD_BEDROOM_WINDOW_MIN",
  "name": "Bedroom Window Minimum Size",
  "description": "Bedrooms must have windows with minimum area of 10% of floor area or 10 square feet, whichever is larger",
  "target_type": "window",
  "selector": {
    "by": "property",
    "value": "bedroom_window"
  },
  "condition": {
    "op": "<",
    "lhs": {
      "attr": "area_m2"
    },
    "rhs": {
      "param": "min_window_area_m2"
    }
  },
  "parameters": {
    "min_window_area_m2": 0.93
  },
  "severity": "WARNING",
  "code_reference": "IBC 2018 Section 1205.2.4",
  "provenance": {
    "source": "regulation",
    "regulation": "International Building Code (IBC)",
    "section": "1205.2.4",
    "country": "US"
  }
}
```

## How to Use These Rules

### Step 1: Create a Regulation Rules JSON File

Save rules in a file like `ibc-2018-rules.json`:

```json
{
  "rules": [
    {
      "id": "ADA_DOOR_MIN_WIDTH",
      "name": "ADA Door Minimum Width",
      ...
    },
    {
      "id": "IBC_STAIR_MIN_WIDTH",
      "name": "Stair Minimum Width",
      ...
    }
  ],
  "metadata": {
    "regulation_set": "IBC 2018 + ADA",
    "version": "1.0",
    "jurisdiction": "United States",
    "created": "2025-11-20"
  }
}
```

### Step 2: Upload to the Application

1. Go to **Rule Layer → Rules**
2. Click **"View Catalogue"**
3. Click **"Import"** button
4. Select your `ibc-2018-rules.json` file
5. Rules are now loaded in the catalogue

### Step 3: Check Rules Against IFC

1. Go to **Rule Layer → Check Rules**
2. Select rules to check
3. System evaluates IFC elements against rules
4. View violations and warnings

## Rule Parameter Reference

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

### Severity Levels
- **ERROR** - Code violation, must be fixed
- **WARNING** - Best practice or recommendable, should be reviewed
- **INFO** - Informational, no action required

## Creating Custom Regulation Rules

### For Different Jurisdictions:

**UK Building Regulations:**
```json
{
  "id": "UK_DOOR_WIDTH_ACCESSIBLE",
  "name": "UK Accessible Door Width",
  "description": "Accessible doors must be at least 775mm wide",
  "target_type": "door",
  "severity": "ERROR",
  "code_reference": "UK Building Regulations 2010 Technical Guidance M",
  "parameters": {
    "min_width_mm": 775
  }
}
```

**EU Accessibility Standards:**
```json
{
  "id": "EN_CORRIDOR_WIDTH",
  "name": "EN Corridor Minimum Width",
  "description": "Corridors must be at least 900mm wide per EN standards",
  "target_type": "space",
  "severity": "ERROR",
  "code_reference": "EN 17210:2021",
  "parameters": {
    "min_corridor_width_mm": 900
  }
}
```

**Canadian Building Code:**
```json
{
  "id": "NBC_DOOR_WIDTH_ACCESSIBLE",
  "name": "NBC Accessible Door Width",
  "description": "Accessible doors must be at least 750mm wide",
  "target_type": "door",
  "severity": "ERROR",
  "code_reference": "NBC 2020 Accessibility Requirements",
  "parameters": {
    "min_width_mm": 750
  }
}
```

## Best Practices

1. **Unique IDs**: Use format `[REGULATION]_[ELEMENT]_[CHECK]` (e.g., `ADA_DOOR_MIN_WIDTH`)
2. **Clear Names**: Make rule names self-explanatory
3. **Code References**: Always include the specific regulation section
4. **Parameter Documentation**: Add comments explaining why parameters were chosen
5. **Severity Assignment**: 
   - ERROR for legal/safety violations
   - WARNING for best practices
   - INFO for informational items
6. **Provenance Tracking**: Record where rules came from for auditability

## Workflow Example

```json
{
  "rules": [
    {
      "id": "PROJECT_RULES_001",
      "name": "Main Entrance Door Width",
      "description": "Primary access doors must be minimum 1000mm wide for emergency access",
      "target_type": "door",
      "selector": {
        "by": "property",
        "value": "main_entrance"
      },
      "condition": {
        "op": "<",
        "lhs": {"attr": "width_mm"},
        "rhs": {"param": "min_width_mm"}
      },
      "parameters": {
        "min_width_mm": 1000
      },
      "severity": "ERROR",
      "code_reference": "Project Specifications v1.0",
      "provenance": {
        "source": "regulation",
        "regulation": "Project Requirements",
        "section": "Access Requirements",
        "country": "US",
        "state": "CA",
        "created_by": "Architect",
        "created_date": "2025-11-20"
      }
    }
  ]
}
```

## Using in the Application

### Import via UI:
1. Create JSON file with rules
2. Go to Rules section
3. Click Import button
4. Select file
5. Rules are saved to `custom_rules.json`

### Generate Rules from IFC:
1. Upload IFC file
2. Go to Generate Rule section
3. Select extraction strategies
4. System auto-generates rules from IFC data

### Check Rules:
1. Go to Check Rules section
2. Select which rules to validate
3. View detailed compliance report
4. Export results

## Next Steps

1. Create regulation-specific rule sets for your jurisdiction
2. Organize rules by category (accessibility, fire safety, etc.)
3. Version control your rule sets
4. Build rule libraries for different projects
5. Share rules across teams and projects
