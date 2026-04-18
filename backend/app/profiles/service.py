import math
import logging
import statistics
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import UserBehaviorProfile, Transaction, User
from app.profiles.repository import ProfilesRepository
from app.ml.velocity import velocity_1h, velocity_24h, track_all_windows
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)

# TTL for cached baselines (seconds). Short enough to stay fresh, long enough to
# absorb burst traffic from bulk injection / live transactions.
_BASELINE_CACHE_TTL = 30

class ProfileService:
    """
    Service for managing user behavioral profiles.
    Supports incremental updates (online learning) and statistical analysis.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProfilesRepository(db)
    
    def get_or_create_profile(self, user_id: int) -> UserBehaviorProfile:
        profile = self.repo.get_profile_by_user_id(user_id)
        if not profile:
            profile = self.repo.create_profile(user_id)
        return profile
    
    def update_profile(self, user_id: int, tx: Transaction, profile: Optional[UserBehaviorProfile] = None) -> UserBehaviorProfile:
        """Incrementally update user profile after a transaction."""
        if not profile:
            profile = self.get_or_create_profile(user_id)
        
        n = profile.total_tx_count
        old_avg = profile.avg_amount
        old_m2 = profile._m2 or 0.0
        
        n += 1
        
        # Outlier Protection
        effective_amount = tx.amount
        if n > 5 and old_avg > 100 and tx.amount > (old_avg * 100):
            effective_amount = old_avg * 100

        # Welford's online algorithm
        delta = effective_amount - old_avg
        new_avg = old_avg + delta / n
        new_avg = min(new_avg, 1_000_000_000.0)
        
        delta2 = effective_amount - new_avg
        new_m2 = old_m2 + delta * delta2
        new_m2 = min(new_m2, 1e18) 
        
        update_data = {
            "total_tx_count": n,
            "avg_amount": new_avg,
            "_m2": new_m2,
            "std_amount": math.sqrt(new_m2 / (n - 1)) if n > 1 else 0.0,
            "last_updated": datetime.utcnow(),
            "last_tx_timestamp": tx.timestamp
        }
        
        if profile.first_tx_date is None:
            update_data["first_tx_date"] = tx.timestamp
            
        if profile.min_amount is None or tx.amount < profile.min_amount:
            update_data["min_amount"] = tx.amount
        if profile.max_amount is None or tx.amount > profile.max_amount:
            update_data["max_amount"] = tx.amount

        # Update ratios & patterns
        self._calculate_patterns(profile, tx, update_data)
        
        # Sync velocity (Redis)
        track_all_windows(user_id, str(tx.id), tx.amount, tx.timestamp.timestamp())
        
        # Save updates
        profile = self.repo.update_profile(profile, update_data)
        
        # Clear Cache
        cache_manager.delete(f"profile:user:{user_id}")
        return profile

    def get_detailed_profile(self, user_id: int) -> Dict[str, Any]:
        """Collects full profile with recent activity stats."""
        profile = self.get_or_create_profile(user_id)
        
        # Get recent transaction stats (Last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent_txs = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.timestamp >= cutoff
        ).all()
        
        flagged_count = sum(1 for tx in recent_txs if tx.decision in ["FLAGGED", "BLOCKED"])
        
        return {
            "profile": {
                "avg_amount": round(profile.avg_amount, 2),
                "std_amount": round(profile.std_amount, 2),
                "tx_count": profile.total_tx_count,
                "tx_per_day": round(profile.tx_per_day or 0.0, 2),
                "night_tx_ratio": round(profile.night_tx_ratio or 0.0, 4),
                "geo_entropy": round(profile.geo_entropy or 0.0, 4),
                "merchant_category_dist": profile.merchant_category_distribution,
                "last_updated": profile.last_updated.isoformat()
            },
            "recent_activity": {
                "transactions_30d": len(recent_txs),
                "flagged_30d": flagged_count,
                "fraud_rate_30d": round(flagged_count / len(recent_txs), 4) if recent_txs else 0.0
            }
        }

    def get_user_statistics(self, user_id: int, days: int = 90) -> Dict[str, Any]:
        """Deep statistical analysis of user behavior."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.timestamp >= cutoff
        ).all()
        
        if not transactions:
            return {"message": "No transactions in analysis period", "period_days": days}
        
        amounts = [tx.amount for tx in transactions]
        risk_scores = [tx.final_risk_score for tx in transactions]
        
        return {
            "spending_stats": {
                "total": round(sum(amounts), 2),
                "avg": round(statistics.mean(amounts), 2),
                "median": round(statistics.median(amounts), 2),
                "std": round(statistics.stdev(amounts), 2) if len(amounts) > 1 else 0.0,
                "max": round(max(amounts), 2),
                "count": len(transactions)
            },
            "risk_stats": {
                "avg_risk": round(statistics.mean(risk_scores), 4),
                "flagged": sum(1 for tx in transactions if tx.decision == "FLAGGED"),
                "blocked": sum(1 for tx in transactions if tx.decision == "BLOCKED")
            }
        }

    def get_drift_alerts(self, threshold: float = 3.0) -> List[Dict[str, Any]]:
        """Detects significant deviations from established baselines."""
        profiles = self.repo.get_all_profiles()
        alerts = []
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        for p in profiles:
            recent_txs = self.db.query(Transaction).filter(
                Transaction.user_id == p.user_id,
                Transaction.timestamp >= cutoff
            ).all()
            
            if len(recent_txs) < 5 or p.std_amount == 0:
                continue
                
            recent_avg = sum(tx.amount for tx in recent_txs) / len(recent_txs)
            z_score = abs(recent_avg - p.avg_amount) / p.std_amount
            
            if z_score >= threshold:
                alerts.append({
                    "user_id": p.user_id,
                    "baseline_avg": round(p.avg_amount, 2),
                    "recent_avg": round(recent_avg, 2),
                    "z_score": round(z_score, 2),
                    "tx_count": len(recent_txs)
                })
        return sorted(alerts, key=lambda x: x["z_score"], reverse=True)

    def reset_profile(self, user_id: int) -> UserBehaviorProfile:
        """Wipes and re-initializes a user profile."""
        profile = self.repo.get_profile_by_user_id(user_id)
        if profile:
            self.repo.delete_profile(profile)
        return self.get_or_create_profile(user_id)

    # --- Internal Helpers ---

    def _calculate_patterns(self, profile, tx, update_data):
        """Helper to calculate ratios and distributions."""
        # Time
        hour = tx.timestamp.hour
        is_night = hour >= 22 or hour < 6
        is_weekend = tx.timestamp.weekday() >= 5
        
        night_count = (profile.night_tx_count or 0) + (1 if is_night else 0)
        weekend_count = (profile.weekend_tx_count or 0) + (1 if is_weekend else 0)
        total = profile.total_tx_count + 1
        
        update_data.update({
            "night_tx_count": night_count,
            "weekend_tx_count": weekend_count,
            "night_tx_ratio": night_count / total,
            "weekend_tx_ratio": weekend_count / total
        })

        # Locations (Top 20)
        if tx.location:
            locs = profile.top_locations or {}
            locs[tx.location] = locs.get(tx.location, 0) + 1
            if len(locs) > 20:
                locs = dict(sorted(locs.items(), key=lambda x: x[1], reverse=True)[:20])
            update_data["top_locations"] = locs
            
            # Entropy
            t_loc = sum(locs.values())
            entropy = sum(-(c/t_loc) * math.log2(c/t_loc) for c in locs.values() if c > 0)
            update_data["geo_entropy"] = entropy

    def get_baseline(self, user_id: int) -> Dict[str, Any]:
        """Baseline retrieval for ML pipeline — Redis-cached for burst performance."""
        cache_key = f"profile:user:{user_id}"

        # 1. Try Redis first (avoids a Postgres round-trip on every transaction)
        try:
            cached = cache_manager.get_json(cache_key)
            if cached:
                logger.debug(f"PROFILE CACHE HIT: user:{user_id}")
                return cached
        except Exception as e:
            logger.warning(f"Profile cache read failed for user {user_id}: {e}")

        # 2. Cache miss — build from DB
        profile = self.get_or_create_profile(user_id)
        if profile.total_tx_count == 0:
            return self._global_fallback()

        v1h_c, v1h_a = velocity_1h.get_velocity(user_id)
        v24h_c, v24h_a = velocity_24h.get_velocity(user_id)

        baseline = {
            "avg_amount": profile.avg_amount,
            "std_amount": profile.std_amount,
            "total_tx_count": profile.total_tx_count,
            "profile_maturity": profile.profile_maturity,
            "velocity": {
                "tx_1h": v1h_c, "amt_1h": v1h_a,
                "tx_24h": v24h_c, "amt_24h": v24h_a
            }
        }

        # 3. Write into Redis with short TTL to absorb future burst
        try:
            cache_manager.set_json(cache_key, baseline, ttl=_BASELINE_CACHE_TTL)
        except Exception as e:
            logger.warning(f"Profile cache write failed for user {user_id}: {e}")

        return baseline

    def _global_fallback(self) -> Dict[str, Any]:
        return {
            "avg_amount": 5000.0, "std_amount": 10000.0,
            "total_tx_count": 0, "profile_maturity": "new",
            "velocity": {"tx_1h": 0, "amt_1h": 0, "tx_24h": 0, "amt_24h": 0}
        }
