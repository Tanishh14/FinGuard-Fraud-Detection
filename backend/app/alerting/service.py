import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Transaction, TransactionStatus
from app.realtime.websocket import manager

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self):
        self.alert_threshold = 0.85 # Default threshold

    async def check_and_trigger_alert(self, tx: Transaction, db: Session):
        """
        Check if a transaction risk score exceeds the threshold and trigger alerts.
        """
        if tx.final_risk_score >= self.alert_threshold:
            logger.warning(f"🚨 CRITICAL ALERT: High-risk transaction detected! TXN-{tx.id}, Risk: {tx.final_risk_score}")
            
            alert_payload = {
                "type": "FRAUD_ALERT",
                "transaction_id": tx.id,
                "amount": tx.amount,
                "merchant": tx.merchant,
                "risk_score": tx.final_risk_score,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Critical risk detected: {round(tx.final_risk_score * 100, 1)}% for ₹{tx.amount} at {tx.merchant}"
            }

            # 1. Broadcast via WebSocket for real-time UI notifications
            try:
                await manager.broadcast_json(alert_payload)
                logger.info(f"   ✓ Alert broadcasted via WebSocket for TXN-{tx.id}")
            except Exception as e:
                logger.error(f"   ❌ Failed to broadcast alert: {e}")

            # 2. Simulate Email/SMS (Logging for now)
            logger.info(f"   [Simulated SMS/Email] To Admin: Critical Fraud Alert for TXN-{tx.id}")

            return True
        return False

alert_service = AlertService()
