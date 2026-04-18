from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from app.core.dependencies import (
    get_db, get_current_user, 
    require_analyst_or_admin as analyst_or_admin,
    require_admin as admin_only,
    require_auditor_access as auditor_only
)
from app.db.models import User
from app.audit.service import AuditService
from app.schemas.api import ReviewRequest, ModelHealthStats

router = APIRouter()

def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)

@router.get("/review-queue", response_model=List[dict])
def get_review_queue(
    limit: int = Query(50, ge=1, le=200),
    service: AuditService = Depends(get_audit_service),
    analyst: User = Depends(analyst_or_admin)
):
    """Get transactions flagged for analyst review."""
    return service.get_pending_reviews(limit=limit)

@router.get("/transactions/{tx_id}", response_model=List[dict])
def get_transaction_audit_trail(
    tx_id: int,
    service: AuditService = Depends(get_audit_service),
    user: User = Depends(analyst_or_admin)
):
    """Get complete audit trail for a transaction."""
    trail = service.get_transaction_audit_trail(tx_id)
    if not trail:
        raise HTTPException(status_code=404, detail="No audit trail found")
    return trail

@router.post("/transactions/{tx_id}/review")
def review_transaction(
    tx_id: int,
    review: ReviewRequest,
    service: AuditService = Depends(get_audit_service),
    analyst: User = Depends(analyst_or_admin)
):
    """Record analyst's review decision on a transaction."""
    from app.audit.repository import AuditRepository
    repo = AuditRepository(service.db)
    audit = repo.get_latest_audit_for_tx(tx_id)
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    try:
        updated = service.record_analyst_action(
            audit_id=audit.id, analyst_id=analyst.id, 
            action=review.action.value, notes=review.notes
        )
        return {"status": "success", "audit_id": updated.id, "final_decision": updated.final_decision}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/export")
def export_audit_logs(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    service: AuditService = Depends(get_audit_service),
    auditor: User = Depends(auditor_only)
):
    """Export audit logs for regulatory compliance."""
    data = service.export_audit_logs(start_date, end_date, format)
    media_type = "text/csv" if format == "csv" else "application/json"
    return Response(content=data, media_type=media_type)

@router.get("/stats")
def get_model_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    service: AuditService = Depends(get_audit_service),
    user: User = Depends(analyst_or_admin)
):
    """Get model performance statistics."""
    if not end_date: end_date = datetime.utcnow()
    if not start_date: start_date = end_date - timedelta(days=30)
    return service.get_model_performance_stats(start_date, end_date)
