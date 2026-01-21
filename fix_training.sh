#!/bin/bash
# Quick fix script for TRM training data
# Run this to clear old data and prepare for fresh training

echo "=================================="
echo "TRM TRAINING FIX - Step by Step"
echo "=================================="

# Step 1: Clear old incompatible data
echo ""
echo "STEP 1: Clearing old data (incompatible format)..."
echo "  Removing: data/trm_incremental_data.json"
rm -f data/trm_incremental_data.json
echo "  ✅ Done"

echo ""
echo "  Removing: checkpoints/trm/* (old model)"
rm -rf checkpoints/trm/*
echo "  ✅ Done"

# Step 2: Verify backend is running
echo ""
echo "STEP 2: Make sure backend is running"
echo "  Required: python backend/app.py (in another terminal)"
echo "  Check: Can you access http://localhost:5000 ?"
echo ""
echo "  If NOT running, do this in a NEW terminal:"
echo "    cd c:\\Research Work\\ACC-Explainability-AEC"
echo "    python backend/app.py"
echo ""
read -p "  Press ENTER when backend is running..."

# Step 3: Add compliance data
echo ""
echo "STEP 3: About to add compliance samples"
echo "  This will extract 320-dimensional features (not old 128-dim)"
echo "  Features include:"
echo "    - Element: width, height, type, accessibility, etc."
echo "    - Rule: severity, complexity, ADA, fire-rated, etc."
echo "    - Context: element-rule affinity, remediation difficulty"
echo ""
echo "  The script will use your last compliance check results"
echo ""
read -p "  Press ENTER to continue..."

# Step 4: Check if we can get compliance results
echo ""
echo "STEP 4: Retrieving last compliance results..."
python << 'EOF'
import requests
import json
from pathlib import Path

try:
    # Check if we have cached compliance results
    cache_file = Path('data/last_compliance_results.json')
    if cache_file.exists():
        with open(cache_file) as f:
            results = json.load(f)
        print(f"✅ Found cached compliance results: {len(results.get('results', []))} checks")
    else:
        print("⚠️  No cached compliance results found")
        print("    After adding data, compliance checks will be cached for next time")
except Exception as e:
    print(f"❌ Error: {e}")
EOF

echo ""
echo "=================================="
echo "NEXT STEPS (Run in PowerShell or terminal):"
echo "=================================="
echo ""
echo "1. RESTART BACKEND (if not already running):"
echo "   cd 'c:\\Research Work\\ACC-Explainability-AEC'"
echo "   python backend/app.py"
echo ""
echo "2. RUN COMPLIANCE CHECK (generates fresh data):"
echo "   curl -X POST http://localhost:5000/api/rules/check-compliance ^"
echo "     -H \"Content-Type: application/json\" ^"
echo "     -d '{\"graph\": {... your IFC graph ...}}'"
echo ""
echo "3. ADD SAMPLES TO TRAINING (with NEW 320-dim features):"
echo "   python add_fresh_data.py"
echo ""
echo "4. VERIFY DATA HAS SIGNAL:"
echo "   python diagnose_training.py"
echo ""
echo "5. TRAIN MODEL WITH FRESH DATA:"
echo "   curl -X POST http://localhost:5000/api/trm/train ^"
echo "     -H \"Content-Type: application/json\" ^"
echo "     -d '{\"epochs\": 20}'"
echo ""
echo "=================================="
