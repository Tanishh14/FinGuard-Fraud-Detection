from fastapi.testclient import TestClient

def test_health_check(client):
    """Test system health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_auth_workflow(client):
    """Test full authentication lifecycle."""
    # 1. Register
    reg_response = client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "username": "testuser",
            "password": "securepassword",
            "role": "end_user"
        }
    )
    assert reg_response.status_code == 200
    
    # 2. Login
    login_response = client.post(
        "/auth/login",
        json={"email": "user@test.com", "password": "securepassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token is not None

    # 3. Get User Profile
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@test.com"

def test_transaction_scoring_pipeline(client, test_user):
    """Test transaction creation and real-time ML scoring."""
    tx_payload = {
        "user_id": 1,
        "amount": 50000.0,
        "merchant": "High Risk Electronics",
        "recipient_name": "Unknown Entity",
        "device_id": "dev_123",
        "ip_address": "192.168.1.100",
        "location": "Mumbai",
        "currency": "INR",
        "timestamp": "2024-01-01T10:00:00"
    }
    
    response = client.post(
        "/anomaly/detection",
        json=tx_payload,
        headers=test_user
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check ML Scoring keys exist
    assert "scores" in data
    assert "ae_score" in data["scores"]
    assert "if_score" in data["scores"]
    assert "final_risk_score" in data["scores"]
    
    # Check decision logic
    assert data["decision"] in ["APPROVED", "FLAGGED", "BLOCKED", "PENDING"]

def test_gnn_fraud_rings(client, test_user):
    """Test GNN fraud ring detection endpoint (requires analyst/admin)."""
    # Create some dummy transactions to analyze (handled by conftest or just rely on empty DB returning [])
    # Even with empty DB, it should not 500
    
    response = client.get(
        "/gnn/fraud-rings?days=30",
        headers=test_user
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_explainability_endpoint(client, test_user):
    """Test explainability endpoint (mocking LLM if needed)."""
    # First create a transaction to explain
    tx_payload = {
        "user_id": 1,
        "amount": 9999999.0, # Extreme amount to trigger flags
        "merchant": "Test Merchant",
        "recipient_name": "Test Recipient",
        "device_id": "dev_test",
        "ip_address": "127.0.0.1",
        "location": "Test Loc"
    }
    tx_res = client.post("/anomaly/detection", json=tx_payload, headers=test_user)
    tx_id = tx_res.json()["transaction_id"]
    
    # Call explainability
    explain_res = client.get(
        f"/explainability/transaction/{tx_id}",
        headers=test_user
    )
    
    assert explain_res.status_code == 200
    data = explain_res.json()
    assert "explanation" in data
    assert data["transaction_id"] == tx_id
    # Ensure fallback works (it returns a string even if LLM fails)
    assert isinstance(data["explanation"], str)
