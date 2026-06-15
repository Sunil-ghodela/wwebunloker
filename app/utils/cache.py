import json
import logging
from typing import Any

import redis

from app.config import get_settings


logger = logging.getLogger(__name__)


class RedisCache:
    """Small Redis cache wrapper that fails open when Redis is unavailable."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ttl_seconds = settings.cache_ttl_seconds
        self.client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    def get(self, key: str) -> dict[str, Any] | None:
        """Return a cached JSON object, or None on miss/unavailable Redis."""

        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except (redis.RedisError, json.JSONDecodeError) as exc:
            logger.warning("Redis cache read failed: %s", exc)
            return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store a JSON object in Redis without breaking requests on failure."""

        try:
            self.client.setex(key, self.ttl_seconds, json.dumps(value))
        except redis.RedisError as exc:
            logger.warning("Redis cache write failed: %s", exc)


cache = RedisCache()
