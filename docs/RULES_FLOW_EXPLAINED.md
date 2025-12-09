# Rules Update Flow - Complete Architecture

## The Flow (Step by Step)

```
┌─────────────────────────────────────────────────────────────┐
│ USER EDITS REGULATORY RULES CATALOGUE IN FRONTEND           │
│ (Add, Remove, Modify rules)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND SENDS TO BACKEND                                    │
│ POST /api/rules/versions/save                               │
│ {                                                            │
│   "rules": {...modified rules...},                          │
│   "mappings": {...updated mappings...},                     │
│   "description": "What changed",                            │
│   "modifications": [...],                                   │
│   "created_by": "user"                                      │
│ }                                                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ BACKEND - VERSION MANAGER                                    │
│ 1. Validates modifications                                  │
│ 2. Creates new version directory (vN/)                      │
│ 3. Copies modified rules to vN/                             │
│ 4. Updates version_manifest.json                            │
│    - Sets current_version = vN                              │
│    - Records who/when/why changed                           │
│    - Stores modification details                            │
│ 5. Returns success with new version ID                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ BACKEND - SYNC MANAGER (AUTOMATIC)                          │
│ 1. Detects catalogue has changed                            │
│ 2. Compares with current mappings                           │
│ 3. Removes orphaned mappings                                │
│ 4. Updates unified_rules_mapping.json                       │
│ 5. Ensures mappings match catalogue                         │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ RESULTS                                                      │
│                                                              │
│ ✓ Original files (v0) untouched                            │
│ ✓ New version (vN) created and saved                       │
│ ✓ Version history tracked                                   │
│ ✓ Mappings automatically synced                            │
│ ✓ Can rollback anytime                                      │
│ ✓ Compliance check uses latest version                      │
│ ✓ Training uses latest version                              │
└──────────────────────────────────────────────────────────────┘
```

## Directory Structure After User Update

```
rules_config/
├── enhanced-regulation-rules.json        ← Original (v0) - never changes
├── unified_rules_mapping.json            ← Original (v0) - never changes
│
└── versions/
    ├── v0/
    │   ├── enhanced-regulation-rules.json (original)
    │   └── unified_rules_mapping.json     (original)
    │
    ├── v1/
    │   ├── enhanced-regulation-rules.json (user modified)
    │   └── unified_rules_mapping.json     (synced to match v1)
    │
    ├── v2/
    │   ├── enhanced-regulation-rules.json (user modified again)
    │   └── unified_rules_mapping.json     (synced to match v2)
    │
    └── version_manifest.json
        {
          "current_version": 2,
          "versions": [
            {
              "version_id": 0,
              "label": "Original",
              "created_by": "system",
              "rules": 14,
              "modifications": []
            },
            {
              "version_id": 1,
              "label": "User Modifications #1",
              "created_by": "user",
              "description": "Removed rule: RULE_XYZ",
              "rules": 13,
              "modifications": [...]
            },
            {
              "version_id": 2,
              "label": "User Modifications #2",
              "created_by": "user",
              "description": "Added rule: RULE_ABC",
              "rules": 14,
              "modifications": [...]
            }
          ]
        }
```

## What Gets Saved in Versions

When user updates catalogue:

### ✅ In versions/vN/ directory:
- **enhanced-regulation-rules.json** - The modified catalogue (14 rules, 13 rules, etc.)
- **unified_rules_mapping.json** - Auto-synced mappings that match the catalogue

### ✅ In version_manifest.json:
- version_id
- timestamp (when changed)
- created_by (who changed it - "user")
- description (what changed)
- num_rules (how many rules in this version)
- modifications (details of each change)
- version_history (audit trail)

### ❌ Original files (parent directory):
- enhanced-regulation-rules.json - **NEVER CHANGES**
- unified_rules_mapping.json - **NEVER CHANGES**

## Key Points

### 1. Original v0 is Safe
```
Original files loaded at app startup
         ↓
Copied to versions/v0/
         ↓
NEVER MODIFIED AFTER
         ↓
Always available as fallback
```

### 2. User Edits = New Version
```
User modifies catalogue
         ↓
Creates versions/vN/ with modified files
         ↓
Updates version_manifest.json
         ↓
Sets current_version = vN
         ↓
All systems use vN (compliance, training, reporting)
```

### 3. Mappings Auto-Sync
```
User adds/removes rules
         ↓
Catalogue updated in vN
         ↓
Sync manager detects change
         ↓
Removes orphaned mappings
         ↓
Adds missing mappings (if templates available)
         ↓
Updates vN/unified_rules_mapping.json
         ↓
Mappings always match catalogue
```

### 4. Rollback Anytime
```
User says "revert to version 1"
         ↓
Rollback endpoint loads v1 files
         ↓
Updates current_version = 1
         ↓
All systems use v1 again
         ↓
Can switch between versions anytime
```

## Example Scenario

### Starting State (v0 - Original)
```
Catalogue: 14 rules
Mappings: 14 rules mapped
Status: ✓ In sync
```

### User removes 1 rule (creates v1)
```
Frontend action: Delete rule "OCCUPANCY_MAX_PER_STOREY"
         ↓
Backend saves to versions/v1/:
  - enhanced-regulation-rules.json (13 rules)
  - unified_rules_mapping.json (13 mapped)
         ↓
version_manifest.json updated:
  "current_version": 1
  "version_id": 1
  "description": "Removed rule: OCCUPANCY_MAX_PER_STOREY"
  "modifications": [
    {
      "type": "rule_remove",
      "rule_id": "OCCUPANCY_MAX_PER_STOREY"
    }
  ]
         ↓
Compliance check now uses v1 (13 rules)
Training data uses v1 (13 rules)
```

### User adds 2 rules (creates v2)
```
Frontend action: Add rules "NEW_RULE_1", "NEW_RULE_2"
         ↓
Backend saves to versions/v2/:
  - enhanced-regulation-rules.json (15 rules)
  - unified_rules_mapping.json (15 mapped)
         ↓
version_manifest.json updated:
  "current_version": 2
  "version_id": 2
  "description": "Added 2 new rules"
  "modifications": [
    {
      "type": "rule_add",
      "rule_id": "NEW_RULE_1"
    },
    {
      "type": "rule_add",
      "rule_id": "NEW_RULE_2"
    }
  ]
         ↓
Compliance check now uses v2 (15 rules)
Training data uses v2 (15 rules)
```

### User clicks "Rollback to v0"
```
Frontend action: Rollback to version 0
         ↓
Backend rollback endpoint:
  - Updates version_manifest.json
  - Sets current_version = 0
  - Clears any temp caches
         ↓
Compliance check reverts to v0 (14 original rules)
Training reverts to v0 (14 original rules)
         ↓
Can modify again to create new version (v3)
```

## API Endpoints Summary

### Saving User Changes
```
POST /api/rules/versions/save
{
  "rules": {...},
  "mappings": {...},
  "description": "What I changed",
  "modifications": [...]
}
→ Creates new version
```

### Checking Current Version
```
GET /api/rules/versions/current
→ Returns which version is active
```

### Listing All Versions
```
GET /api/rules/versions/list
→ Shows all versions with history
```

### Rolling Back
```
POST /api/rules/versions/rollback/1
→ Switches to version 1
```

### Syncing Mappings
```
POST /api/rules/sync/on-catalogue-update
→ Auto-syncs mappings after catalogue change
```

## Summary

**The regulatory rules catalogue is the user's editable document:**
- User modifies it in UI
- Changes saved to new version in `versions/vN/`
- Version history preserved in `version_manifest.json`
- Mappings auto-sync to match catalogue
- Original v0 always available unchanged
- Can rollback to any previous version
- All systems (compliance, training, reporting) use current version

Does this flow clarify how the versioning works with your catalogue?
