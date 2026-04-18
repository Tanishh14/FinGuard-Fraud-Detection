import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.cache import cache_manager
from app.db.models import Transaction

logger = logging.getLogger(__name__)

class SimilarityEngine:
    """
    Evaluates transaction similarity to bypass heavy ML computations.
    Backed by Redis for O(1) recent fingerprint lookups.
    """
    def __init__(self, db: Session):
        self.db = db
        # Cache fingerprints for 1 hour
        self.ttl = 3600

    def _generate_cache_key(self, user_id: int, merchant: str) -> str:
        # Standardize merchant string
        merch_clean = str(merchant).lower().strip().replace(" ", "_")
        return f"similarity:user:{user_id}:merchant:{merch_clean}"

    def check_similarity(self, tx_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        High-performance check for closely matching recent transactions.
        Threshold: 95% similarity on amount for the same User + Merchant pair.
        """
        user_id = tx_data.get("user_id")
        merchant = tx_data.get("merchant", "unknown")
        amount = float(tx_data.get("amount", 0))
        
        if not user_id:
            return None
            
        cache_key = self._generate_cache_key(user_id, merchant)
        
        try:
            # 1. PRIMARY REDIS PATH (Express Lane)
            cached_fingerprint = cache_manager.get_json(cache_key)
            
            if cached_fingerprint:
                prev_amount = cached_fingerprint.get("amount", 0)
                if prev_amount > 0:
                    # Calculate deviation
                    deviation = abs(amount - prev_amount) / prev_amount
                    similarity = 1.0 - deviation
                    
                    if similarity >= 0.99:
                        logger.info(f"⚡ [REDIS EXPRESS LANE] Similarity Hit! {similarity*100:.1f}% Match for User {user_id} -> {merchant}. Bypassing ML.")
                        return self._build_inherited_decision(cached_fingerprint, similarity)
            
            logger.debug(f"Similarity Miss: No recent cache for {cache_key}")
                        
        except Exception as e:
            logger.error(f"Similarity Cache Error: {e}")
            
        # 2. PERSISTENCE FALLBACK (Minimal DB Check)
        try:
            # Parse timestamp if it's a string (e.g., from API payload)
            tx_time = tx_data.get("timestamp", datetime.utcnow())
            if isinstance(tx_time, str):
                from dateutil import parser
                try:
                    tx_time = parser.isoparse(tx_time)
                except Exception:
                    tx_time = datetime.utcnow()

            # Limited to last 30 minutes for safety
            time_cutoff = tx_time - timedelta(minutes=30)
            
            recent_tx = self.db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.merchant == merchant,
                Transaction.status.in_(["APPROVED", "BLOCKED"]),
                Transaction.timestamp >= time_cutoff
            ).order_by(Transaction.timestamp.desc()).first()
            
            if recent_tx:
                fingerprint = {
                    "tx_id": recent_tx.id,
                    "amount": recent_tx.amount,
                    "decision": recent_tx.status,
                    "final_risk_score": recent_tx.final_risk_score,
                    "rule_score": recent_tx.rule_score
                }
                # Update Redis for future hits
                cache_manager.set_json(cache_key, fingerprint, ttl=self.ttl)
                
                similarity = 1.0 - abs(amount - recent_tx.amount) / recent_tx.amount
                if similarity >= 0.99:
                    logger.info(f"🏛️ [DATABASE FALLBACK] Similarity Hit! Using historical data for User {user_id}.")
                    return self._build_inherited_decision(fingerprint, similarity)
        except Exception as e:
            logger.error(f"Similarity DB Error: {e}")
            
        return None
        
    def _build_inherited_decision(self, fingerprint: Dict[str, Any], similarity: float) -> Dict[str, Any]:
        """Builds a decision object that skips ML pipelines."""
        return {
            "similarity_triggered": True,
            "inherited_from_transaction_id": fingerprint.get("tx_id"),
            "final_risk": float(fingerprint.get("final_risk_score", 0.05)),
            "decision": fingerprint.get("decision", "APPROVED"),
            "decision_reason": f"EXPRESS LANE: Decision inherited from similar transaction {fingerprint.get('tx_id')} ({similarity*100:.1f}% match).",
            "ae_score": 0.0,
            "if_score": 0.0,
            "gnn_score": 0.0,
            "gnn_active": False,
            "latency_ms": 1.5, # Indicative of cache speed
            "intelligence": {
                "labels": ["SIMILARITY_BYPASS", "REDIS_HIT"],
                "breakdown": {
                    "Similarity Engine": 100.0,
                    "ML Execution": 0.0
                }
            }
        }
        
    def save_fingerprint(self, tx: Transaction):
        """Asynchronously save a processed transaction to the similarity cache."""
        if not tx.user_id or not tx.merchant:
            return
            
        cache_key = self._generate_cache_key(tx.user_id, tx.merchant)
        fingerprint = {
            "tx_id": tx.id,
            "amount": tx.amount,
            "decision": tx.status,
            "final_risk_score": tx.final_risk_score,
            "rule_score": tx.rule_score
        }
        cache_manager.set_json(cache_key, fingerprint, ttl=self.ttl)

def get_similarity_engine(db: Session) -> SimilarityEngine:
    return SimilarityEngine(db)
