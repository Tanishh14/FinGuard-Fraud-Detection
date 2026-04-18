"""
FinGuard User Behavior Profile Module
=====================================
Implements persistent user behavioral baselines with online learning.
Profiles are updated incrementally after each transaction.
"""
from app.profiles.service import ProfileService

__all__ = ["ProfileService"]

