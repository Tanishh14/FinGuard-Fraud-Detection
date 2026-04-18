import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "test-token-admin" # Use admin token for analyst actions

def test_forensics_story():
    print("\n--- Testing Forensics Story (Enhanced) ---")
    # Fetch a transaction first
    headers = {"Authorization": f"Bearer {TOKEN}"}
    tx_res = requests.get(f"{BASE_URL}/transactions/all", headers=headers)
    if tx_res.status_code != 200:
        print(f"Failed to get transactions: {tx_res.status_code} - {tx_res.text}")
        return
    txs = tx_res.json()
    if not txs:
        print("No transactions found to test forensics.")
        return
    
    tx_id = txs[0]['id']
    f_res = requests.get(f"{BASE_URL}/forensics/story/{tx_id}", headers=headers)
    print(f"Forensics Story Response: {f_res.status_code}")
    if f_res.status_code != 200:
        print(f"Error: {f_res.text}")
        return
    data = f_res.json()
    
    print(f"Transaction ID: {data['transaction']['id']}")
    print(f"Risk History Count: {len(data['forensics']['risk_history'])}")
    print(f"Peer Comparison: {data['forensics']['peer_comparison']}")
    
    assert "risk_history" in data["forensics"]
    assert "peer_comparison" in data["forensics"]
    print("[PASS] Forensics Story Test")

def test_account_freeze():
    print("\n--- Testing Account Freeze Action ---")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    # Using user_id 1 for test
    res = requests.post(f"{BASE_URL}/forensics/accounts/freeze/9", headers=headers)
    data = res.json()
    print(f"Result: {data['message']}")
    assert data["status"] == "frozen"
    print("[PASS] Account Freeze Test")

if __name__ == "__main__":
    try:
        test_forensics_story()
        test_account_freeze()
        print("\nFORENSICS & ACTIONS TESTS PASSED")
    except Exception as e:
        print(f"\nTest Failed: {e}")
