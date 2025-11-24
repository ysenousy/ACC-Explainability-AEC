"""Quick test to check if all rules are returned"""
import requests
import json

try:
    response = requests.get('http://localhost:5000/api/reasoning/all-rules', timeout=5)
    if response.status_code == 200:
        data = response.json()
        total = data.get("total_rules", 0)
        rules = data.get("rules", [])
        print(f"Total Rules: {total}")
        print(f"\nRules ({len(rules)}):")
        for i, rule in enumerate(rules, 1):
            target = rule.get("target_ifc_class", "?")
            print(f"{i}. {rule.get('name')} ({target})")
    else:
        print(f"Error: {response.status_code}")
        print("Make sure backend is running on port 5000")
except Exception as e:
    print(f"Error: {e}")
    print("Make sure backend is running: python backend/app.py")
