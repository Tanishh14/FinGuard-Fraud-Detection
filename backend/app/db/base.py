"""
FinGuard Database Base
Centralized SQLAlchemy base - re-exports Base from models
"""
# Import Base and all models from models.py
# This module exists for backwards compatibility and centralized imports
from app.db.models import (
    Base,
    User,
    UserRole,
    UserBehaviorProfile,
    UserDevice,
    UserAccount,
    MerchantProfile,
    MerchantRiskLevel,
    Transaction,
    TransactionStatus,
    AuditLog,
    AnalystAction,
    ModelConfig,
    FeedbackRecord
)

__all__ = [
    "Base",
    "User",
    "UserRole",
    "UserBehaviorProfile",
    "UserDevice",
    "UserAccount",
    "MerchantProfile",
    "MerchantRiskLevel",
    "Transaction",
    "TransactionStatus",
    "AuditLog",
    "AnalystAction",
    "ModelConfig",
    "FeedbackRecord"
]
