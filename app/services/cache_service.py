import json
import time
from typing import Any, Dict, List, Optional
import redis.asyncio as aioredis
from backend.app.config import settings
from backend.app.core.logging import logger


class InMemoryCache:
    """Thread-safe in-memory cache with TTL eviction for fallback."""
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["val"]

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        self._store[key] = {
            "val": value,
            "expires_at": time.time() + ttl_seconds
        }

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> int:
        keys_to_delete = [k for k in self._store.keys() if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    def flush(self) -> None:
        self._store.clear()


class CacheService:
    def __init__(self):
        self._redis_client: Optional[aioredis.Redis] = None
        self._in_memory = InMemoryCache()
        self._connected = False
        self._last_connection_attempt = 0.0
        self._connection_cooldown_seconds = 30.0

    async def get_redis(self) -> Optional[aioredis.Redis]:
        # Fast path for testing or if already connected
        if settings.ENVIRONMENT == "testing":
            return None

        if self._redis_client is not None and self._connected:
            return self._redis_client

        # Avoid repeated connection attempts when Redis is offline
        now = time.time()
        if now - self._last_connection_attempt < self._connection_cooldown_seconds:
            return None

        self._last_connection_attempt = now
        try:
            self._redis_client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            await self._redis_client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            return self._redis_client
        except Exception as e:
            logger.warning(f"Could not connect to Redis ({e}), using in-memory cache fallback.")
            self._redis_client = None
            self._connected = False
            return None

    # Key Builders
    @staticmethod
    def build_nearby_key(
        lat: float,
        lng: float,
        radius_km: float,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> str:
        # Round coordinates to 3 decimals (~110m resolution) to maximize cache hits
        norm_lat = round(lat, 3)
        norm_lng = round(lng, 3)
        cat_str = category.lower() if category else "all"
        return f"services:nearby:{norm_lat}:{norm_lng}:{radius_km}:{cat_str}:{skip}:{limit}"

    @staticmethod
    def build_list_key(category: Optional[str] = None, skip: int = 0, limit: int = 50) -> str:
        cat_str = category.lower() if category else "all"
        return f"services:list:{cat_str}:{skip}:{limit}"

    @staticmethod
    def build_detail_key(service_id: str) -> str:
        return f"services:detail:{service_id}"

    @staticmethod
    def build_categories_key() -> str:
        return "services:categories:summary"

    async def get(self, key: str) -> Optional[Any]:
        client = await self.get_redis()
        if client:
            try:
                raw = await client.get(key)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis get failed for {key}: {e}")
        return self._in_memory.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds or settings.CACHE_DEFAULT_TTL_SECONDS
        json_val = json.dumps(value, default=str)
        client = await self.get_redis()
        if client:
            try:
                await client.setex(key, ttl, json_val)
                return
            except Exception as e:
                logger.warning(f"Redis set failed for {key}: {e}")
        self._in_memory.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        client = await self.get_redis()
        if client:
            try:
                await client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed for {key}: {e}")
        self._in_memory.delete(key)

    async def invalidate_service_caches(self) -> int:
        """
        Invalidates all nearby search, listing, and category caches.
        Triggered when an admin creates, updates, deletes, or bulk uploads services.
        """
        deleted_count = 0
        client = await self.get_redis()
        if client:
            try:
                # Scan and delete all services:* keys
                cursor = 0
                while True:
                    cursor, keys = await client.scan(cursor=cursor, match="services:*", count=100)
                    if keys:
                        deleted_count += await client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis cache invalidation error: {e}")

        # Invalidate in-memory fallback
        deleted_count += self._in_memory.delete_prefix("services:")
        logger.info(f"Invalidated service caches: {deleted_count} keys evicted.")
        return deleted_count

    async def close(self) -> None:
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


cache_service = CacheService()
