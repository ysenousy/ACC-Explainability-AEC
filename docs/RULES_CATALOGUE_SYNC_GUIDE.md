# Rules Catalogue & Mapping Auto-Sync System

## Overview

The **Auto-Sync System** ensures that rule mappings are **always in sync with the catalogue**:

✅ When you **add a rule** to catalogue → system tracks it  
✅ When you **remove a rule** from catalogue → orphaned mapping removed automatically  
✅ When you **modify a rule** in catalogue → mapping stays valid  
✅ **Frontend and backend stay consistent** at all times  

## Problem It Solves

**Before (without sync):**
- User removes rule from catalogue (13 rules)
- But unified_rules_mapping.json still has 15 mappings
- Compliance check evaluates rules that don't exist
- Data becomes inconsistent

**After (with sync):**
- User removes rule from catalogue (13 rules)
- Auto-sync removes corresponding mapping
- unified_rules_mapping.json has exactly 13 mappings
- Everything stays in sync automatically

## How It Works

```
User edits catalogue in Frontend
        ↓
Frontend calls POST /api/rules/sync/on-catalogue-update
        ↓
Backend loads current catalogue
        ↓
Identifies which rules are in catalogue
        ↓
Removes mappings for rules not in catalogue
        ↓
Updates unified_rules_mapping.json
        ↓
Compliance check always uses synced mappings
```

## API Endpoints

### 1. Get Sync Status (No Changes)

```bash
GET /api/rules/sync/status
```

Returns current sync state without making changes.

**Response:**
```json
{
  "status": "success",
  "sync_status": {
    "status": "in_sync",
    "catalogue_rules": 13,
    "mapped_rules": 13,
    "orphaned": 0,
    "missing": 0,
    "details": {
      "catalogue_rules": ["ADA_DOOR_MIN_CLEAR_WIDTH", ...],
      "mapped_rules": ["ADA_DOOR_MIN_CLEAR_WIDTH", ...],
      "orphaned": [],
      "missing": []
    }
  }
}
```

### 2. Synchronize Now

```bash
POST /api/rules/sync/synchronize
```

Immediately sync mappings with catalogue.

**Response:**
```json
{
  "status": "success",
  "message": "Mappings synchronized with catalogue",
  "result": {
    "status": "synced",
    "catalogue_rules": 13,
    "mapped_rules": 13,
    "valid_mappings": 13,
    "orphaned_removed": 2,
    "missing_mappings": 0,
    "sync_details": {
      "catalogue_rules": [...],
      "mapped_rules": [...],
      "orphaned_removed": ["OCCUPANCY_MAX_PER_STOREY", "DOOR_MAINTENANCE_WARNING"],
      "missing_mappings": []
    }
  }
}
```

### 3. On Catalogue Update (Auto-Sync)

```bash
POST /api/rules/sync/on-catalogue-update

{
  "action": "remove",           # add, remove, modify, batch
  "rule_id": "RULE_ID_HERE"    # which rule changed
}
```

Called automatically when user modifies catalogue. Syncs mappings.

**Response:**
```json
{
  "status": "success",
  "message": "Catalogue updated (remove rule: RULE_NAME). Mappings synchronized.",
  "sync_result": { ... }
}
```

### 4. Validate Sync

```bash
GET /api/rules/sync/validate
```

Check if mappings are valid (without changing anything).

**Response:**
```json
{
  "status": "success",
  "is_valid": true,
  "validation": {
    "status": "in_sync",
    "catalogue_rules": 13,
    "mapped_rules": 13,
    ...
  }
}
```

### 5. Detailed Status

```bash
GET /api/rules/sync/detailed-status
```

Full sync status with complete rule lists.

**Response:**
```json
{
  "status": "success",
  "sync_status": {
    "status": "in_sync",
    "catalogue_rules": 13,
    "mapped_rules": 13,
    "orphaned": 0,
    "missing": 0,
    "details": {
      "catalogue_rules": [
        "ADA_DOOR_MIN_CLEAR_WIDTH",
        "IBC_FIRE_EXIT_DOOR_HEIGHT",
        ...
      ],
      "mapped_rules": [...],
      "orphaned": [],
      "missing": []
    }
  }
}
```

## Frontend Integration

### When User Adds a Rule

```javascript
const handleAddRule = async (newRule) => {
  // Add to catalogue
  const updatedCatalogue = [...rules, newRule];
  
  // Save catalogue
  await saveRulesToCatalogue(updatedCatalogue);
  
  // Trigger sync
  const syncResponse = await fetch('/api/rules/sync/on-catalogue-update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'add',
      rule_id: newRule.id
    })
  });
  
  if (syncResponse.ok) {
    showMessage('Rule added and mappings updated');
    reloadComplianceCheck();
  }
};
```

### When User Removes a Rule

```javascript
const handleRemoveRule = async (ruleId) => {
  if (window.confirm('Remove this rule? Mapping will be deleted.')) {
    // Remove from catalogue
    const updatedCatalogue = rules.filter(r => r.id !== ruleId);
    
    // Save catalogue
    await saveRulesToCatalogue(updatedCatalogue);
    
    // Trigger sync
    const syncResponse = await fetch('/api/rules/sync/on-catalogue-update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'remove',
        rule_id: ruleId
      })
    });
    
    if (syncResponse.ok) {
      showMessage(`Rule removed and mapping cleaned up`);
      reloadComplianceCheck();
    }
  }
};
```

### Check Sync Status

```javascript
const checkSyncStatus = async () => {
  const response = await fetch('/api/rules/sync/status');
  const data = await response.json();
  
  if (data.sync_status.status === 'in_sync') {
    console.log(`✓ All ${data.sync_status.catalogue_rules} rules are mapped`);
  } else {
    console.warn('⚠ Sync issues detected:');
    console.warn(`  Orphaned: ${data.sync_status.orphaned}`);
    console.warn(`  Missing: ${data.sync_status.missing}`);
  }
};
```

## Python Usage

### Check Sync Status

```python
from backend.rules_mapping_sync import RulesMappingSynchronizer

sync = RulesMappingSynchronizer("rules_config")
status = sync.get_sync_status()

print(f"Status: {status['status']}")
print(f"Catalogue rules: {status['catalogue_rules']}")
print(f"Mapped rules: {status['mapped_rules']}")
print(f"Orphaned: {status['orphaned']}")
print(f"Missing: {status['missing']}")
```

### Perform Sync

```python
result = sync.sync_mappings(verbose=True)

print(f"Orphaned removed: {result['orphaned_removed']}")
print(f"Removed: {result['sync_details']['orphaned_removed']}")
```

### Validate Sync

```python
is_valid = sync.validate_sync()

if is_valid:
    print("✓ All mappings are valid")
else:
    print("✗ Sync issues detected")
```

## Data Flow

### Scenario: Remove Rule from Catalogue

```
Step 1: User clicks "Delete Rule" in UI
   ↓
Step 2: Frontend saves updated catalogue
   └─ POST to save catalogue endpoint
   ↓
Step 3: Frontend triggers sync
   └─ POST /api/rules/sync/on-catalogue-update
        {
          "action": "remove",
          "rule_id": "RULE_TO_REMOVE"
        }
   ↓
Step 4: Backend synchronizer
   ├─ Loads current catalogue
   ├─ Loads current mappings
   ├─ Identifies orphaned mappings
   ├─ Removes orphaned mappings
   └─ Saves updated unified_rules_mapping.json
   ↓
Step 5: Frontend receives success
   ├─ Shows confirmation message
   ├─ Reloads compliance check
   └─ Displays updated mapping count
   ↓
Step 6: Compliance Check
   ├─ Uses synced mappings
   ├─ Evaluates only rules in catalogue
   └─ Report shows correct count
```

### Scenario: Batch Update (Multiple Rules)

```
User adds 3 rules, removes 2 rules
        ↓
Frontend sends single sync request:
{
  "action": "batch",
  "rule_ids": ["ADD_1", "ADD_2", "ADD_3", "REM_1", "REM_2"]
}
        ↓
Backend sync:
  • Compares full catalogues
  • Removes all orphaned mappings
  • Adds any missing mappings (if templates available)
  • Generates report of all changes
        ↓
Frontend reloads everything
```

## Key Features

### ✅ Real-Time Consistency

- Rule deletions are immediately reflected in mappings
- No stale mappings in the system
- Compliance check always uses current rules

### ✅ Automatic Cleanup

- Orphaned mappings removed automatically
- No manual intervention needed
- Transparent to user (runs in background)

### ✅ Safe Operations

- Original files preserved (v0 in versions/)
- All changes tracked in version_manifest.json
- Can rollback to previous versions if needed

### ✅ Detailed Reporting

- Know exactly what was synced
- See which mappings were removed
- Identify missing mappings

### ✅ Multiple Ways to Trigger

- Manual: `GET /api/rules/sync/status`
- On demand: `POST /api/rules/sync/synchronize`
- Automatic: `POST /api/rules/sync/on-catalogue-update` (called by frontend)

## Common Scenarios

### Scenario 1: User Removes 1 Rule

**Before Sync:**
- Catalogue: 13 rules
- Mappings: 14 (includes 1 orphaned)
- Issue: Compliance check evaluates rule that's not in catalogue

**After Sync:**
- Catalogue: 13 rules
- Mappings: 13 (orphaned removed)
- Status: ✓ In sync

### Scenario 2: User Modifies Rule Parameter

**What Happens:**
1. Rule definition in catalogue updated
2. Mapping remains valid (rule still exists)
3. Compliance check uses updated parameter

**Sync Status:** Already in sync (rule not added/removed)

### Scenario 3: Bulk Import of Rules

**What Happens:**
1. User imports 5 new rules
2. Frontend calls sync with `action: "batch"`
3. Mappings created for all 5 rules
4. Compliance check now includes all 5

## Maintenance

### Check System Health

```bash
# Check status
curl http://localhost:5000/api/rules/sync/status

# Validate
curl http://localhost:5000/api/rules/sync/validate
```

### Force Resync

```bash
curl -X POST http://localhost:5000/api/rules/sync/synchronize
```

### Monitor Logs

```
[INFO] Mappings sync completed:
       Catalogue rules: 13
       Mapped rules: 13
       Orphaned removed: 0
       Missing mappings: 0
```

## Integration Checklist

- [ ] Update frontend Rules Catalogue to call `on-catalogue-update` on any change
- [ ] Add sync status indicator in Rules UI
- [ ] Show warning if `sync_status.status !== "in_sync"`
- [ ] Add "Sync Now" button for manual sync
- [ ] Display orphaned/missing rules if found
- [ ] Test add/remove/modify rule workflows
- [ ] Verify compliance check uses synced mappings

## Troubleshooting

### Q: Mappings still show 15 when catalogue shows 13?

**A:** Run manual sync:
```bash
POST /api/rules/sync/synchronize
```

This will remove any orphaned mappings.

### Q: New rule added but not mapped?

**A:** Check for missing mappings:
```bash
GET /api/rules/sync/status
```

If a rule is missing from mappings, manually add mapping or create template.

### Q: How do I revert to original mappings?

**A:** Rollback using version manager:
```bash
POST /api/rules/versions/rollback/0
```

This reverts to original v0 (before any user modifications).

## Performance Notes

- Sync operation is fast (~100ms for 14 rules)
- Can be run on every catalogue change
- Minimal impact on system performance
- No database queries needed (file-based)
