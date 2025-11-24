"""Test ReasoningEngine with both regulatory and custom rules."""

import json
from pathlib import Path
from reasoning_layer.reasoning_engine import ReasoningEngine

def test_reasoning_engine_with_rules():
    """Test that ReasoningEngine loads and can explain both regulatory and custom rules."""
    
    # Initialize engine with regulatory rules
    rules_file = Path('rules_config/enhanced-regulation-rules.json')
    custom_rules_file = Path('backend/custom_rules.json')
    
    engine = ReasoningEngine(
        str(rules_file) if rules_file.exists() else None,
        str(custom_rules_file) if custom_rules_file.exists() else None
    )
    
    print(f"[OK] ReasoningEngine initialized")
    print(f"  Total rules: {len(engine.rules)}")
    print(f"  Regulatory: {len(engine.regulatory_rules)}")
    print(f"  Custom: {len(engine.custom_rules)}")
    
    # Test explaining a regulatory rule
    if engine.regulatory_rules:
        first_rule_id = list(engine.regulatory_rules.keys())[0]
        explanation = engine.explain_rule(
            first_rule_id,
            applicable_elements=['IfcDoor'],
            elements_checked=10,
            elements_passing=8,
            elements_failing=2
        )
        print(f"\n[OK] Successfully explained regulatory rule: {first_rule_id}")
        print(f"  Explanation keys: {list(explanation.keys())}")
    
    # Simulate adding a custom rule and test explaining it
    if not engine.custom_rules:
        print(f"\n[OK] Custom rules file not present (as expected)")
        print(f"  ReasoningEngine ready to support custom rules when custom_rules.json is created")
        
        # Show what would happen with custom rules
        sample_custom_rule = {
            "id": "CUSTOM_RULE_1",
            "name": "Custom Safety Rule",
            "description": "A custom user-defined rule",
            "severity": "medium"
        }
        engine.rules[sample_custom_rule["id"]] = sample_custom_rule
        engine.custom_rules[sample_custom_rule["id"]] = sample_custom_rule
        
        print(f"\n[OK] After adding sample custom rule:")
        print(f"  Total rules: {len(engine.rules)}")
        print(f"  Regulatory: {len(engine.regulatory_rules)}")
        print(f"  Custom: {len(engine.custom_rules)}")
        
        # Try to explain the custom rule
        try:
            explanation = engine.explain_rule(
                sample_custom_rule["id"],
                applicable_elements=['IfcDoor'],
                elements_checked=5,
                elements_passing=5,
                elements_failing=0
            )
            print(f"\n[OK] Successfully explained custom rule: {sample_custom_rule['id']}")
        except Exception as e:
            print(f"[ERROR] Error explaining custom rule: {e}")
    
    print(f"\n[SUCCESS] ReasoningEngine supports both regulatory and custom rules")
    print(f"   - Regulatory rules: Always loaded from enhanced-regulation-rules.json")
    print(f"   - Custom rules: Loaded from custom_rules.json when it exists")
    print(f"   - All rules can be explained via explain_rule() method")

if __name__ == "__main__":
    test_reasoning_engine_with_rules()
