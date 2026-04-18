import logging
import json
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Transaction, FeedbackRecord
from app.audit.repository import AuditRepository
from app.profiles.service import ProfileService

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for managing audit logs and regulatory compliance.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditRepository(db)
        self.profile_service = ProfileService(db)
    
    def create_audit_entry(self, tx: Transaction, scoring_result: Dict[str, Any], explanation: str, explanation_model: str = "llama3") -> AuditLog:
        """Create immutable audit log entry for a transaction."""
        user_profile_snapshot = self.profile_service.get_baseline(tx.user_id) # Using get_baseline for snapshot
        
        audit_data = {
            "tx_id": tx.id,
            "timestamp": datetime.utcnow(),
            "input_features": self._extract_audit_features(tx),
            "user_profile_snapshot": user_profile_snapshot,
            "ae_score": scoring_result.get("ae_score", 0.0),
            "if_score": scoring_result.get("if_score", 0.0),
            "gnn_score": scoring_result.get("gnn_score", 0.0),
            "rule_flags": scoring_result.get("risk_flags", []),
            "final_risk_score": scoring_result.get("final_risk", 0.0),
            "model_version": scoring_result.get("model_version", "v1.0.0"),
            "threshold_config": scoring_result.get("threshold_config", {"flag": 0.5, "block": 0.8}),
            "auto_decision": scoring_result.get("decision", "PENDING"),
            "final_decision": scoring_result.get("decision", "PENDING"),
            "explanation": explanation,
            "explanation_model": explanation_model,
            "scoring_latency_ms": scoring_result.get("latency_ms")
        }
        
        return self.repo.create_audit_log(audit_data)
    
    def record_analyst_action(self, audit_id: int, analyst_id: int, action: str, notes: Optional[str] = None) -> AuditLog:
        """Record analyst's review action."""
        audit = self.repo.get_audit_by_id(audit_id)
        if not audit:
            raise ValueError(f"Audit log {audit_id} not found")
        
        updated_audit = self.repo.update_audit_log(audit, {
            "analyst_id": analyst_id,
            "analyst_action": action,
            "analyst_notes": notes,
            "analyst_action_time": datetime.utcnow(),
            "final_decision": action
        })
        
        # Feedback logic moved here
        self._record_feedback(updated_audit)
        return updated_audit
    
    def _record_feedback(self, audit: AuditLog):
        """Record feedback when analyst overrides auto decision."""
        if audit.analyst_action and audit.analyst_action != audit.auto_decision:
            feedback_type = "false_positive" if audit.auto_decision in ["FLAGGED", "BLOCKED"] and audit.analyst_action == "APPROVED" else "false_negative"
            
            self.repo.create_feedback_record({
                "tx_id": audit.tx_id,
                "audit_id": audit.id,
                "original_decision": audit.auto_decision,
                "corrected_decision": audit.analyst_action,
                "features": audit.input_features,
                "feedback_type": feedback_type,
                "analyst_id": audit.analyst_id,
                "timestamp": datetime.utcnow()
            })

    def get_transaction_audit_trail(self, tx_id: int) -> List[Dict[str, Any]]:
        """Get complete audit trail for a transaction."""
        audits = self.repo.get_transaction_audit_trail(tx_id)
        return [self._format_audit_entry(a) for a in audits]
    
    def get_pending_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transactions flagged for analyst review."""
        txs = self.repo.get_pending_reviews(limit)
        result = []
        for tx in txs:
            audit = self.repo.get_latest_audit_for_tx(tx.id)
            result.append({
                "tx_id": tx.id, "amount": tx.amount, "merchant": tx.merchant,
                "timestamp": tx.timestamp.isoformat(), "risk_score": tx.final_risk_score,
                "status": tx.status, "explanation": audit.explanation if audit else None,
                "audit_id": audit.id if audit else None
            })
        return result
    
    def export_audit_logs(self, start_date: datetime, end_date: datetime, format: str = "json") -> str:
        """Export audit logs for regulatory compliance."""
        audits = self.repo.get_audits_in_range(start_date, end_date)
        if format == "csv":
            return self._export_csv(audits)
        return json.dumps([self._format_audit_entry(a) for a in audits], indent=2)

    def get_model_performance_stats(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        """Calculate model performance statistics."""
        audits = self.repo.get_all_audits(start_date, end_date)
        if not audits:
             return {"total_transactions": 0}
             
        total = len(audits)
        auto_approved = sum(1 for a in audits if a.auto_decision == "APPROVED")
        false_pos = sum(1 for a in audits if a.auto_decision in ["FLAGGED", "BLOCKED"] and a.analyst_action == "APPROVED")
        
        return {
            "total_transactions": total,
            "auto_approved": auto_approved,
            "analyst_reviewed": sum(1 for a in audits if a.analyst_action),
            "false_positive_rate": round(false_pos / (total - auto_approved) * 100, 2) if (total - auto_approved) > 0 else 0
        }

    # --- Helpers ---

    def _extract_audit_features(self, tx: Transaction) -> Dict[str, Any]:
        return {
            "amount": tx.amount, "merchant": tx.merchant, "location": tx.location,
            "device_id": tx.device_id, "ip_address": tx.ip_address,
            "timestamp": tx.timestamp.isoformat() if tx.timestamp else None
        }

    def _format_audit_entry(self, a: AuditLog) -> Dict[str, Any]:
        return {
            "audit_id": a.id, "timestamp": a.timestamp.isoformat(),
            "scores": {"ae": a.ae_score, "if": a.if_score, "risk": a.final_risk_score},
            "auto_decision": a.auto_decision, "final_decision": a.final_decision,
            "explanation": a.explanation,
            "analyst": {"action": a.analyst_action, "notes": a.analyst_notes} if a.analyst_id else None
        }

    def _export_csv(self, audits: List[AuditLog]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["audit_id", "tx_id", "timestamp", "auto_decision", "final_decision", "risk_score"])
        for a in audits:
            writer.writerow([a.id, a.tx_id, a.timestamp.isoformat(), a.auto_decision, a.final_decision, a.final_risk_score])
        return output.getvalue()
