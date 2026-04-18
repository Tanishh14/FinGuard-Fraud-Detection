from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.db.models import Transaction, User

class TransactionRepository:
    """
    Handles all database operations for the Transactions module.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tx_id: int) -> Optional[Transaction]:
        return self.db.query(Transaction).filter(Transaction.id == tx_id).first()

    def create(self, tx_data: Dict[str, Any]) -> Transaction:
        tx = Transaction(**tx_data)
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx

    def update(self, tx: Transaction, update_data: Dict[str, Any]) -> Transaction:
        for key, value in update_data.items():
            setattr(tx, key, value)
        self.db.commit()
        self.db.refresh(tx)
        return tx

    def get_count(self, user_id: Optional[int] = None, filters: Dict[str, Any] = None) -> int:
        query = self.db.query(func.count(Transaction.id))
        
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
        
        if filters:
            query = self._apply_filters(query, filters)
            
        return query.scalar() or 0

    def get_all(self, user_id: Optional[int] = None, filters: Dict[str, Any] = None, 
                page: int = 1, page_size: int = 200) -> List[Transaction]:
        query = self.db.query(Transaction, User.username).join(User, Transaction.user_id == User.id)
        
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
            
        if filters:
            query = self._apply_filters(query, filters, join_user=True)
            
        offset = (page - 1) * page_size
        results = query.order_by(Transaction.timestamp.desc()).offset(offset).limit(page_size).all()
        
        txs = []
        for tx, uname in results:
            tx.username = uname
            txs.append(tx)
        return txs

    def _apply_filters(self, query, filters: Dict[str, Any], join_user: bool = False):
        if filters.get("username") and join_user:
            query = query.filter(User.username.ilike(f"%{filters['username']}%"))
        elif filters.get("username"):
            # If we haven't joined yet but need to filter by username
            query = query.join(User, Transaction.user_id == User.id).filter(User.username.ilike(f"%{filters['username']}%"))
            
        if filters.get("merchant"):
            query = query.filter(Transaction.merchant.ilike(f"%{filters['merchant']}%"))
        if filters.get("min_amount") is not None:
            query = query.filter(Transaction.amount >= filters["min_amount"])
        if filters.get("max_amount") is not None:
            query = query.filter(Transaction.amount <= filters["max_amount"])
        if filters.get("risk_level"):
            risk_level = filters["risk_level"].upper()
            if risk_level == "SAFE":
                query = query.filter(Transaction.decision == "APPROVED")
            elif risk_level == "SUSPICIOUS":
                query = query.filter(Transaction.decision == "FLAGGED")
            elif risk_level == "BLOCKED":
                query = query.filter(Transaction.decision == "BLOCKED")
        return query

    def create_sar_draft(self, user_id: int, tx_id: int, reason: str):
        from app.db.models import SARRecord
        sar = SARRecord(
            user_id=user_id,
            transaction_id=tx_id,
            reason=reason,
            status="DRAFT" # Hardening: Analyst review mandatory
        )
        self.db.add(sar)
        self.db.commit()
        return sar
