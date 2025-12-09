# Rules Versioning System - Complete Guide

## Overview

The Rules Versioning System preserves **original rule files** while allowing **runtime modifications** to create new versions. This ensures:

✅ **Original files never change** - v0 is the permanent baseline  
✅ **All modifications tracked** - Complete audit trail  
✅ **Easy rollback** - Can revert to any previous version  
✅ **No data loss** - All versions stored in `rules_config/versions/`  
✅ **Version comparison** - See what changed between versions  

## Architecture

```
rules_config/
├── enhanced-regulation-rules.json      ← Original (loaded on first run)
├── unified_rules_mapping.json          ← Original (loaded on first run)
├── execution-config.json
├── custom_rules.json
└── versions/
    ├── v0/                             ← Original baseline (read-only)
    │   ├── enhanced-regulation-rules.json
    │   └── unified_rules_mapping.json
    ├── v1/                             ← First user modification
    │   ├── enhanced-regulation-rules.json
    │   └── unified_rules_mapping.json
    ├── v2/                             ← Second user modification
    │   ├── enhanced-regulation-rules.json
    │   └── unified_rules_mapping.json
    ├── version_manifest.json           ← Metadata for all versions
    └── README.md
```

## Data Flow

```
User Modifies Rules in UI
        ↓
Frontend sends to /api/rules/versions/save
        ↓
Backend validates modifications
        ↓
Creates new version directory (vN/)
        ↓
Copies modified rules to vN/
        ↓
Updates version_manifest.json
        ↓
Sets current_version = vN
        ↓
Compliance Check uses current version
Reporting uses current version
Training uses current version
```

## API Endpoints

### 1. Get Current Version

```bash
GET /api/rules/versions/current
```

**Response:**
```json
{
  "status": "success",
  "current_version": 1,
  "version_info": {
    "version_id": 1,
    "label": "User Modifications #1",
    "created_at": "2025-12-09T14:30:00Z",
    "created_by": "user",
    "description": "Updated ADA door clearance requirements",
    "num_rules": 14,
    "rule_ids": [...]
  },
  "num_rules": 14,
  "num_mappings": 42
}
```

### 2. List All Versions

```bash
GET /api/rules/versions/list
```

**Response:**
```json
{
  "status": "success",
  "total_versions": 3,
  "current_version": 1,
  "versions": [
    {
      "version_id": 0,
      "label": "Original",
      "created_at": "2025-12-09T00:00:00Z",
      "created_by": "system",
      "description": "Original rules configuration",
      "num_rules": 14,
      "modifications": []
    },
    {
      "version_id": 1,
      "label": "User Modifications #1",
      "created_at": "2025-12-09T14:30:00Z",
      "created_by": "user",
      "description": "Updated ADA door clearance requirements",
      "num_rules": 14,
      "modifications": [...]
    }
  ]
}
```

### 3. Get Specific Version

```bash
GET /api/rules/versions/<version_id>
```

**Example:**
```bash
GET /api/rules/versions/0
```

**Response:**
```json
{
  "status": "success",
  "version_id": 0,
  "version_info": {...},
  "rules": {...},
  "mappings": {...}
}
```

### 4. Save New Version (User Modification)

```bash
POST /api/rules/versions/save
Content-Type: application/json

{
  "rules": {
    "rules": [
      {
        "id": "ADA_DOOR_MIN_CLEAR_WIDTH",
        "name": "ADA Accessible Door Minimum Clear Width",
        "description": "...",
        "parameters": {
          "min_clear_width_mm": 815
        }
      },
      ...
    ]
  },
  "mappings": {...},
  "description": "Updated ADA door clearance requirements",
  "modifications": [
    {
      "type": "rule_update",
      "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
      "field": "parameters.min_clear_width_mm",
      "old_value": 762,
      "new_value": 815
    }
  ],
  "created_by": "user"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "New version 2 created successfully",
  "new_version_id": 2,
  "version_info": {...}
}
```

### 5. Rollback to Previous Version

```bash
POST /api/rules/versions/rollback/<version_id>
```

**Example:**
```bash
POST /api/rules/versions/rollback/0
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully rolled back to version 0",
  "version_id": 0,
  "num_rules": 14
}
```

### 6. Compare Two Versions

```bash
GET /api/rules/versions/compare/<version_id_1>/<version_id_2>
```

**Example:**
```bash
GET /api/rules/versions/compare/0/1
```

**Response:**
```json
{
  "status": "success",
  "comparison": {
    "version_1": 0,
    "version_2": 1,
    "rules_added": [],
    "rules_removed": [],
    "rules_modified": ["ADA_DOOR_MIN_CLEAR_WIDTH", "IBC_STAIR_MIN_WIDTH"],
    "mappings_changed": true
  }
}
```

### 7. Get Original Version (v0)

```bash
GET /api/rules/versions/original
```

**Response:**
```json
{
  "status": "success",
  "version_id": 0,
  "version_info": {...},
  "rules": {...},
  "mappings": {...},
  "message": "Original rules (v0) - baseline configuration"
}
```

### 8. Export Version

```bash
POST /api/rules/versions/export/<version_id>
```

**Example:**
```bash
POST /api/rules/versions/export/1
```

**Response:**
```json
{
  "status": "success",
  "message": "Version 1 exported successfully",
  "export_data": {
    "export_timestamp": "2025-12-09T15:00:00Z",
    "version_id": 1,
    "version_info": {...},
    "rules": {...},
    "mappings": {...}
  }
}
```

## Python Usage (Backend)

### Initialize Version Manager

```python
from backend.rules_version_manager import RulesVersionManager
from pathlib import Path

rules_config_path = Path("rules_config")
version_manager = RulesVersionManager(str(rules_config_path))
```

### Load Rules from Specific Version

```python
# Load current version
rules, mappings = version_manager.load_rules()

# Load specific version
rules, mappings = version_manager.load_rules(version_id=1)

# Load original (v0)
rules, mappings = version_manager.load_rules(version_id=0)
```

### Create New Version

```python
# After user modifies rules
new_version_id = version_manager.create_new_version(
    rules_dict=modified_rules,
    mappings_dict=modified_mappings,
    description="Updated door width requirements",
    modifications=[
        {
            "type": "rule_update",
            "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
            "field": "parameters.min_clear_width_mm",
            "old_value": 762,
            "new_value": 815
        }
    ],
    created_by="user"
)
print(f"New version: {new_version_id}")
```

### Rollback to Previous Version

```python
# Rollback to version 0 (original)
rules, mappings = version_manager.rollback_to(version_id=0)

# Rollback to version 1
rules, mappings = version_manager.rollback_to(version_id=1)
```

### Compare Versions

```python
diff = version_manager.get_version_diff(version_id_1=0, version_id_2=1)

print(f"Rules added: {diff['rules_added']}")
print(f"Rules removed: {diff['rules_removed']}")
print(f"Rules modified: {diff['rules_modified']}")
print(f"Mappings changed: {diff['mappings_changed']}")
```

### List All Versions

```python
versions = version_manager.list_all_versions()

for v in versions:
    print(f"v{v['version_id']}: {v['label']} - {v['description']}")
    print(f"  Created: {v['created_at']}")
    print(f"  By: {v['created_by']}")
    print(f"  Rules: {v['num_rules']}")
    print()
```

### Get Current Version Info

```python
current_version_id = version_manager.get_current_version_id()
version_info = version_manager.get_version_info(current_version_id)

print(f"Current version: {current_version_id}")
print(f"Label: {version_info['label']}")
print(f"Description: {version_info['description']}")
print(f"Modified by: {version_info['created_by']}")
```

## Frontend Integration

### In Rules Catalogue Component

```javascript
// When user modifies rules
const handleSaveRuleChanges = async (modifiedRules, modifiedMappings, description) => {
  try {
    const response = await fetch('/api/rules/versions/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rules: modifiedRules,
        mappings: modifiedMappings,
        description: description,
        modifications: trackModifications(originalRules, modifiedRules),
        created_by: 'user'
      })
    });

    const result = await response.json();
    
    if (result.status === 'success') {
      setCurrentVersion(result.new_version_id);
      showSuccessMessage(`Rules saved as version ${result.new_version_id}`);
      
      // Reload compliance check with new rules
      reloadComplianceCheck();
    }
  } catch (error) {
    showErrorMessage(`Failed to save rules: ${error.message}`);
  }
};
```

### Display Version History

```javascript
const handleLoadVersionHistory = async () => {
  const response = await fetch('/api/rules/versions/list');
  const data = await response.json();
  
  // Display version timeline
  const versions = data.versions.map(v => ({
    id: v.version_id,
    label: `v${v.version_id}: ${v.label}`,
    description: v.description,
    created: new Date(v.created_at),
    by: v.created_by
  }));
  
  setVersionHistory(versions);
};
```

### Rollback UI Action

```javascript
const handleRollback = async (versionId) => {
  if (window.confirm(`Rollback to version ${versionId}? This will discard current changes.`)) {
    const response = await fetch(`/api/rules/versions/rollback/${versionId}`, {
      method: 'POST'
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      setCurrentVersion(versionId);
      reloadRules();
      showSuccessMessage(`Rolled back to version ${versionId}`);
    }
  }
};
```

## Version Manifest Structure

**File:** `rules_config/versions/version_manifest.json`

```json
{
  "current_version": 1,
  "total_versions": 2,
  "versions": [
    {
      "version_id": 0,
      "label": "Original",
      "created_at": "2025-12-09T00:00:00Z",
      "created_by": "system",
      "description": "Original rules configuration with 14 rules",
      "num_rules": 14,
      "rule_ids": ["ADA_DOOR_MIN_CLEAR_WIDTH", "IBC_FIRE_EXIT_DOOR_HEIGHT", ...],
      "modifications": []
    },
    {
      "version_id": 1,
      "label": "User Modifications #1",
      "created_at": "2025-12-09T14:30:00Z",
      "created_by": "user",
      "description": "Updated ADA door clearance from 762mm to 815mm",
      "num_rules": 14,
      "rule_ids": ["ADA_DOOR_MIN_CLEAR_WIDTH", "IBC_FIRE_EXIT_DOOR_HEIGHT", ...],
      "modifications": [
        {
          "type": "rule_update",
          "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
          "field": "parameters.min_clear_width_mm",
          "old_value": 762,
          "new_value": 815
        }
      ]
    }
  ],
  "version_history": [
    {
      "timestamp": "2025-12-09T14:30:00Z",
      "action": "create_version",
      "version_id": 1,
      "description": "Updated ADA door clearance",
      "created_by": "user"
    }
  ]
}
```

## Workflow Examples

### Example 1: User Updates a Rule Parameter

1. **User in UI**: Opens Rules Catalogue → Modifies ADA_DOOR_MIN_CLEAR_WIDTH from 762 to 815 mm
2. **User clicks**: "Save Changes"
3. **Frontend**: Sends POST /api/rules/versions/save with:
   - Modified rules object
   - Modifications list with change details
4. **Backend**: 
   - Validates new rules
   - Creates versions/v1/ directory
   - Copies modified files to v1/
   - Updates version_manifest.json (current_version = 1)
5. **Result**: Version 1 created, all downstream systems use v1 rules

### Example 2: Rollback to Original

1. **User in UI**: Views Version History → Clicks "Rollback to v0"
2. **Frontend**: Confirms with user, sends POST /api/rules/versions/rollback/0
3. **Backend**:
   - Updates version_manifest.json (current_version = 0)
   - Records rollback in version_history
4. **Result**: System uses original rules (v0), changes discarded

### Example 3: Compare Two Versions

1. **User in UI**: Clicks "Compare v0 vs v1"
2. **Frontend**: Sends GET /api/rules/versions/compare/0/1
3. **Backend**: Analyzes differences
4. **Result**: Shows which rules were added/removed/modified between versions

## Key Principles

### ✅ Original Files Protected

- Parent directory files (`rules_config/enhanced-regulation-rules.json`, etc.) loaded on first run
- Never modified after initialization
- Original always available as v0

### ✅ Version Isolation

- Each version completely self-contained in its directory
- No cross-version dependencies
- Can safely delete old versions without affecting others

### ✅ Compliance Consistency

- Compliance check uses `current_version` from manifest
- All modifications to rules → create new version → compliance uses new version
- No confusion about which rules are active

### ✅ Audit Trail

- version_manifest.json tracks all modifications
- Each change recorded with timestamp, description, and user
- Can trace why/when/who changed each rule

### ✅ Easy Rollback

- Any version can be restored instantly
- No data reconstruction needed
- Complete history always available

## Common Tasks

### Task: Add New Rule

```python
# Load current rules
rules, mappings = version_manager.load_rules()

# Add new rule
new_rule = {
    "id": "NEW_RULE_ID",
    "name": "New Rule Name",
    ...
}
rules["rules"].append(new_rule)

# Create version
version_id = version_manager.create_new_version(
    rules_dict=rules,
    mappings_dict=mappings,
    description="Added new rule: NEW_RULE_ID",
    modifications=[{"type": "rule_add", "rule_id": "NEW_RULE_ID"}],
    created_by="user"
)
```

### Task: Update Rule Parameter

```python
# Load current rules
rules, mappings = version_manager.load_rules()

# Find and update rule
for rule in rules["rules"]:
    if rule["id"] == "ADA_DOOR_MIN_CLEAR_WIDTH":
        old_value = rule["parameters"]["min_clear_width_mm"]
        rule["parameters"]["min_clear_width_mm"] = 815
        
        # Create version
        version_id = version_manager.create_new_version(
            rules_dict=rules,
            mappings_dict=mappings,
            description=f"Updated ADA_DOOR_MIN_CLEAR_WIDTH width: {old_value} → 815",
            modifications=[{
                "type": "rule_update",
                "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
                "field": "parameters.min_clear_width_mm",
                "old_value": old_value,
                "new_value": 815
            }],
            created_by="user"
        )
        break
```

### Task: Export Version for Backup

```python
# Export to external location
version_manager.export_version(
    version_id=1,
    output_dir="/backups/"
)

# Backup created at: /backups/rules_v1/
```

## Files and Locations

| File | Purpose | Modified? |
|------|---------|-----------|
| `rules_config/enhanced-regulation-rules.json` | Original rules (loaded on start) | Never |
| `rules_config/unified_rules_mapping.json` | Original mappings (loaded on start) | Never |
| `rules_config/versions/v0/...` | Baseline copy (read-only backup) | Never |
| `rules_config/versions/vN/...` | User modification copies | No |
| `rules_config/versions/version_manifest.json` | Version metadata & history | Yes (append-only) |
| `backend/rules_version_manager.py` | Python version manager | Code only |
| `backend/rules_versioning_api.py` | Flask API endpoints | Code only |

## Best Practices

✅ **Always create new versions** - Never modify files in place  
✅ **Document changes** - Provide clear descriptions of what changed  
✅ **Use meaningful names** - Include what/why in descriptions  
✅ **Export for backup** - Export important versions to safe location  
✅ **Regular snapshots** - Create versions after significant changes  
✅ **Review differences** - Use compare endpoint before committing to version  

## Troubleshooting

### Issue: Version not found

```
GET /api/rules/versions/5
Status: 404
Message: "Version 5 not found"
```

**Solution**: Check available versions with `GET /api/rules/versions/list`

### Issue: Rollback failed

```
POST /api/rules/versions/rollback/10
Status: 400
Message: "Version 10 does not exist"
```

**Solution**: Verify version exists before rollback

### Issue: Save version failed

```
POST /api/rules/versions/save
Status: 400
Message: "Missing required fields: rules, mappings"
```

**Solution**: Ensure request body includes both `rules` and `mappings` objects

## Future Enhancements

- [ ] Diff viewer UI showing exact changes between versions
- [ ] Version tagging (e.g., "stable", "testing", "production")
- [ ] Branching (multiple development lines)
- [ ] Merge functionality for combining versions
- [ ] Scheduled version snapshots
- [ ] Version comparison with rule impact analysis
