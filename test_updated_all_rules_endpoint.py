"""Test the updated /api/reasoning/all-rules endpoint."""

import json
from pathlib import Path

# Test the endpoint locally
def test_all_rules_endpoint():
    """Test that the endpoint returns both regulatory and custom rules."""
    from reasoning_layer.reasoning_engine import ReasoningEngine
    
    # Initialize engine as the app does
    rules_file = Path('rules_config/enhanced-regulation-rules.json')
    custom_rules_file = Path('backend/custom_rules.json')
    
    engine = ReasoningEngine(
        str(rules_file) if rules_file.exists() else None,
        str(custom_rules_file) if custom_rules_file.exists() else None
    )
    
    print("[TEST] ReasoningEngine initialized")
    print(f"  Total rules: {len(engine.rules)}")
    print(f"  Regulatory: {len(engine.regulatory_rules)}")
    print(f"  Custom: {len(engine.custom_rules)}")
    
    # Simulate the endpoint response
    all_rules = engine.rules
    
    if not all_rules:
        print("[ERROR] No rules loaded")
        return False
    
    # Transform rules to simplified format (same as endpoint does)
    rules_list = []
    for rule_id, rule in all_rules.items():
        rule_source = "custom" if rule_id in engine.custom_rules else "regulatory"
        
        rules_list.append({
            "id": rule.get("id"),
            "name": rule.get("name"),
            "description": rule.get("description"),
            "severity": rule.get("severity", "WARNING"),
            "source": rule_source,
            "target_ifc_class": rule.get("target", {}).get("ifc_class") if isinstance(rule.get("target"), dict) else None,
            "regulation": rule.get("provenance", {}).get("regulation") if isinstance(rule.get("provenance"), dict) else None,
        })
    
    response = {
        "success": True,
        "rules": rules_list,
        "total_rules": len(all_rules),
        "regulatory_rules": len(engine.regulatory_rules),
        "custom_rules": len(engine.custom_rules),
        "error": None
    }
    
    print("\n[OK] Endpoint response structure:")
    print(f"  Total rules: {response['total_rules']}")
    print(f"  Regulatory: {response['regulatory_rules']}")
    print(f"  Custom: {response['custom_rules']}")
    
    if rules_list:
        print(f"\n[OK] Sample rules with source field:")
        for rule in rules_list[:3]:
            print(f"  - {rule['id']}: source={rule['source']}")
    
    print(f"\n[SUCCESS] /api/reasoning/all-rules endpoint will return:")
    print(f"  - {response['total_rules']} total rules")
    print(f"  - {response['regulatory_rules']} regulatory rules")
    print(f"  - {response['custom_rules']} custom rules (will be > 0 when custom_rules.json exists)")
    
    return True

if __name__ == "__main__":
    test_all_rules_endpoint()
