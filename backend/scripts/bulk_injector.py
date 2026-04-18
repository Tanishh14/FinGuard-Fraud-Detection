import asyncio
import random
import uuid
import logging
import time
import sys
import os
from datetime import datetime, timedelta

# -------------------------
# PATH FIX - run from backend/ without PYTHONPATH
# -------------------------
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import User
from app.transactions.service import TransactionService

# Reduce logging noise
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# -------------------------
# SYNTHETIC USER POOL CONFIG
# -------------------------

# How many unique synthetic users to create in the pool.
# Transactions will randomly pick from these (with repeats).
SYNTHETIC_USER_COUNT = 100
SYNTHETIC_EMAIL_SUFFIX = "@bulk.inject"

# -------------------------
# DATA POOLS
# -------------------------

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Arnav", "Ayaan",
    "Krishna", "Ishaan", "Shaurya", "Atharv", "Advait", "Pranav", "Dhruv",
    "Priya", "Ananya", "Kavya", "Shruti", "Pooja", "Sneha", "Riya", "Meera",
    "Divya", "Neha", "Swati", "Anjali", "Deepika", "Nisha", "Lakshmi"
]

LAST_NAMES = [
    "Sharma", "Verma", "Kumar", "Singh", "Patel", "Gupta",
    "Reddy", "Iyer", "Nair", "Joshi", "Mehta", "Shah", "Pillai",
    "Rao", "Das", "Bose", "Chatterjee", "Mukherjee", "Mishra", "Tiwari"
]

MERCHANT_TYPES = [
    "Electronics", "Fashion", "Groceries", "Pharmacy",
    "Restaurant", "Cafe", "Fitness", "Bookstore",
    "Travel", "Fuel", "Healthcare", "Education",
    "Luxury_Retail", "Gaming", "Streaming", "HomeDecor"
]

LOCATIONS = [
    "Mumbai, MH", "Delhi, DL", "Bengaluru, KA",
    "Hyderabad, TG", "Chennai, TN", "Pune, MH",
    "Ahmedabad, GJ", "Kolkata, WB", "Jaipur, RJ", "Surat, GJ"
]

DEVICES = [f"DEV_{i:03d}" for i in range(1, 500)]
IPS = [f"192.168.{random.randint(0, 255)}.{i}" for i in range(1, 255)]


# -------------------------
# GENERATORS
# -------------------------

def random_person():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_merchant():
    return f"{random.choice(MERCHANT_TYPES)}_{random.randint(100, 999)}"


# -------------------------
# SYNTHETIC USER POOL
# -------------------------

def get_or_create_synthetic_users(db: Session) -> list:
    """
    Creates a pool of SYNTHETIC_USER_COUNT synthetic User rows in the DB,
    tagged with @bulk.inject emails so they can be identified and cleaned up.
    Returns the full list of synthetic User objects.
    """
    existing = db.query(User).filter(
        User.email.like(f"%{SYNTHETIC_EMAIL_SUFFIX}")
    ).all()

    if len(existing) >= SYNTHETIC_USER_COUNT:
        print(f"[Pool] Using existing {len(existing)} synthetic users.")
        return existing

    needed = SYNTHETIC_USER_COUNT - len(existing)
    existing_emails = {u.email for u in existing}
    print(f"[Pool] Creating {needed} new synthetic users (pool target: {SYNTHETIC_USER_COUNT})...")

    new_users = []
    i = len(existing)
    while len(new_users) < needed:
        email = f"synthetic_{i:04d}{SYNTHETIC_EMAIL_SUFFIX}"
        if email not in existing_emails:
            name = random_person()
            username = f"{name.replace(' ', '_')}_{i}"
            user = User(
                email=email,
                username=username,
                hashed_password="bulk_inject_dummy_not_loginable",
                role="end_user",
                is_active=True,
                # IMPORTANT: 2FA enabled so MFA gate never blocks large amounts
                is_2fa_enabled=True,
            )
            db.add(user)
            new_users.append(user)
        i += 1

    db.commit()
    # Refresh to get DB-assigned IDs
    for u in new_users:
        db.refresh(u)

    all_synthetic = existing + new_users
    print(f"[Pool] Synthetic user pool ready: {len(all_synthetic)} users "
          f"(IDs {all_synthetic[0].id} - {all_synthetic[-1].id})")
    return all_synthetic


# -------------------------
# SAFE BULK INJECTOR
# -------------------------

async def inject_transactions(count=5000):
    db: Session = SessionLocal()
    service = TransactionService(db)

    # Build or load the synthetic user pool
    synthetic_users = get_or_create_synthetic_users(db)
    if not synthetic_users:
        print("[ERROR] Could not create synthetic users. Aborting.")
        db.close()
        return

    print(f"[>>] Starting injection of {count} transactions "
          f"across {len(synthetic_users)} synthetic users")
    start_time = time.time()

    approved = 0
    blocked = 0
    flagged = 0

    # -------------------------
    # INITIALIZE MODELS
    # -------------------------
    from app.ml.registry import registry
    registry.load_all_models()

    # -------------------------
    # MOCK MAIL & BROADCAST
    # (avoid sending real emails / websocket noise during bulk run)
    # -------------------------
    from app.realtime.websocket import manager
    from app.core.mail import mail_service

    async def noop_async(*args, **kwargs): return None
    def noop(*args, **kwargs): return None

    original_broadcast = manager.broadcast_transaction_event
    manager.broadcast_transaction_event = noop_async
    mail_service.send_transaction_alert = noop
    mail_service.send_otp_email = noop

    # -------------------------
    # MAIN LOOP
    # -------------------------

    for i in range(count):

        scenario = random.choices(
            ["NORMAL", "P2P", "LOW", "WHALE", "NIGHT"],
            weights=[60, 20, 10, 5, 5]
        )[0]

        # Pick a random synthetic user (can repeat)
        user = random.choice(synthetic_users)

        timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 10000))
        location = random.choice(LOCATIONS)
        device_id = random.choice(DEVICES)
        ip_address = random.choice(IPS)

        if scenario == "P2P":
            merchant = random_person()
            merchant_id = f"U_{uuid.uuid4().hex[:8]}"
            amount = round(random.uniform(10, 2000), 2)

        elif scenario == "LOW":
            merchant = "Local_Kirana"
            merchant_id = f"M_LOCAL_{random.randint(1000, 9999)}"
            amount = round(random.uniform(5, 100), 2)

        elif scenario == "WHALE":
            merchant = "Luxury_Retail"
            merchant_id = "M_LUXURY"
            amount = round(random.uniform(35000, 55000), 2)

        elif scenario == "NIGHT":
            merchant = random_merchant()
            merchant_id = f"M_{random.randint(1000, 9999)}"
            amount = round(random.uniform(8000, 25000), 2)
            timestamp = timestamp.replace(hour=random.randint(1, 4))

        else:  # NORMAL
            merchant = random_merchant()
            merchant_id = f"M_{random.randint(1000, 9999)}"
            amount = round(random.uniform(100, 5000), 2)

        payload = {
            "amount": amount,
            "merchant": merchant,
            "merchant_id": merchant_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "location": location,
            "timestamp": timestamp.isoformat()
        }

        try:
            tx = await service.process_transaction(payload, user)

            if tx.status == "APPROVED":
                approved += 1
            elif tx.status == "BLOCKED":
                blocked += 1
            else:
                flagged += 1

        except Exception as e:
            db.rollback()
            logger.warning(f"Transaction failed at {i}: {e}")

        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            pct = ((i + 1) / count) * 100
            print(f"Progress: {i+1}/{count} ({pct:.0f}%) | {rate:.1f} tx/s | "
                  f"OK:{approved} BL:{blocked} FL:{flagged}")

    # Restore broadcast
    manager.broadcast_transaction_event = original_broadcast

    total_time = time.time() - start_time

    print("-" * 60)
    print(f"[OK] Completed in {total_time:.2f}s")
    print(f"Approved : {approved}  ({approved/count*100:.1f}%)")
    print(f"Blocked  : {blocked}  ({blocked/count*100:.1f}%)")
    print(f"Flagged  : {flagged}  ({flagged/count*100:.1f}%)")
    print(f"[**] Average Rate: {count/total_time:.2f} tx/s")
    print(f"Users used: {len(synthetic_users)} synthetic users (randomly repeated)")

    db.close()


# -------------------------
# ENTRY POINT
# -------------------------

if __name__ == "__main__":
    count = 5000

    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass

    asyncio.run(inject_transactions(count))
