# Rules Versioning System

This directory contains versioned copies of rule configurations created when users modify the rule catalogue at runtime.

## Directory Structure

```
versions/
├── v0/                          # Original/baseline rules (never modified)
│   ├── enhanced-regulation-rules.json
│   └── unified_rules_mapping.json
├── v1/                          # First user modification
│   ├── enhanced-regulation-rules.json
│   └── unified_rules_mapping.json
├── v2/                          # Second user modification
│   ├── enhanced-regulation-rules.json
│   └── unified_rules_mapping.json
└── version_manifest.json        # Metadata about all versions
```

## Version Manifest Format

```json
{
  "current_version": 1,
  "versions": [
    {
      "version_id": 0,
      "label": "Original",
      "created_at": "2025-12-09T10:00:00Z",
      "created_by": "system",
      "description": "Original rules configuration",
      "modifications": []
    },
    {
      "version_id": 1,
      "label": "User Modifications #1",
      "created_at": "2025-12-09T14:30:00Z",
      "created_by": "user",
      "description": "Updated ADA_DOOR_MIN_CLEAR_WIDTH parameters",
      "modifications": [
        {
          "type": "rule_update",
          "rule_id": "ADA_DOOR_MIN_CLEAR_WIDTH",
          "field": "parameters.min_clear_width_mm",
          "old_value": 762,
          "new_value": 800
        }
      ]
    }
  ]
}
```

## Usage

### Loading Rules

```python
# Load specific version (returns merged rules from base + version)
version_manager.load_version(version_id=1)

# Load latest user modifications
version_manager.load_current()

# Load original rules
version_manager.load_version(version_id=0)
```

### Creating New Version

When user saves modifications:
1. Copy current files to `versions/vN/`
2. Apply user changes to copies
3. Update version_manifest.json
4. Increment current_version
5. Never touch original files in parent directory

### Rollback

```python
# Revert to version 0 (original)
version_manager.rollback_to(version_id=0)
```

## Key Principles

✅ **Original files (v0) are read-only** - Never modified after initialization
✅ **Each modification creates new version** - Full history preserved
✅ **Version manifest tracks all changes** - Audit trail of modifications
✅ **Compliance uses current version** - Always latest user modifications
✅ **Easy rollback** - Can revert to any previous version
✅ **No data loss** - All versions stored permanently
