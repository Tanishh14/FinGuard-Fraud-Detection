import time
from typing import Dict, Any, Tuple, Optional
import logging

from app.core.cache import cache_manager

logger = logging.getLogger(__name__)

class VelocityTracker:
    """
    Redis-backed velocity tracking using Sorted Sets (ZSET).
    This tracks the number and amount of transactions in a sliding window.
    """
    
    def __init__(self, key_prefix: str, window_seconds: int = 3600):
        self.key_prefix = key_prefix
        self.window_seconds = window_seconds

    def _get_key(self, user_id: int) -> str:
        return f"velocity:{self.key_prefix}:user:{user_id}"

    def track_transaction(self, user_id: int, tx_id: str, amount: float, timestamp: Optional[float] = None) -> None:
        """
        Record a new transaction in the user's velocity sliding window.
        """
        if timestamp is None:
            timestamp = time.time()
            
        key = self._get_key(user_id)
        
        # We store the amount as the member value with tx_id to keep it unique,
        # e.g., "tx_id:amount" so we can parse it if we need to aggregate amounts.
        member = f"{tx_id}:{amount}"
        
        # O(log N) insertion
        cache_manager.zadd(key, {member: timestamp})
        
        # Immediately evict old items
        min_score = 0
        max_score = timestamp - self.window_seconds
        cache_manager.zremrangebyscore(key, min_score, max_score)
        
        # Set expiry on the whole set so inactive users don't bloat Redis
        cache_manager.expire(key, self.window_seconds * 2)

    def get_velocity(self, user_id: int, current_time: Optional[float] = None) -> Tuple[int, float]:
        """
        Get the transaction count and total amount in the current sliding window.
        """
        if current_time is None:
            current_time = time.time()
            
        key = self._get_key(user_id)
        
        # Clean up old entries first
        min_score = 0
        max_score = current_time - self.window_seconds
        cache_manager.zremrangebyscore(key, min_score, max_score)
        
        # Get count
        count = cache_manager.zcard(key) or 0
        
        total_amount = 0.0
        # If we need the total amount, we have to fetch the members.
        # This can be slightly expensive if count is huge, but for typical
        # hourly velocity, it's very fast.
        if count > 0 and cache_manager.is_connected:
            try:
                # ZRANGE is standard. By default, withscores=False in redis-py unless specified.
                members = cache_manager.client.zrange(key, 0, -1)
                for m in members:
                    try:
                        parts = m.split(":", 1)
                        if len(parts) == 2:
                            total_amount += float(parts[1])
                    except ValueError:
                        pass
            except Exception as e:
                logger.error(f"Failed to fetch members for velocity key {key}: {e}")
                
        return count, total_amount

# Global trackers for typical windows
velocity_1h = VelocityTracker("1h", 3600)
velocity_24h = VelocityTracker("24h", 86400)

def track_all_windows(user_id: int, tx_id: str, amount: float, timestamp: Optional[float] = None):
    """Convenience to track transaction in all windows"""
    velocity_1h.track_transaction(user_id, tx_id, amount, timestamp)
    velocity_24h.track_transaction(user_id, tx_id, amount, timestamp)

