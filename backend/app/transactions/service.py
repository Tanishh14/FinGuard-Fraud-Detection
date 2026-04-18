import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import Transaction, TransactionStatus, MerchantProfile, User, UserOTP
from app.transactions.repository import TransactionRepository
from app.auth.repository import AuthRepository # For OTP handling
from app.profiles.service import ProfileService
from app.audit.service import AuditService
from app.realtime.websocket import manager
from app.alerting.service import alert_service
from app.core.mail import mail_service
import secrets

logger = logging.getLogger(__name__)

class TransactionService:
    """
    Authoritative service for processing and scoring transactions.
    Integrated with ML models, behavioral profiling, and audit logs.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = TransactionRepository(db)
        self.auth_repo = AuthRepository(db)
        self.profile_service = ProfileService(db)
        self.audit_service = AuditService(db)

    async def process_transaction(self, payload: Dict[str, Any], current_user: User) -> Transaction:
        """
        Orchestrate the full transaction pipeline using the modernized ML stack.
        """
        # 1. Ensure Merchant Exists (Small biz logic, keep in service)
        if payload.get("merchant_id"):
            m_id = str(payload["merchant_id"])
            exists = self.db.query(MerchantProfile).filter(MerchantProfile.merchant_id == m_id).first()
            if not exists:
                try:
                    logger.info(f"Auto-creating missing merchant profile: {m_id}")
                    new_merchant = MerchantProfile(
                        merchant_id=m_id,
                        merchant_name=payload.get("merchant") or "Unknown Merchant",
                        category="uncategorized",
                        risk_level="normal" 
                    )
                    self.db.add(new_merchant)
                    self.db.commit()
                except Exception:
                    self.db.rollback()

        # 2. Basic Validation
        amount = float(payload.get("amount", 0.0))
        if amount <= 0:
            raise HTTPException(400, "Transaction amount must be greater than 0")
            
        payload["user_id"] = current_user.id

        tx_data = {
            "user_id": current_user.id,
            "amount": amount,
            "merchant": payload.get("merchant", "Unknown Merchant"),
            "merchant_id": payload.get("merchant_id", "M_GENERIC"),
            "recipient_name": payload.get("recipient_name"),
            "device_id": payload.get("device_id", "D_UNKNOWN"),
            "ip_address": payload.get("ip_address"),
            "location": payload.get("location"),
            "timestamp": datetime.utcnow(),
            "status": TransactionStatus.PENDING.value
        }
        
        tx = self.repo.create(tx_data)
        
        try:
            # 3. [EXPRESS LANE] Similarity Bypass Check (Redis-backed)
            # Check before heavy ML or DB profile lookups to minimize latency
            from app.ml.similarity.service import get_similarity_engine
            sim_engine = get_similarity_engine(self.db)
            similarity_result = sim_engine.check_similarity(payload)
            
            if similarity_result:
                # IMMEDIATE PERSISTENCE & RETURN
                update_data = {
                    "final_risk_score": similarity_result["final_risk"],
                    "status": getattr(TransactionStatus, similarity_result["decision"]).value,
                    "decision": similarity_result["decision"],
                    "explanation": similarity_result["decision_reason"],
                    "similarity_triggered": True,
                    "inherited_from_transaction_id": similarity_result.get("inherited_from_transaction_id"),
                    "scoring_latency_ms": similarity_result.get("latency_ms", 1.5),
                    "intelligence": similarity_result.get("intelligence")
                }
                tx = self.repo.update(tx, update_data)
                # Quick Notify
                await manager.broadcast_transaction_event(tx)
                return tx

            # 4. Standard ML Pipeline (Similarity Miss)
            from app.ml.scoring_pipeline import get_scoring_pipeline
            pipeline = get_scoring_pipeline()
            
            # Heavy operations: Profile lookup and ML inference
            baseline = self.profile_service.get_baseline(current_user.id)
            
            # Forensic Pattern Matching
            from app.db.models import Transaction as DBTransaction
            # DIAGNOSTIC: Check if self.db is corrupted
            if not hasattr(self.db, "query"):
                logger.error(f"DB CORRUPTION DETECTED: self.db is {type(self.db)}: {self.db}")
            
            last_txs = self.db.query(DBTransaction).filter(DBTransaction.user_id == current_user.id).order_by(DBTransaction.id.desc()).limit(5).all()
            last_amt = last_txs[0].amount if last_txs else 0.0
            same_amt_count = sum(1 for t in last_txs if abs(t.amount - amount) < 0.01)

            scoring_result = await asyncio.to_thread(
                pipeline.score_transaction,
                self.db,
                {
                    **payload,
                    "user_id": current_user.id,
                    "last_tx_amount": last_amt,
                    "same_amount_count": same_amt_count,
                    "device_id": payload.get("device_id", "unknown"),
                    "amount_z_score": (amount - baseline["avg_amount"]) / max(baseline["std_amount"], 1e-9)
                },
                baseline
            )
            
            # 4. Update with ML Results
            update_data = {
                "final_risk_score": scoring_result["final_risk"],
                "ae_score": scoring_result.get("ae_score", 0.0),
                "if_score": scoring_result.get("if_score", 0.0),
                "gnn_score": scoring_result.get("gnn_score", 0.0),
                "similarity_triggered": scoring_result.get("similarity_triggered", False),
                "inherited_from_transaction_id": scoring_result.get("inherited_from_transaction_id")
            }
            
            # 5. [COMPLIANCE] MFA Gate (Soft-Flag only — hard block removed to not override AI)
            # Only flag as advisory for very high-value transactions without 2FA
            mfa_advisory = not current_user.is_2fa_enabled and amount > 50000

            # 6. Set Decision — map pipeline strings to DB enum values
            decision = scoring_result["decision"]  # APPROVED / REVIEW / BLOCKED / PENDING
            if decision in ["PENDING", "REVIEW_NEEDED"]:
                decision = "APPROVED"

            # MFA advisory override for very high-value txs without 2FA
            if mfa_advisory and decision == "APPROVED":
                decision = "REVIEW"

            if decision == "REVIEW":
                update_data["status"] = TransactionStatus.REVIEW.value
                update_data["decision"] = "REVIEW"
            elif decision == "BLOCKED":
                update_data["status"] = TransactionStatus.BLOCKED.value
                update_data["decision"] = "BLOCKED"
            else:
                # APPROVED (includes FLAGGED — allowed through)
                update_data["status"] = TransactionStatus.APPROVED.value
                update_data["decision"] = "APPROVED"

            update_data["risk_score"] = update_data["final_risk_score"]
            update_data["explanation"] = scoring_result["decision_reason"]

            # Enrich intelligence with ALL model signals for forensic investigation panel
            base_intelligence = scoring_result.get("intelligence", {})
            base_intelligence["breakdown"] = {
                "GNN (Graph Network)": scoring_result.get("gnn_score", 0.0),
                "Anomaly (Autoencoder)": scoring_result.get("ae_score", 0.0),
                "Isolation Forest": scoring_result.get("if_score", 0.0),
                "Behavioral Rules": round(scoring_result.get("model_contributions", {}).get("rules", 0.0), 4),
                "Calibrated FRS": scoring_result.get("final_risk", 0.0),
                "Model Confidence": scoring_result.get("confidence", 0.0),
            }
            base_intelligence["labels"] = [
                f"TRACK: {scoring_result.get('track', 'PROBATIONARY')}",
                f"FRS: {scoring_result.get('final_risk', 0.0)*100:.1f}%",
                f"CONFIDENCE: {scoring_result.get('confidence', 0.0):.2f}",
                f"LATENCY: {scoring_result.get('latency_ms', 0):.1f}ms",
                f"GATE: {scoring_result.get('gate_status', 'N/A')}",
            ]
            update_data["intelligence"] = base_intelligence
            update_data["scoring_latency_ms"] = scoring_result.get("latency_ms", 0)
            
            tx = self.repo.update(tx, update_data)
            
            # 7. Post-processing
            profile_obj = self.profile_service.get_or_create_profile(current_user.id)
            await self._run_post_processing(current_user, tx, profile_obj, scoring_result)
            
            return tx
            
        except Exception as e:
            logger.error(f"Error in transaction pipeline: {e}")
            return self.repo.update(tx, {
                "status": TransactionStatus.REVIEW.value,
                "explanation": f"ML System Stability Fallback: {str(e)}",
                "final_risk_score": 0.5
            })

    def get_transaction_count(self, user: User, filters: Dict[str, Any]) -> int:
        user_id = user.id if user.role not in ["admin", "fraud_analyst"] else None
        return self.repo.get_count(user_id=user_id, filters=filters)

    def get_all_transactions(self, user: User, filters: Dict[str, Any], page: int, page_size: int) -> List[Transaction]:
        user_id = user.id if user.role not in ["admin", "fraud_analyst"] else None
        return self.repo.get_all(user_id=user_id, filters=filters, page=page, page_size=page_size)

    async def override_transaction(self, tx_id: int, status: str, reviewer_id: int) -> Transaction:
        tx = self.repo.get_by_id(tx_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        
        tx = self.repo.update(tx, {
            "status": status,
            "decision": status,
            "reviewed_by": reviewer_id,
            "reviewed_at": datetime.utcnow()
        })
        
        await manager.broadcast_transaction_event(tx, event_type="TRANSACTION_UPDATED")
        return tx

    def verify_transaction_mfa(self, tx_id: int, user_id: int) -> Transaction:
        tx = self.repo.get_by_id(tx_id)
        if not tx or tx.user_id != user_id:
            raise HTTPException(403, "Access denied")
        
        if tx.status != "FLAGGED":
            raise HTTPException(400, "Only flagged transactions can be verified")
            
        return self.repo.update(tx, {
            "status": "APPROVED",
            "decision": "APPROVED",
            "explanation": "Transaction verified by user via MFA."
        })

    def initiate_otp_flow(self, tx_id: int, user: User, flow_type: str, reason: str, urgency: str) -> Dict[str, str]:
        """Generic OTP flow for appeals/reports."""
        tx = self.repo.get_by_id(tx_id)
        if not tx or tx.user_id != user.id:
            raise HTTPException(403, "Access denied")
            
        otp_code = "".join(secrets.choice("0123456789") for _ in range(6))
        
        self.auth_repo.create_otp({
            "email": user.email,
            "otp_code": otp_code,
            "otp_type": flow_type,
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
            "reference_id": json.dumps({
                "tx_id": tx_id,
                "reason": reason,
                "urgency": urgency,
                "type": flow_type
            })
        })

        mail_service.send_otp_email(user.email, otp_code, f"Transaction {flow_type.capitalize()}")
        return {"message": f"OTP sent for {flow_type}. Please verify to proceed."}

    async def verify_and_finalize_otp(self, email: str, otp_code: str, otp_type: str) -> Transaction:
        """Verifies OTP and applies the appeal/report to the transaction."""
        otp_types = ["appeal", "report"] if otp_type in ["appeal", "report"] else [otp_type]
        otp = self.auth_repo.get_active_otp(email, otp_type) # This might need repo update or just use what we have
        
        if not otp or otp.otp_type not in otp_types:
            raise HTTPException(401, "Invalid or expired code")

        if otp.otp_code != otp_code:
            self.auth_repo.increment_otp_attempts(otp)
            raise HTTPException(401, "Invalid verification code")

        self.auth_repo.mark_otp_as_used(otp)
        data = json.loads(otp.reference_id)
        
        tx = self.repo.get_by_id(data["tx_id"])
        if not tx:
            raise HTTPException(404, "Transaction not found")
            
        tx = self.repo.update(tx, {
            "status": "UNDER_REVIEW",
            "is_appealed": True,
            "appeal_reason": data["reason"],
            "appeal_urgency": data["urgency"],
            "appeal_timestamp": datetime.utcnow()
        })
        
        await manager.broadcast_transaction_event(tx, event_type="TRANSACTION_UPDATED")
        return tx

    async def _run_post_processing(self, user, tx, profile_obj, results):
        """Internal helper for secondary tasks."""
        try:
            self.profile_service.update_profile(user.id, tx, profile=profile_obj)
            self.audit_service.create_audit_entry(tx, results, tx.explanation)
            await manager.broadcast_transaction_event(tx)
            await alert_service.check_and_trigger_alert(tx, self.db)
            
            if tx.status in ["APPROVED", "BLOCKED"]:
                mail_service.send_transaction_alert(user.email, {
                    "id": tx.id, "amount": tx.amount, "merchant": tx.merchant,
                    "currency": tx.currency, "timestamp": tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": tx.status
                }, is_blocked=(tx.status == "BLOCKED"))

            # --- Hardening: Compliance SAR Drafting Assistant ---
            # Automatically draft for BLOCKED or High-Risk REVIEW (>0.8)
            if tx.status == "BLOCKED" or (tx.status == "UNDER_REVIEW" and results.get("final_risk", 0) > 0.8):
                try:
                    sar_reason = results.get("decision_reason", "High-risk neural anomaly.")
                    self.repo.create_sar_draft(user.id, tx.id, sar_reason)
                    logger.info(f"SAR Drafted for transaction {tx.id}")
                except Exception as e:
                    logger.warning(f"SAR Drafting failed for {tx.id}: {e}")
                
            if not tx.similarity_triggered:
                from app.ml.similarity.service import get_similarity_engine
                get_similarity_engine(self.db).save_fingerprint(tx)
        except Exception as e:
            logger.error(f"Post-processing failed for {tx.id}: {e}")
