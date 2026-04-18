"""Initialize database tables for FinGuard AI."""
import sys
sys.path.append('app')

from app.db.session import engine
from app.db.base import Base
from app.db.models import (
    User, Transaction, UserBehaviorProfile, MerchantProfile, 
    UserDevice, UserAccount, AuditLog, ModelConfig, FeedbackRecord
)

print("Creating all database tables...")
Base.metadata.create_all(bind=engine)
print("Database initialized successfully!")
print("\nTables created:")
print("  - users")
print("  - user_behavior_profiles")
print("  - merchant_profiles")
print("  - user_devices")
print("  - user_accounts")
print("  - transactions")
print("  - audit_logs")
print("  - model_configs")
print("  - feedback_records")
