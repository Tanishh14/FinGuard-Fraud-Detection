"""
RAG Context Builder
-------------------
Responsible for preparing sanitized, structured context
for LLM explainability.

⚠️ No PII (email, IP, exact device ID) is exposed.
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from app.db.models import Transaction


def build_context(tx: Transaction, db: Session = None) -> dict:
    """
    Converts a Transaction ORM object into
    LLM-safe structured reasoning context.
    Includes citations from similar past cases if db session is provided.
    """

    context = {
        "transaction_features": {
            "amount": tx.amount,
            "merchant": tx.merchant,
            "location": tx.location,
            "timestamp": tx.timestamp.isoformat(),
        },
        "behavioral_features": {
            "average_user_spend": tx.avg_user_spend,
            "amount_deviation_ratio": (
                round(tx.amount / tx.avg_user_spend, 2)
                if tx.avg_user_spend and tx.avg_user_spend > 0
                else None
            ),
        },
        "model_outputs": {
            "risk_score": tx.risk_score,
            "ae_score": tx.ae_score,
            "if_score": tx.if_score,
            "gnn_score": tx.gnn_score,
            "decision": tx.status
        },
        "similar_cases": []
    }

    # Similarity Search (Basic Vector-less RAG)
    if db:
        # Find transactions with similar amount (±20%) and same status
        similar = db.query(Transaction).filter(
            and_(
                Transaction.id != tx.id,
                Transaction.status == tx.status,
                Transaction.amount.between(tx.amount * 0.8, tx.amount * 1.2)
            )
        ).order_by(desc(Transaction.timestamp)).limit(2).all()
        
        for s in similar:
            context["similar_cases"].append({
                "case_id": s.id,
                "amount": s.amount,
                "merchant": s.merchant,
                "risk_score": s.final_risk_score,
                "outcome": s.status
            })

    return context
