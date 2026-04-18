from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from app.db.models import AuditLog, Transaction, FeedbackRecord

class AuditRepository:
    """
    Handles all database operations for the Audit module.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(self, audit_data: Dict[str, Any]) -> AuditLog:
        audit = AuditLog(**audit_data)
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def get_audit_by_id(self, audit_id: int) -> Optional[AuditLog]:
        return self.db.query(AuditLog).filter(AuditLog.id == audit_id).first()

    def get_latest_audit_for_tx(self, tx_id: int) -> Optional[AuditLog]:
        return self.db.query(AuditLog).filter(AuditLog.tx_id == tx_id).order_by(AuditLog.timestamp.desc()).first()

    def get_transaction_audit_trail(self, tx_id: int) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(AuditLog.tx_id == tx_id).order_by(AuditLog.timestamp).all()

    def update_audit_log(self, audit: AuditLog, update_data: Dict[str, Any]) -> AuditLog:
        for key, value in update_data.items():
            setattr(audit, key, value)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def create_feedback_record(self, feedback_data: Dict[str, Any]) -> FeedbackRecord:
        feedback = FeedbackRecord(**feedback_data)
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_pending_reviews(self, limit: int) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            Transaction.status.in_(["FLAGGED", "UNDER_REVIEW"])
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    def get_audits_in_range(self, start_date: datetime, end_date: datetime) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
        ).order_by(AuditLog.timestamp).all()

    def get_all_audits(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> List[AuditLog]:
        query = self.db.query(AuditLog)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        return query.all()
