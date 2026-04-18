import requests
import os

# Configuration
API_URL = "http://localhost:8000/analytics/reports/download"
TOKEN_URL = "http://localhost:8000/auth/login"

def get_admin_token():
    # Attempting to get token for an admin/analyst. 
    # In this environment, I'll try to find an existing user or use a common demo one.
    # Note: This part might fail if there are no users, but the goal is to test the logic.
    payload = {
        "username": "analyst",
        "password": "password123"
    }
    try:
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"Auth failed: {e}")
        return None

def test_pdf_generation():
    token = get_admin_token()
    if not token:
        print("Skipping PDF test: No valid token.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    params = {"time_range": "7d"}
    
    print(f"Requesting PDF with params: {params}...")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type")
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {content_type}")
        
        if content_type == "application/pdf":
            file_path = "temp_test_report.pdf"
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"✅ PDF successfully generated and saved to {file_path}")
            print(f"File Size: {len(response.content)} bytes")
        else:
            print(f"❌ Unexpected content type: {content_type}")
            
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")

if __name__ == "__main__":
    # Ensure backend is running before this
    test_pdf_generation()
