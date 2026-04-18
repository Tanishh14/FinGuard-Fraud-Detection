import sys
import os
import random
from datetime import datetime

# Robust Path Fix
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.db.session import SessionLocal
from app.db.models import Transaction, User, UserRole, TransactionStatus

def create_fraud_ring():
    db = SessionLocal()
    try:
        print("Creating Complex Fraud Ring Data...")
        # Create 6 fake users
        users = []
        for i in range(1, 7):
            email = f"ring_member_{i}@fraud.com"
            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password="fake_password_hash",
                    username=f"Ring Member {i}",
                    role=UserRole.END_USER.value,
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            users.append(user)
        
        # Ring 1: Circular A -> B -> C -> A (The core)
        # Ring 2: D -> E -> F -> D (The satellite)
        # Bridge: B <-> D (The connection)
        
        amount = 95000.0
        
        # Sequence of transactions to form the ring
        tx_chain = [
            (users[0], users[1], "Crypto Exchange X"),
            (users[1], users[2], "Gambling Portal Y"),
            (users[2], users[0], "Laundromat Z"),
            (users[3], users[4], "Shell Co A"),
            (users[4], users[5], "Shell Co B"),
            (users[5], users[3], "Shell Co C"),
            (users[1], users[3], "Bridge Transfer"), # The bridge
        ]
        
        for sender, rec_user, merchant in tx_chain:
            tx = Transaction(
                user_id=sender.id,
                recipient_name=rec_user.username,
                amount=amount + random.uniform(-500, 500),
                merchant=merchant,
                timestamp=datetime.utcnow(),
                status=TransactionStatus.BLOCKED.value, 
                risk_score=0.99,
                anomaly_score=0.98,
                gnn_score=0.97,
                device_id="device_shared_999", # All share a device
                ip_address="192.168.1.99"
            )
            db.add(tx)
            amount -= 100 # Peeling off small amounts

        db.commit()
        print("✓ Successfully injected Complex Fraud Ring (6 nodes, shared device).")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_fraud_ring()
