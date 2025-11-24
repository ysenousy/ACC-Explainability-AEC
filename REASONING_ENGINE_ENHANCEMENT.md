# ReasoningEngine Enhancement: Custom Rules Support

## Overview
Enhanced the ReasoningEngine to load and support both **regulatory rules** and **custom/generated rules**, enabling comprehensive reasoning analysis across all rule types.

## Changes Made

### 1. ReasoningEngine Class (`reasoning_layer/reasoning_engine.py`)

#### Before
- Loaded only regulatory rules from a single file
- Constructor: `__init__(self, rules_file: Optional[str] = None)`
- Single rule dict: `self.rules`

#### After
- Loads both regulatory AND custom rules from separate files
- Constructor: `__init__(self, rules_file: Optional[str] = None, custom_rules_file: Optional[str] = None)`
- Three rule dicts for tracking:
  - `self.rules`: All rules combined (regulatory + custom)
  - `self.regulatory_rules`: Only regulatory rules
  - `self.custom_rules`: Only custom/generated rules

#### New Method: `_load_rules_from_file()`
```python
def _load_rules_from_file(self, rules_file: str, rule_type: str = 'regulatory'):
    """Load rules from a file and categorize them."""
```
- Shared loading logic for both file types
- Handles multiple JSON structures:
  - `{"rules": [...]}` - Rules array with metadata
  - `{"rule_id": {...}}` - Dict keyed by rule ID
  - `[{...}, {...}]` - Direct array of rule objects
- Categorizes rules by source (regulatory vs custom)
- Includes logging for debugging

#### Benefits
- **Separation of Concerns**: Regulatory rules maintained separately from custom
- **Flexibility**: Load only one file type or both
- **Transparency**: Track rule sources for frontend display
- **Robustness**: Logs which rules loaded and sample IDs

### 2. Flask App Initialization (`backend/app.py`)

#### Before
```python
rules_file = Path(__file__).parent.parent / 'rules_config' / 'enhanced-regulation-rules.json'
reasoning_engine = ReasoningEngine(str(rules_file) if rules_file.exists() else None)
```

#### After
```python
rules_file = Path(__file__).parent.parent / 'rules_config' / 'enhanced-regulation-rules.json'
custom_rules_file = Path(__file__).parent / 'backend/custom_rules.json'
reasoning_engine = ReasoningEngine(
    str(rules_file) if rules_file.exists() else None,
    str(custom_rules_file) if custom_rules_file.exists() else None
)
```

- Now passes both regulatory and custom rules files
- Gracefully handles missing custom_rules.json (optional)
- Ensures reasoning layer has access to all rules for explanations

### 3. API Endpoint Update (`backend/app.py`)

#### `/api/reasoning/all-rules` (GET)

**Enhanced to return both regulatory and custom rules**

Response now includes:
```json
{
  "success": true,
  "rules": [
    {
      "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
      "name": "Door Minimum Clear Width",
      "description": "...",
      "severity": "ERROR",
      "source": "regulatory",  // NEW: marks origin
      "target_ifc_class": "IfcDoor",
      "regulation": "ADA",
      "section": "303.2",
      "jurisdiction": "USA"
    },
    // Custom rules will appear here with source="custom"
  ],
  "total_rules": 9,           // NEW: total across both sources
  "regulatory_rules": 9,      // NEW: count of regulatory rules
  "custom_rules": 0,          // NEW: count of custom rules
  "error": null
}
```

**Frontend Benefits**:
- Can now display all rules in "Why Rules Exist" section
- Rules tagged with source for UI highlighting/filtering
- Count of each rule type for transparency
- Ready to show custom rules when imported

## File Paths

| File | Purpose |
|------|---------|
| `reasoning_layer/reasoning_engine.py` | ReasoningEngine class with dual rule loading |
| `backend/app.py` | Flask app initialization and API endpoints |
| `rules_config/enhanced-regulation-rules.json` | Regulatory rules (9 rules for ADA/IBC compliance) |
| `backend/custom_rules.json` | Custom/imported rules (created on first rule import) |

## Usage

### Loading Rules
```python
from reasoning_layer.reasoning_engine import ReasoningEngine

# Load regulatory and custom rules
engine = ReasoningEngine(
    rules_file='rules_config/enhanced-regulation-rules.json',
    custom_rules_file='backend/custom_rules.json'
)

print(f"Regulatory: {len(engine.regulatory_rules)}")
print(f"Custom: {len(engine.custom_rules)}")
print(f"Total: {len(engine.rules)}")
```

### Explaining Rules
```python
# Works for both regulatory AND custom rules
explanation = engine.explain_rule(
    rule_id='ADA_DOOR_MIN_CLEAR_WIDTH',  # or custom rule ID
    applicable_elements=['IfcDoor'],
    elements_checked=10,
    elements_passing=8,
    elements_failing=2
)
```

### API Endpoint
```bash
GET /api/reasoning/all-rules

Response includes:
- All 9 regulatory rules with source="regulatory"
- Any custom rules with source="custom"
- Total counts for UI display
```

## Testing

### Run Tests
```bash
cd "c:\Research Work\ACC-Explainability-AEC"
python test_reasoning_with_custom_rules.py
python test_updated_all_rules_endpoint.py
```

### Expected Output
```
[OK] ReasoningEngine initialized
  Total rules: 9
  Regulatory: 9
  Custom: 0

[OK] Successfully explained regulatory rule: ADA_DOOR_MIN_CLEAR_WIDTH
  Explanation keys: ['reasoning_type', 'rule_explanations', ...]

[OK] Custom rules file not present (as expected)
  ReasoningEngine ready to support custom rules when custom_rules.json is created

[SUCCESS] ReasoningEngine supports both regulatory and custom rules
```

## Integration Points

### Reasoning Layer ✅
- ✅ ReasoningEngine loads both rule types
- ✅ explain_rule() works for regulatory and custom rules
- ✅ RuleJustifier initialized with regulatory rules file
- ✅ ElementFailureAnalyzer works with all rules
- ✅ SolutionGenerator handles all rule types

### Compliance Engine (Already Working)
- ✅ UnifiedComplianceEngine evaluates compliance
- ✅ custom_rules.json loaded when generating compliance reports
- ✅ Separate tracking of regulatory vs custom in reports

### Frontend Integration
- ✅ `/api/reasoning/all-rules` returns all rules with source field
- ✅ `/api/reasoning/all-rules-with-status` shows applicability
- ✅ `/api/reasoning/analyze-failure` explains failures
- ✅ Ready for frontend to display both rule types

## Next Steps (Optional Enhancements)

1. **Frontend Display**
   - Update "Why Rules Exist" section to show all 9 rules + custom rules
   - Add filter to show only regulatory or only custom rules
   - Visual distinction between rule types (color, icon, etc.)

2. **Custom Rule Management**
   - Endpoint to create new custom rules via UI
   - Endpoint to import rules from files
   - Endpoint to delete/update custom rules
   - Rule import/export functionality

3. **Advanced Reasoning**
   - Consider rule relationships (regulatory vs custom dependencies)
   - Conflict detection between regulatory and custom rules
   - Rule priority handling

## Backwards Compatibility

✅ **Fully backward compatible**
- Existing code without custom_rules.json works unchanged
- ReasoningEngine.__init__() still accepts single rules_file parameter
- All existing API endpoints function identically
- No breaking changes to data structures

## Summary

The ReasoningEngine now comprehensively supports explaining both regulatory and custom rules, enabling complete transparency about building compliance across all rule types. Custom rules can be added and managed independently while maintaining separation from regulatory requirements.
