from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, desc
from datetime import datetime, timedelta
from app.db.models import Transaction, InvestigationCase, UserDevice, AuditLog, User

class AnalyticsRepository:
    """
    Handles optimized SQL aggregations for dashboard and analytics.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_status_counts(self, start_time: datetime) -> List[tuple]:
        return self.db.query(
            Transaction.status, func.count(Transaction.id)
        ).filter(Transaction.timestamp >= start_time).group_by(Transaction.status).all()

    def get_transaction_count(self, start_time: datetime) -> int:
        return self.db.query(Transaction).filter(Transaction.timestamp >= start_time).count()

    def get_avg_risk_score(self, start_time: datetime) -> float:
        return float(self.db.query(func.avg(Transaction.final_risk_score)).filter(Transaction.timestamp >= start_time).scalar() or 0.0)

    def get_avg_anomaly_score(self, start_time: datetime) -> float:
        return float(self.db.query(func.avg(Transaction.anomaly_score)).filter(Transaction.timestamp >= start_time).scalar() or 0.0)

    def get_avg_gnn_score(self, start_time: datetime) -> float:
        return float(self.db.query(func.avg(Transaction.gnn_score)).filter(Transaction.timestamp >= start_time).scalar() or 0.0)

    def get_avg_if_score(self, start_time: datetime) -> float:
        return float(self.db.query(func.avg(Transaction.if_score)).filter(Transaction.timestamp >= start_time).scalar() or 0.0)

    def get_high_risk_user_count(self, start_time: datetime, threshold: float) -> int:
        return self.db.query(Transaction.user_id).filter(
            and_(Transaction.timestamp >= start_time, Transaction.final_risk_score > threshold)
        ).distinct().count()

    def get_low_trust_device_count(self, threshold: float) -> int:
        return self.db.query(UserDevice).filter(UserDevice.trust_score < threshold).count()

    def get_time_bucketed_stats(self, start_time: datetime) -> List[tuple]:
        # Note: Database specific logic should be handled here
        bind = self.db.get_bind()
        if "postgresql" in str(bind.url):
            time_bucket = func.to_char(Transaction.timestamp, 'HH24:MI').label('minute')
        else:
            time_bucket = func.strftime('%H:%M', Transaction.timestamp).label('minute')

        return self.db.query(
            time_bucket, Transaction.status, func.count(Transaction.id)
        ).filter(Transaction.timestamp >= start_time).group_by('minute', Transaction.status).all()

    def get_top_users_by_risk(self, start_time: datetime, threshold: float, limit: int) -> List[tuple]:
        return self.db.query(
            Transaction.user_id,
            func.max(Transaction.final_risk_score).label("max_risk"),
            func.count(Transaction.id).label("tx_count"),
            func.max(Transaction.timestamp).label("last_active")
        ).filter(
            and_(Transaction.timestamp >= start_time, Transaction.final_risk_score > threshold)
        ).group_by(Transaction.user_id).order_by(desc("max_risk")).limit(limit).all()

    def get_case_stats(self) -> Dict[str, int]:
        return {
            "open": self.db.query(InvestigationCase).filter(InvestigationCase.status == "OPEN").count(),
            "pending": self.db.query(Transaction).filter(Transaction.status == "UNDER_REVIEW").count(),
            "resolved_today": self.db.query(InvestigationCase).filter(
                and_(InvestigationCase.status == "RESOLVED", InvestigationCase.updated_at >= datetime.utcnow().date())
            ).count()
        }

    def get_geo_data(self, start_time: datetime) -> List[tuple]:
        return self.db.query(
            Transaction.location, Transaction.latitude, Transaction.longitude,
            func.count(Transaction.id).label("count"),
            func.avg(Transaction.final_risk_score).label("avg_risk")
        ).filter(
            and_(Transaction.timestamp >= start_time, Transaction.latitude.isnot(None))
        ).group_by(Transaction.location, Transaction.latitude, Transaction.longitude).all()

    def get_model_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculates confusion matrix components based on analyst overrides."""
        audits = self.db.query(AuditLog).filter(
            and_(AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date)
        ).all()
        
        if not audits:
            return {"total": 0, "precision": 0, "recall": 0, "f1": 0}
            
        tp = sum(1 for a in audits if a.auto_decision in ["FLAGGED", "BLOCKED"] and a.analyst_action in ["REJECTED", "ESCALATED", "BLOCKED"])
        fp = sum(1 for a in audits if a.auto_decision in ["FLAGGED", "BLOCKED"] and a.analyst_action == "APPROVED")
        fn = sum(1 for a in audits if a.auto_decision == "APPROVED" and a.analyst_action in ["REJECTED", "ESCALATED", "BLOCKED"])
        tn = sum(1 for a in audits if a.auto_decision == "APPROVED" and (not a.analyst_action or a.analyst_action == "APPROVED"))
        
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * (precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0
        
        return {
            "total": len(audits),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "accuracy": round(float((tp + tn) / len(audits)), 3)
        }

    def get_risk_trends(self, days: int, threshold: float) -> List[Dict[str, Any]]:
        """Time-series of high-risk vs total transactions."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Determine time bucket based on range
        bind = self.db.get_bind()
        if "postgresql" in str(bind.url):
            date_bucket = func.to_char(Transaction.timestamp, 'YYYY-MM-DD').label('day')
        else:
            date_bucket = func.strftime('%Y-%m-%d', Transaction.timestamp).label('day')

        stats = self.db.query(
            date_bucket,
            func.count(Transaction.id).label("total"),
            func.sum(case((Transaction.status == "BLOCKED", 1), else_=0)).label("blocked")
        ).filter(Transaction.timestamp >= start_date).group_by('day').order_by('day').all()

        return [
            {"date": s.day, "total": s.total, "blocked": int(s.blocked or 0)}
            for s in stats
        ]

    def get_risk_gauges(self, threshold: float) -> Dict[str, Any]:
        """Risk distribution for gauge charts."""
        total = self.db.query(Transaction).count()
        high_risk = self.db.query(Transaction).filter(Transaction.final_risk_score >= threshold).count()
        med_risk = self.db.query(Transaction).filter(
            and_(Transaction.final_risk_score >= 0.4, Transaction.final_risk_score < threshold)
        ).count()
        
        return {
            "total": total,
            "high": high_risk,
            "medium": med_risk,
            "low": total - high_risk - med_risk,
            "system_trust": round(1.0 - (high_risk / (total or 1)), 2)
        }

    def get_top_merchants(self, limit: int) -> List[Dict[str, Any]]:
        """Rank merchants by risk and volume."""
        from app.db.models import MerchantProfile
        results = self.db.query(
            Transaction.merchant,
            func.count(Transaction.id).label("count"),
            func.avg(Transaction.final_risk_score).label("avg_risk")
        ).group_by(Transaction.merchant).order_by(desc("avg_risk")).limit(limit).all()
        
        return [
            {"name": r.merchant, "count": r.count, "risk": round(float(r.avg_risk), 3)}
            for r in results
        ]

    def get_forensic_summary(self) -> Dict[str, Any]:
        """Summary metrics for forensics dashboard."""
        return {
            "total_cases": self.db.query(InvestigationCase).count(),
            "active_investigations": self.db.query(InvestigationCase).filter(InvestigationCase.status == "INVESTIGATING").count(),
            "avg_resolution_time_hrs": 2.4, # Mocked or calculated
            "unassigned_cases": self.db.query(InvestigationCase).filter(InvestigationCase.analyst_id.is_(None)).count()
        }

    def get_filtered_transactions(self, 
                                  start_time: Optional[datetime] = None, 
                                  username: Optional[str] = None,
                                  min_amount: Optional[float] = None,
                                  max_amount: Optional[float] = None) -> List[Transaction]:
        """Fetches transactions with flexible filters for reporting."""
        query = self.db.query(Transaction, User.username).join(User, Transaction.user_id == User.id)
        
        if start_time:
            query = query.filter(Transaction.timestamp >= start_time)
        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
            
        results = query.order_by(Transaction.timestamp.desc()).all()
        
        # Attach username attribute back to transaction objects for the service
        txs = []
        for tx, uname in results:
            tx.username = uname
            txs.append(tx)
        return txs
