from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.dependencies import get_db, require_analyst_or_admin, require_admin
from app.db.models import User
from app.profiles.service import ProfileService

router = APIRouter()

def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    return ProfileService(db)

@router.get("/user/{user_id}")
def get_user_profile(
    user_id: int,
    service: ProfileService = Depends(get_profile_service),
    analyst: User = Depends(require_analyst_or_admin)
) -> Dict[str, Any]:
    """Get complete behavioral profile for a user."""
    return service.get_detailed_profile(user_id)

@router.get("/statistics/{user_id}")
def get_profile_statistics(
    user_id: int,
    days: int = 90,
    service: ProfileService = Depends(get_profile_service),
    analyst: User = Depends(require_analyst_or_admin)
) -> Dict[str, Any]:
    """Get detailed statistical analysis of user behavior."""
    return service.get_user_statistics(user_id, days)

@router.post("/reset/{user_id}")
def reset_user_profile(
    user_id: int,
    service: ProfileService = Depends(get_profile_service),
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Reset user behavioral profile (admin only)."""
    profile = service.reset_profile(user_id)
    return {
        "status": "success",
        "message": f"Profile reset for user {user_id}",
        "last_updated": profile.last_updated.isoformat()
    }

@router.get("/drift-alerts")
def get_profile_drift_alerts(
    threshold: float = 3.0,
    service: ProfileService = Depends(get_profile_service),
    analyst: User = Depends(require_analyst_or_admin)
) -> Dict[str, Any]:
    """Get users with significant profile drift."""
    alerts = service.get_drift_alerts(threshold)
    return {
        "status": "success",
        "drift_alerts": alerts,
        "count": len(alerts),
        "threshold": threshold
    }
