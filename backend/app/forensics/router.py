from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from typing import List, Dict, Any
from datetime import datetime

from app.core.dependencies import get_db, require_analyst
from app.db.models import Transaction, AuditLog, User, UserBehaviorProfile, MerchantProfile, FeedbackRecord
from app.realtime.websocket import manager

router = APIRouter()

@router.get("/story/{tx_id}")
def get_transaction_story(
    tx_id: int,
    db: Session = Depends(get_db),
    analyst=Depends(require_analyst)
):
    """
    Aggregates a complete forensic timeline for a transaction.
    - User behavioral baseline
    - Recent history
    - Network links (shared devices, IPs)
    - Audit decision path
    """
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    user = db.query(User).filter(User.id == tx.user_id).first()
    profile = db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == tx.user_id).first()
    
    # 1. Historical Context (Last 5 transactions before this one)
    history = db.query(Transaction).filter(
        and_(
            Transaction.user_id == tx.user_id,
            Transaction.timestamp < tx.timestamp
        )
    ).order_by(desc(Transaction.timestamp)).limit(5).all()

    # 2. Network Links (Other users sharing this device or IP)
    linked_users_count = db.query(User).join(Transaction, User.id == Transaction.user_id).filter(
        and_(
            Transaction.user_id != tx.user_id,
            or_(
                Transaction.device_id == tx.device_id,
                Transaction.ip_address == tx.ip_address
            )
        )
    ).distinct().count()

    # 3. Audit Path
    audit = db.query(AuditLog).filter(AuditLog.tx_id == tx.id).first()

    # 4. Risk History (Last 30 transactions)
    risk_history = db.query(
        Transaction.timestamp,
        Transaction.final_risk_score
    ).filter(Transaction.user_id == tx.user_id).order_by(Transaction.timestamp.desc()).limit(30).all()

    # 5. Peer Comparison (Cohorts)
    global_avg_risk = db.query(func.avg(Transaction.final_risk_score)).filter(Transaction.status == "APPROVED").scalar() or 0.15
    global_avg_amount = db.query(func.avg(Transaction.amount)).filter(Transaction.status == "APPROVED").scalar() or 500.0

    return {
        "transaction": {
            "id": tx.id,
            "amount": tx.amount,
            "merchant": tx.merchant,
            "status": tx.status,
            "risk_score": tx.final_risk_score,
            "timestamp": tx.timestamp.isoformat(),
            "location": tx.location,
            "device_id": tx.device_id,
            "ip_address": tx.ip_address
        },
        "user_context": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "member_since": user.created_at.isoformat(),
            "avg_spend": float(profile.avg_amount) if profile else 0,
            "total_tx": profile.total_tx_count if profile else 0
        },
        "forensics": {
            "historical_timeline": [
                {
                    "id": h.id,
                    "amount": h.amount,
                    "status": h.status,
                    "timestamp": h.timestamp.isoformat()
                } for h in history
            ],
            "risk_history": [
                {"date": r[0].isoformat(), "score": round(float(r[1] or 0), 4)}
                for r in sorted(risk_history, key=lambda x: x[0])
            ],
            "peer_comparison": {
                "user_avg_risk": round(float(profile.avg_amount/1000) if profile and profile.avg_amount else 0.1, 2), # Normalized proxy
                "global_avg_risk": round(float(global_avg_risk), 2),
                "user_avg_amount": round(float(profile.avg_amount) if profile else 0, 2),
                "global_avg_amount": round(float(global_avg_amount), 2)
            },
            "network_risk": {
                "shared_infrastructure_users": linked_users_count,
                "risk_level": "HIGH" if linked_users_count > 3 else ("MEDIUM" if linked_users_count > 0 else "LOW")
            },
            "audit_trail": {
                "auto_decision": audit.auto_decision if audit else "UNKNOWN",
                "explanation": audit.explanation if audit else "No audit log found.",
                "flags": audit.rule_flags if audit else []
            }
        }
    }

@router.post("/accounts/freeze/{user_id}")
async def freeze_account(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_analyst)
):
    """Admin action: Freeze a user account to prevent further transactions."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    db.commit()
    
    # Log this action for regulatory compliance
    if user.id:
        audit = AuditLog(
            tx_id=None,
            analyst_id=admin.id,
            analyst_action="ACCOUNT_FROZEN",
            analyst_notes=f"User account {user.email} (ID: {user_id}) manually frozen by forensic analyst.",
            timestamp=datetime.utcnow(),
            # Required schema fields (Mapping administrative action to Audit structure)
            model_version="admin_v2",
            threshold_config={"action": "manual_freeze"},
            auto_decision="MEMBER_ACTION",
            final_decision="ACCOUNT_FROZEN",
            explanation=f"Administrative account freeze triggered by {admin.username}.",
            explanation_model="forensic_ops",
            final_risk_score=1.0,
            ae_score=1.0,
            if_score=1.0,
            gnn_score=1.0
        )
        db.add(audit)
        db.commit()
    
    return {"message": f"Account {user.email} frozen successfully", "status": "frozen", "user_id": user_id}

@router.post("/transactions/override/{tx_id}")
async def override_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_analyst)
):
    """Analyst action: Manually override a blocked transaction."""
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx.status = "APPROVED"
    tx.decision = "APPROVED"
    tx.explanation = "Manually approved by forensic analyst after investigation."
    tx.reviewed_by = admin.id
    db.commit()

    # Broadcast update to all listeners
    await manager.broadcast_transaction_event(tx, event_type="TRANSACTION_UPDATED")

    return {"message": "Transaction override successful", "status": "APPROVED"}

@router.post("/actions/escalate-legal/{tx_id}")
async def escalate_to_legal(
    tx_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_analyst)
):
    """Escalate transaction to legal/compliance team."""
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx.status = "UNDER_REVIEW"
    tx.decision = "ESCALATED"
    tx.explanation = "Case escalated to compliance and legal team for deep verification."
    db.commit()

    # Broadcast update to all listeners
    await manager.broadcast_transaction_event(tx, event_type="TRANSACTION_UPDATED")

    return {"message": "Escalated to legal", "status": "UNDER_REVIEW"}

@router.post("/feedback/{tx_id}/false-positive")
async def mark_false_positive(
    tx_id: int,
    db: Session = Depends(get_db),
    analyst=Depends(require_analyst)
):
    """Analyst action: Mark a transaction as a false positive (incorrectly flagged/blocked)."""
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Get the audit log for this transaction
    audit = db.query(AuditLog).filter(AuditLog.tx_id == tx_id).order_by(AuditLog.timestamp.desc()).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found for this transaction")
    
    # Update transaction status to APPROVED
    tx.status = "APPROVED"
    tx.decision = "APPROVED"
    tx.explanation = "Marked as false positive by forensic analyst - system decision was incorrect."
    tx.reviewed_by = analyst.id
    db.commit()
    
    # Record feedback for model retraining
    if audit.auto_decision in ["FLAGGED", "BLOCKED"]:
        feedback = FeedbackRecord(
            tx_id=tx_id,
            audit_id=audit.id,
            original_decision=audit.auto_decision,
            corrected_decision="APPROVED",
            features=audit.input_features,
            feedback_type="false_positive",
            analyst_id=analyst.id,
            timestamp=datetime.utcnow(),
            used_for_retraining=False
        )
        db.add(feedback)
        db.commit()
    
    # Broadcast update to all listeners
    await manager.broadcast_transaction_event(tx, event_type="TRANSACTION_UPDATED")
    
    return {
        "message": "Transaction marked as false positive successfully",
        "transaction_id": tx_id,
        "status": "APPROVED",
        "feedback_recorded": True
    }
