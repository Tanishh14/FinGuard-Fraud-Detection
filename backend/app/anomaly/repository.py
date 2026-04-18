from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime
from app.db.models import Transaction, User, UserBehaviorProfile, SARRecord

class AnomalyRepository:
    """
    Handles database interactions for the Anomaly Detection module.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_user_profile(self, user_id: int) -> Optional[UserBehaviorProfile]:
        return self.db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == user_id).first()

    def get_high_risk_transactions(self, cutoff_date: datetime, threshold: float, limit: int) -> List[Transaction]:
        return self.db.query(Transaction, User).join(
            User, Transaction.user_id == User.id
        ).filter(
            and_(
                Transaction.timestamp >= cutoff_date,
                Transaction.final_risk_score >= threshold
            )
        ).order_by(desc(Transaction.timestamp)).limit(limit).all()

    def get_transaction_by_id(self, tx_id: int) -> Optional[Transaction]:
        return self.db.query(Transaction).filter(Transaction.id == tx_id).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_transactions(self, user_id: int, cutoff_date: datetime, limit: int) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.timestamp >= cutoff_date
            )
        ).order_by(desc(Transaction.timestamp)).limit(limit).all()

    def get_all_transactions_in_period(self, cutoff_date: datetime) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            Transaction.timestamp >= cutoff_date
        ).all()

    def get_sar_by_tx_id(self, tx_id: int) -> Optional[SARRecord]:
        return self.db.query(SARRecord).filter(SARRecord.tx_id == tx_id).order_by(desc(SARRecord.version)).first()

    def save_sar(self, sar: SARRecord):
        self.db.add(sar)
        self.db.commit()
        self.db.refresh(sar)
        return sar
