from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.session import get_db
from app.db.models import User
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.anomaly.service import AnomalyService

from pydantic import BaseModel, Field
from typing import Optional

class AnomalyDetectionRequest(BaseModel):
    user_id: int
    merchant: str
    amount: float = Field(gt=0)
    device_id: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[str] = None

router = APIRouter(tags=["Anomaly Detection"])

def get_anomaly_service(db: Session = Depends(get_db)) -> AnomalyService:
    return AnomalyService(db)

@router.post("/detection")
def detect_anomaly(
    request: AnomalyDetectionRequest,
    service: AnomalyService = Depends(get_anomaly_service),
    current_user: User = Depends(get_current_user)
):
    """Perform real-time anomaly detection on a transaction."""
    return service.detect_transaction_anomaly(request.model_dump())

@router.get("/patterns")
def get_anomaly_patterns(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    service: AnomalyService = Depends(get_anomaly_service),
    analyst: User = Depends(require_analyst_or_admin)
):
    """Get recent anomaly patterns from the transaction history."""
    return service.get_recent_anomaly_patterns(days, limit)

@router.post("/{transaction_id}/explain")
def explain_transaction(
    transaction_id: int,
    service: AnomalyService = Depends(get_anomaly_service),
    analyst: User = Depends(require_analyst_or_admin)
):
    """Generate structured LLM explanation for a transaction."""
    return service.explain_anomaly(transaction_id)

@router.post("/{transaction_id}/generate-sar")
def generate_sar(
    transaction_id: int,
    service: AnomalyService = Depends(get_anomaly_service),
    analyst: User = Depends(require_analyst_or_admin)
):
    """Generate compliance-grade SAR narrative (Analyst/Admin only)."""
    return service.generate_sar(transaction_id, analyst.id)

@router.get("/statistics")
def get_anomaly_statistics(
    days: int = Query(30, ge=1, le=365),
    service: AnomalyService = Depends(get_anomaly_service),
    analyst: User = Depends(require_analyst_or_admin)
):
    """Get system-wide anomaly detection statistics."""
    return service.get_system_statistics(days)
