import redis
import logging
import json
from typing import Any, Optional, Dict, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Centralized caching abstraction for FinGuard.
    Provides fail-safe Redis interactions. If Redis is down, it fails open (returns None)
    so the system can gracefully fallback to Postgres/ML paths.
    """
    def __init__(self):
        self.redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        self.client = None
        self._connected = False
        self._connect()
        
    def _connect(self):
        """Initialize Redis connection."""
        try:
            self.client = redis.Redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_timeout=2.0,  # Fail fast to prevent locking up the API
                socket_connect_timeout=2.0
            )
            # Ping to verify connection
            self.client.ping()
            self._connected = True
            logger.info("CacheManager: Successfully connected to Redis.")
        except Exception as e:
            self._connected = False
            self.client = None
            logger.warning(f"CacheManager: Failed to connect to Redis. Running in degraded (no-cache) mode. Error: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get(self, key: str) -> Optional[str]:
        if not self._connected:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"CacheManager: GET failed for {key}: {e}")
            return None

    def get_json(self, key: str) -> Optional[Dict]:
        val = self.get(key)
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                logger.error(f"CacheManager: JSON decode failed for key {key}")
                return None
        return None

    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        if not self._connected:
            return False
        try:
            self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"CacheManager: SET failed for {key}: {e}")
            return False

    def set_json(self, key: str, value: Dict, ttl: int = 3600) -> bool:
        return self.set(key, json.dumps(value), ttl)

    def delete(self, key: str) -> bool:
        if not self._connected:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"CacheManager: DELETE failed for {key}: {e}")
            return False

    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        if not self._connected:
            return None
        try:
            val = self.client.incrby(key, amount)
            if ttl is not None and val == amount:
                # Set expiry only on first increment
                self.client.expire(key, ttl)
            return val
        except Exception as e:
            logger.error(f"CacheManager: INCR failed for {key}: {e}")
            return None

    # Sorted Set Operations for Velocity
    def zadd(self, key: str, mapping: Dict[str, float]) -> bool:
        """Add elements to a sorted set."""
        if not self._connected:
            return False
        try:
            self.client.zadd(key, mapping)
            return True
        except Exception as e:
            logger.error(f"CacheManager: ZADD failed for {key}: {e}")
            return False

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> Optional[int]:
        """Remove elements from a sorted set with scores between min and max."""
        if not self._connected:
            return None
        try:
            return self.client.zremrangebyscore(key, min_score, max_score)
        except Exception as e:
            logger.error(f"CacheManager: ZREMRANGEBYSCORE failed for {key}: {e}")
            return None

    def zcard(self, key: str) -> Optional[int]:
        """Get the number of elements in a sorted set."""
        if not self._connected:
            return None
        try:
            return self.client.zcard(key)
        except Exception as e:
            logger.error(f"CacheManager: ZCARD failed for {key}: {e}")
            return None
            
    def expire(self, key: str, ttl: int) -> bool:
        if not self._connected:
            return False
        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"CacheManager: EXPIRE failed for {key}: {e}")
            return False

# Global instance for easy import
cache_manager = CacheManager()
