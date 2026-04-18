import requests
import time

BASE_URL = "http://localhost:8000"
TOKEN = "test-token-end_user"

def test_mfa_gate():
    print("\n--- Testing Step 1: MFA Gate ---")
    # First, ensure 2FA is OFF for the test user
    # (Assuming we have a way to toggle it or use a user who has it off)
    # Using the bypass token which might auto-create the user with default 2FA=Off
    
    payload = {
        "user_id": 1,
        "recipient_name": "Compliance Test",
        "merchant": "Global Store",
        "amount": 1500.0,
        "device_id": "TEST-DEVICE",
        "ip_address": "127.0.0.1",
        "location": "Mumbai, India"
    }
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(f"{BASE_URL}/transactions/", json=payload, headers=headers)
    data = response.json()
    
    print(f"Status: {data.get('status')}")
    print(f"Explanation: {data.get('explanation')}")
    
    assert data.get('status') == "BLOCKED"
    assert "MFA REQUIRED" in data.get('explanation')
    print("✅ MFA Gate Test Passed")

def test_ml_weighted_fusion():
    print("\n--- Testing Step 4: Weighted Fusion & Thresholds ---")
    # Test a small transaction (under 1000) to see ML scoring and thresholds
    payload = {
        "user_id": 1,
        "recipient_name": "Compliance Test",
        "merchant": "Safe Shop",
        "amount": 200.0,
        "device_id": "TEST-DEVICE",
        "ip_address": "127.0.0.1",
        "location": "Mumbai, India"
    }
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(f"{BASE_URL}/transactions/", json=payload, headers=headers)
    data = response.json()
    
    risk = data.get('final_risk_score')
    status = data.get('status')
    intelligence = data.get('intelligence', {})
    breakdown = intelligence.get('breakdown', {})
    
    print(f"Final Risk: {risk}")
    print(f"Status: {status}")
    print("Breakdown Keys:", list(breakdown.keys()))
    
    # Check breakdown keys for new weights
    required_keys = ["Anomaly Engine (35%)", "Graph Neural (30%)", "Merchant Risk (20%)", "User Behavior (15%)"]
    for key in required_keys:
        assert key in breakdown, f"Missing key: {key}"
    
    # Check threshold logic
    if risk < 0.35:
        assert status == "APPROVED"
    elif risk < 0.65:
        assert status == "FLAGGED"
    else:
        assert status == "BLOCKED"
        
    print("✅ ML Weighted Fusion & Thresholds Test Passed")

if __name__ == "__main__":
    try:
        test_mfa_gate()
        test_ml_weighted_fusion()
        print("\n🏆 ALL COMPLIANCE TESTS PASSED")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
