# Auto-Sync Integration - Complete Solution

## The Problem You Found

When you **deleted a rule in the Rules Catalogue UI** (making it 13 rules), the **mappings still showed 14** because:

1. ✗ Rule deleted from catalogue in frontend
2. ✗ Backend deleted rule from custom_rules
3. ✗ **Missing: No sync call was made**
4. ✗ Mappings never updated to match new catalogue
5. Result: Mismatch (13 rules vs 14 mappings)

## The Solution Implemented

Now, whenever a user **modifies the catalogue**, the sync is **automatically triggered**:

```
User deletes rule
        ↓
Frontend calls DELETE /api/rules/delete/{rule_id}
        ↓
Backend deletes rule
        ↓
Frontend automatically calls POST /api/rules/sync/on-catalogue-update
        ↓
Backend removes orphaned mapping
        ↓
Mappings now match catalogue (13 = 13)
```

## Changes Made

### Frontend: RuleCatalogueModal.js

**1. Delete rule** (Line 233-263)
```javascript
deleteRule = async (ruleId) => {
  // Delete rule from catalogue
  await fetch(`/api/rules/delete/${ruleId}`, { method: 'DELETE' })
  
  // NEW: Sync mappings immediately
  await fetch('/api/rules/sync/on-catalogue-update', {
    method: 'POST',
    body: JSON.stringify({ action: 'remove', rule_id: ruleId })
  })
}
```

**2. Import catalogue** (Line 71-85)
```javascript
handleImportCatalogue = async (file) => {
  // Import rules from file
  await fetch('/api/rules/import-catalogue', { method: 'POST' })
  
  // NEW: Sync mappings immediately
  await fetch('/api/rules/sync/on-catalogue-update', {
    method: 'POST',
    body: JSON.stringify({ action: 'batch' })
  })
}
```

**3. Append to catalogue** (Line 135-150)
```javascript
handleAppendCatalogue = async (file) => {
  // Append rules to catalogue
  await fetch('/api/rules/import-catalogue', { method: 'POST' })
  
  // NEW: Sync mappings immediately
  await fetch('/api/rules/sync/on-catalogue-update', {
    method: 'POST',
    body: JSON.stringify({ action: 'batch' })
  })
}
```

**4. Update rule** (Line 228-242)
```javascript
saveEditedRule = async () => {
  // Update rule parameters
  await fetch('/api/rules/update', { method: 'PUT' })
  
  // NEW: Sync mappings immediately
  await fetch('/api/rules/sync/on-catalogue-update', {
    method: 'POST',
    body: JSON.stringify({ action: 'modify', rule_id: id })
  })
}
```

## How It Works Now

### User deletes rule "OCCUPANCY_MAX_PER_STOREY"

**Before fix:**
```
Rules Catalogue: 13 rules ✓
Unified Mappings: 14 rules ✗
Status: OUT OF SYNC
```

**After fix:**
```
User clicks delete
    ↓
DELETE /api/rules/delete/OCCUPANCY_MAX_PER_STOREY
    ↓
POST /api/rules/sync/on-catalogue-update
    ↓
Backend removes orphaned mapping
    ↓
Rules Catalogue: 13 rules ✓
Unified Mappings: 13 rules ✓
Status: IN SYNC
```

## API Flow Diagram

```
┌──────────────────────┐
│ User Action          │
│ (Delete/Add/Modify)  │
└──────────┬───────────┘
           ↓
┌──────────────────────────────────────────┐
│ Frontend                                 │
│ Calls: DELETE /api/rules/delete/{id}    │
│        or PUT /api/rules/update          │
│        or POST /api/rules/import         │
└──────────┬───────────────────────────────┘
           ↓ (on success)
┌──────────────────────────────────────────┐
│ Frontend Auto-Calls                     │
│ POST /api/rules/sync/on-catalogue-update │
│ {                                        │
│   "action": "remove|add|modify|batch",  │
│   "rule_id": "RULE_ID"                  │
│ }                                        │
└──────────┬───────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ Backend Rules Sync                       │
│ 1. Load current catalogue rules          │
│ 2. Load current mappings                 │
│ 3. Find orphaned mappings                │
│ 4. Remove orphaned mappings              │
│ 5. Save updated mappings                 │
│ 6. Return sync status                    │
└──────────┬───────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ Result                                   │
│ Catalogue and Mappings now in sync       │
│ No stale data, no mismatch               │
└──────────────────────────────────────────┘
```

## Real-World Example

### Scenario: You delete 2 rules to make it 13

**Step 1: User interface**
```
Rules Catalogue Modal
├─ RULE_1 (Delete button clicked)
├─ RULE_2 (Delete button clicked)
└─ ...11 more rules
```

**Step 2: Frontend executes (automatically)**
```javascript
// Delete RULE_1
await fetch('/api/rules/delete/RULE_1', { method: 'DELETE' })
await fetch('/api/rules/sync/on-catalogue-update', {
  method: 'POST',
  body: JSON.stringify({ action: 'remove', rule_id: 'RULE_1' })
})

// Delete RULE_2
await fetch('/api/rules/delete/RULE_2', { method: 'DELETE' })
await fetch('/api/rules/sync/on-catalogue-update', {
  method: 'POST',
  body: JSON.stringify({ action: 'remove', rule_id: 'RULE_2' })
})
```

**Step 3: Backend syncs automatically**
```
For each delete:
  - Load rules/mappings from current version
  - Remove mapping for deleted rule
  - Save updated mappings
  - Return success

Result:
  - Catalogue: 13 rules
  - Mappings: 13 rules
  - Status: in_sync ✓
```

**Step 4: User sees**
```
"✓ Rule deleted and mappings synced"
```

## Files Modified

### Frontend
- `frontend/src/components/RuleCatalogueModal.js`
  - `deleteRule()` - Added sync on delete
  - `handleImportCatalogue()` - Added sync on import
  - `handleAppendCatalogue()` - Added sync on append
  - `saveEditedRule()` - Added sync on update

### Backend (Already existed)
- `backend/rules_sync_api.py` - Sync endpoints
- `backend/rules_mapping_sync.py` - Sync logic

## Testing

**Before fix:**
1. Delete rule → Catalogue shows 13
2. Check mappings → Shows 14 (WRONG!)

**After fix:**
1. Delete rule → Catalogue shows 13
2. Sync triggers automatically
3. Check mappings → Shows 13 (CORRECT!)
4. User sees confirmation: "Rule deleted and mappings synced"

## Key Benefits

✅ **Automatic** - No manual sync needed
✅ **Real-time** - Happens immediately after change
✅ **Non-blocking** - Sync errors don't break deletion
✅ **Transparent** - User sees confirmation message
✅ **Safe** - All data preserved, only orphaned mappings removed

## Error Handling

If sync fails (unlikely):
```javascript
try {
  await sync()
} catch (syncErr) {
  console.warn('Sync error (non-critical):', syncErr)
  // Still shows deletion succeeded
  // But warns user to check mappings
}
```

The deletion succeeds, but user is warned to manually verify mappings if sync fails.

## Next Steps (Optional)

You could add:
- [ ] "Sync Status" indicator in Rules UI
- [ ] Manual "Sync Now" button for safety
- [ ] Toast notification on sync completion
- [ ] Audit log of all sync operations
