"""
Test the session state fix for multiple rule deletions
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_multiple_deletes():
    print("\n" + "="*60)
    print("TESTING: Multiple Rule Deletions with Session State")
    print("="*60)
    
    # Test 1: Get initial rules
    print("\n[TEST 1] Get initial rules")
    response = requests.get(f"{BASE_URL}/api/rules/custom")
    data = response.json()
    initial_rules = data['custom_rules']
    print(f"Initial count: {len(initial_rules)} rules")
    print(f"Is editing: {data.get('is_editing')}")
    if initial_rules:
        print(f"First rule ID: {initial_rules[0]['id']}")
    
    # Test 2: Delete first rule
    print("\n[TEST 2] Delete first rule")
    first_rule_id = initial_rules[0]['id']
    response = requests.delete(f"{BASE_URL}/api/rules/delete/{first_rule_id}")
    data = response.json()
    after_first_delete = data['rules']
    print(f"After delete: {len(after_first_delete)} rules (should be {len(initial_rules)-1})")
    print(f"Delete message: {data.get('message')}")
    
    # Test 3: Check session state
    print("\n[TEST 3] Check session state after delete")
    response = requests.get(f"{BASE_URL}/api/rules/custom")
    data = response.json()
    current_rules = data['custom_rules']
    print(f"Current count: {len(current_rules)} rules")
    print(f"Is editing: {data.get('is_editing')}")
    
    if len(current_rules) != len(after_first_delete):
        print(f"❌ ERROR: Session state not maintained! Expected {len(after_first_delete)}, got {len(current_rules)}")
        return False
    
    # Test 4: Delete second rule
    print("\n[TEST 4] Delete second rule")
    second_rule_id = current_rules[0]['id']
    response = requests.delete(f"{BASE_URL}/api/rules/delete/{second_rule_id}")
    data = response.json()
    after_second_delete = data['rules']
    print(f"After delete: {len(after_second_delete)} rules (should be {len(current_rules)-1})")
    
    # Test 5: Verify second delete worked
    print("\n[TEST 5] Verify second delete maintained")
    response = requests.get(f"{BASE_URL}/api/rules/custom")
    data = response.json()
    final_rules = data['custom_rules']
    print(f"Final count: {len(final_rules)} rules")
    print(f"Is editing: {data.get('is_editing')}")
    
    expected_count = len(initial_rules) - 2
    if len(final_rules) == expected_count:
        print(f"✅ SUCCESS: Multiple deletes working! {len(initial_rules)} → {len(final_rules)}")
        return True
    else:
        print(f"❌ ERROR: Expected {expected_count}, got {len(final_rules)}")
        return False

if __name__ == "__main__":
    try:
        success = test_multiple_deletes()
        print("\n" + "="*60)
        if success:
            print("TEST PASSED ✓")
        else:
            print("TEST FAILED ✗")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        print("Make sure Flask server is running: python start_server.py")
