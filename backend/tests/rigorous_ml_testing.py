import os
import sys
import torch
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ml.registry import registry
from app.ml.scoring_pipeline import get_scoring_pipeline
from app.db.session import SessionLocal
from app.db.models import User, Transaction, MerchantProfile

def setup_test_data(db):
    """Setup basic test data if not exists."""
    user = db.query(User).filter(User.email == "test_ml@example.com").first()
    if not user:
        user = User(email="test_ml@example.com", hashed_password="hashed_password", role="end_user")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    merchant = db.query(MerchantProfile).filter(MerchantProfile.merchant_id == "M_TEST").first()
    if not merchant:
        merchant = MerchantProfile(merchant_id="M_TEST", merchant_name="Test Merchant", category="retail")
        db.add(merchant)
        db.commit()
    
    return user

def run_rigorous_tests():
    db = SessionLocal()
    user = setup_test_data(db)
    
    registry.load_all_models()
    pipeline = get_scoring_pipeline()
    
    scenarios = [
        {
            "name": "Normal Transaction",
            "data": {
                "user_id": user.id,
                "amount": 500.0,
                "merchant": "Test Merchant",
                "merchant_id": "M_TEST",
                "device_id": "D_NORMAL",
                "location": "Mumbai",
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        {
            "name": "High-Value Anomaly",
            "data": {
                "user_id": user.id,
                "amount": 500000.0, # 1000x normal
                "merchant": "Test Merchant",
                "merchant_id": "M_TEST",
                "device_id": "D_NORMAL",
                "location": "Mumbai",
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        {
            "name": "New Device & Location",
            "data": {
                "user_id": user.id,
                "amount": 2000.0,
                "merchant": "Test Merchant",
                "merchant_id": "M_TEST",
                "device_id": "D_NEW_FOREIGN",
                "location": "Lagos",
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        {
            "name": "Absurdly High Amount (INR6T)",
            "data": {
                "user_id": user.id,
                "amount": 6000000000000.0,
                "merchant": "tt",
                "merchant_id": "11",
                "device_id": "D_NORMAL",
                "location": "Mumbai",
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        {
            "name": "Very High Amount (INR900k)",
            "data": {
                "user_id": user.id,
                "amount": 900000.0,
                "merchant": "amao",
                "merchant_id": "22",
                "device_id": "D_NORMAL",
                "location": "Mumbai",
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        {
            "name": "Night-Time Transaction",
            "data": {
                "user_id": user.id,
                "amount": 1500.0,
                "merchant": "Test Merchant",
                "merchant_id": "M_TEST",
                "device_id": "D_NORMAL",
                "location": "Mumbai",
                "timestamp": datetime(2025, 1, 1, 3, 0, 0).isoformat() # 3 AM
            }
        }
    ]
    
    print("\n" + "="*80)
    print(f"{'SCENARIO':<30} | {'FINAL':<8} | {'AE':<8} | {'IF':<8} | {'GNN':<8} | {'DECISION'}")
    print("-"*80)
    
    for s in scenarios:
        print(f"\nTesting Scenario: {s['name']}")
        result = pipeline.score_transaction(db, s["data"])
        print(f"AE: {result.get('ae_score')} | IF: {result.get('if_score')} | GNN: {result.get('gnn_score')} (Active: {result.get('gnn_active')})")
        print(f"FINAL RISK: {result.get('final_risk')} | DECISION: {result.get('decision')}")
        print(f"REASON: {result.get('decision_reason')}")
        
    print("\n" + "="*80)
    print(f"{'SCENARIO':<30} | {'FINAL':<8} | {'DECISION':<15} | {'REASON'}")
    print("-"*80)
    
    for s in scenarios:
        result = pipeline.score_transaction(db, s["data"])
        print(f"{s['name']:<30} | {result['final_risk']*100:>7.1f}% | {result['decision']:<15} | {result['decision_reason'][:40]}...")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    run_rigorous_tests()
