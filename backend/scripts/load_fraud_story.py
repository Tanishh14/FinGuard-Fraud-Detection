import sys
import os
import random
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import User, Transaction, UserBehaviorProfile, UserDevice, MerchantProfile

def load_mumbai_ring_story():
    db = SessionLocal()
    try:
        print("🎬 Initializing 'The Mumbai ATM Ring' Story...")
        
        # 1. Create Target Users
        users = []
        for i in range(3):
            email = f"ring_victim_{i}@example.com"
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    username=f"Victim_{i}",
                    hashed_password="hashed_password",
                    role="end_user"
                )
                db.add(user)
                db.flush()
            users.append(user)

        # 2. Setup Baseline Profiles
        for user in users:
            profile = db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == user.id).first()
            if not profile:
                profile = UserBehaviorProfile(
                    user_id=user.id,
                    avg_amount=2500.0,
                    total_tx_count=50,
                    last_updated=datetime.utcnow() - timedelta(days=1)
                )
                db.add(profile)

        # 3. SET THE STAGE: Transaction Sequence
        # Device ID shared across the ring
        SHARED_DEVICE = "ATTACK_DEVICE_99"
        MUMBAI_LAT = 19.0760
        MUMBAI_LNG = 72.8777

        # Step 1: User 0 Compromise (High Amount, New Location)
        t1 = Transaction(
            user_id=users[0].id,
            amount=85000.0,
            merchant="Mumbai Central ATM",
            location="Mumbai, IN",
            latitude=MUMBAI_LAT,
            longitude=MUMBAI_LNG,
            device_id=SHARED_DEVICE,
            ip_address="103.12.45.1",
            risk_score=0.85,
            status="BLOCKED",
            explanation="Anomaly: Amount 34x above 30-day average. Geographic jump detected.",
            timestamp=datetime.utcnow() - timedelta(minutes=10)
        )
        db.add(t1)

        # Step 2: User 1 and 2 share the same device minutes later
        for i in range(1, 3):
            t = Transaction(
                user_id=users[i].id,
                amount=5000.0,
                merchant="Mumbai West Store",
                location="Mumbai, IN",
                latitude=MUMBAI_LAT + (random.random() * 0.01),
                longitude=MUMBAI_LNG + (random.random() * 0.01),
                device_id=SHARED_DEVICE,
                ip_address="103.12.45.1",
                risk_score=0.92,
                status="FLAGGED",
                explanation="GNN: Shared device infrastructure link found across 3 accounts.",
                timestamp=datetime.utcnow() - timedelta(minutes=5)
            )
            db.add(t)

        db.commit()
        print("✅ Story Loaded successfully.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error loading story: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_mumbai_ring_story()
