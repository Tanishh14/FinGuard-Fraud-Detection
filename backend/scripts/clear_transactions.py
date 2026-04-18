import sys
import os

# Path fix - allows running from backend/ without setting PYTHONPATH
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.db.session import SessionLocal
from app.db.models import Transaction, AuditLog, InvestigationCase, UserBehaviorProfile
from app.core.cache import cache_manager


def flush_redis_cache():
    """Wipe all similarity, velocity, and profile keys from Redis."""
    if not cache_manager.is_connected:
        print("  Redis not connected - skipping cache flush.")
        return

    client = cache_manager.client
    patterns = ["similarity:*", "velocity:*", "profile:user:*"]
    total_deleted = 0
    for pattern in patterns:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
            total_deleted += len(keys)
            print(f"  Flushed {len(keys)} keys matching '{pattern}'")
    if total_deleted == 0:
        print("  Redis cache was already empty.")
    else:
        print(f"  Total Redis keys deleted: {total_deleted}")


def clear_data():
    db = SessionLocal()
    try:
        # Delete dependent data first (FK order)
        print("Clearing Investigation Cases...")
        db.query(InvestigationCase).delete()
        print("Clearing Audit Logs...")
        db.query(AuditLog).delete()
        print("Clearing Transactions...")
        tx_count = db.query(Transaction).count()
        db.query(Transaction).delete()

        # Reset all user behavioral profiles to zero
        print("Resetting User Behavioral Profiles...")
        profiles = db.query(UserBehaviorProfile).all()
        for p in profiles:
            p.avg_amount = 0.0
            p.std_amount = 0.0
            p.total_tx_count = 0
            p.min_amount = None
            p.max_amount = None
            p.top_merchants = {}
            p.top_locations = {}
            p.known_devices = []
            p.known_ips = []
            p.night_tx_count = 0
            p.weekend_tx_count = 0
            p.night_tx_ratio = 0.0
            p.weekend_tx_ratio = 0.0
            p.tx_count_last_hour = 0
            p.tx_count_last_day = 0
            p.amount_last_hour = 0.0
            p.amount_last_day = 0.0
            p.tx_per_day = 0.0
            p.profile_maturity = "new"
            p._m2 = 0.0
            p.geo_entropy = 0.0
            p.first_tx_date = None
            p.last_tx_timestamp = None

        db.commit()
        print(f"[DB] Deleted {tx_count} transactions + audit logs + cases. Profiles reset.")

    except Exception as e:
        db.rollback()
        print(f"Error during DB clearing: {e}")
        raise
    finally:
        db.close()

    # Flush Redis AFTER DB is clean
    print("Flushing Redis cache...")
    flush_redis_cache()

    print("")
    print("=" * 50)
    print("[OK] All transactions cleared. System is clean.")
    print("=" * 50)


if __name__ == "__main__":
    clear_data()

