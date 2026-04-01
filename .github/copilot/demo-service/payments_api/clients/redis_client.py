"""
Redis Cache Client
Connects to Redis Cache - Payments service
"""
import redis
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self):
        self._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return self._client.get(key)
        except redis.RedisError as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            raise

    def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        try:
            return self._client.setex(key, ttl, value)
        except redis.RedisError as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            raise

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return self._client.delete(key) > 0
        except redis.RedisError as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            raise

    def get_account_balance(self, account_id: str) -> Optional[float]:
        """Get cached account balance."""
        value = self.get(f"balance:{account_id}")
        return float(value) if value else None
