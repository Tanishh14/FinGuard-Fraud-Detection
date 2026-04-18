import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_appeal_flow():
    # 1. Login as end_user (assuming user 1 exists)
    # We'll use a mock token if possible or assume a token is available
    # For this script, we'll try to find an existing user or create one
    
    # Let's assume we have a way to get a token
    # In a real test environment, we'd use test credentials
    print("--- Starting Appeal Flow Verification ---")
    
    unique_email = f"tester_{int(time.time())}@example.com"
    
    try:
        # 1. Register a new user
        print(f"0. Registering new user {unique_email}...")
        reg_payload = {
            "email": unique_email,
            "username": "AppealTester",
            "password": "password123",
            "role": "analyst", # Use analyst role so it can override later
            "is_2fa_enabled": False
        }
        requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
        
        # 2. Login
        login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": unique_email, "password": "password123"})
        if login_res.status_code != 200:
            print("Failed to login.")
            return
        
        token = login_res.json()["access_token"]
        user_id = login_res.json()["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Ingest a transaction that will be BLOCKED
        tx_payload = {
            "amount": 850000,
            "merchant": "MUMBAI_LUXURY_ESTATES",
            "merchant_id": "MLE-99",
            "recipient_name": "Investment Fund",
            "user_id": user_id,
            "location": "Mumbai, India",
            "device_id": "DEVICE-A1",
            "ip_address": "1.2.3.4",
            "timestamp": datetime.now().isoformat()
        }
        
        print("1. Ingesting high-risk transaction...")
        tx_res = requests.post(f"{BASE_URL}/transactions/", json=tx_payload, headers=headers)
        tx_data = tx_res.json()
        print(f"   Response Status: {tx_res.status_code}")
        print(f"   Transaction Status: {tx_data.get('status')}")
        
        tx_id = tx_data['id']
        
        # 4. Submit Appeal
        print(f"2. Submitting appeal for Tx #{tx_id}...")
        appeal_payload = {
            "reason": "This is a legitimate urgent payment for property booking. I am in Mumbai.",
            "urgency": "HIGH"
        }
        appeal_res = requests.post(f"{BASE_URL}/transactions/{tx_id}/appeal", json=appeal_payload, headers=headers)
        print(f"   Appeal Response Status: {appeal_res.status_code}")
        
        if appeal_res.status_code == 200:
            appeal_data = appeal_res.json()
            print(f"   New Status: {appeal_data['status']}")
            print(f"   Is Appealed: {appeal_data['is_appealed']}")
        else:
            print(f"   Appeal Failed: {appeal_res.text}")
            return

        # 5. Admin Approval
        print(f"3. Admin Approving Appeal...")
        approve_res = requests.post(f"{BASE_URL}/forensics/transactions/override/{tx_id}", headers=headers)
        if approve_res.status_code == 200:
            final_data = approve_res.json()
            print(f"   Final Status: {final_data['status']}")
        else:
            print(f"   Approval Failed: {approve_res.text}")
            return
            
        print("\n🏆 APPEAL WORKFLOW VERIFIED SUCCESSFULLY")
        
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_appeal_flow()
