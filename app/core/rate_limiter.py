import time
from collections import defaultdict, deque
from typing import Optional, Tuple
from fastapi import Request
import redis.asyncio as aioredis

from backend.app.config import settings
from backend.app.core.exceptions import RateLimitExceededException
from backend.app.core.logging import logger

# In-memory sliding window fallback when Redis is unreachable
_in_memory_rate_limiter = defaultdict(deque)


class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int,
        endpoint_tag: str,
        window_seconds: int = 60,
        enabled: Optional[bool] = None
    ):
        self.limit = requests_per_minute
        self.endpoint_tag = endpoint_tag
        self.window_seconds = window_seconds
        self.enabled = enabled if enabled is not None else settings.RATE_LIMIT_ENABLED

    @staticmethod
    def get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return "127.0.0.1"

    async def check_rate_limit(
        self,
        request: Request,
        redis_client: Optional[aioredis.Redis] = None
    ) -> Tuple[int, int, int]:
        """
        Validates rate limit for current client IP.
        Returns: (limit, remaining, reset_timestamp)
        Raises: RateLimitExceededException if exceeded.
        """
        if not self.enabled:
            return (self.limit, self.limit, int(time.time() + self.window_seconds))

        client_ip = self.get_client_ip(request)
        key = f"ratelimit:{self.endpoint_tag}:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds

        # Attempt Redis sliding window
        if redis_client:
            try:
                pipe = redis_client.pipeline(transaction=True)
                # Remove timestamps older than window
                pipe.zremrangebyscore(key, 0, window_start)
                # Count elements in current window
                pipe.zcard(key)
                # Fetch oldest timestamp to compute exact reset time
                pipe.zrange(key, 0, 0, withscores=True)
                results = await pipe.execute()

                current_count = results[1]
                oldest_entries = results[2]

                if current_count >= self.limit:
                    if oldest_entries:
                        oldest_ts = oldest_entries[0][1]
                        retry_after = max(1, int(oldest_ts + self.window_seconds - now))
                    else:
                        retry_after = self.window_seconds
                    
                    logger.warning(f"Rate limit exceeded for {client_ip} on '{self.endpoint_tag}'. Limit: {self.limit}/min")
                    raise RateLimitExceededException(retry_after=retry_after)

                # Add current request timestamp
                pipe = redis_client.pipeline(transaction=True)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, self.window_seconds + 5)
                await pipe.execute()

                remaining = max(0, self.limit - (current_count + 1))
                reset_ts = int(now + self.window_seconds)
                return (self.limit, remaining, reset_ts)

            except RateLimitExceededException:
                raise
            except Exception as e:
                logger.warning(f"Redis rate limiter failed, switching to in-memory fallback: {e}")

        # In-memory sliding window fallback
        queue = _in_memory_rate_limiter[key]
        while queue and queue[0] <= window_start:
            queue.popleft()

        if len(queue) >= self.limit:
            oldest_ts = queue[0]
            retry_after = max(1, int(oldest_ts + self.window_seconds - now))
            raise RateLimitExceededException(retry_after=retry_after)

        queue.append(now)
        remaining = max(0, self.limit - len(queue))
        reset_ts = int(now + self.window_seconds)
        return (self.limit, remaining, reset_ts)


# Standard rate limiter instances
public_rate_limiter = RateLimiter(
    requests_per_minute=settings.RATE_LIMIT_PUBLIC_PER_MINUTE,
    endpoint_tag="public"
)
search_rate_limiter = RateLimiter(
    requests_per_minute=settings.RATE_LIMIT_SEARCH_PER_MINUTE,
    endpoint_tag="search"
)
auth_rate_limiter = RateLimiter(
    requests_per_minute=settings.RATE_LIMIT_AUTH_PER_MINUTE,
    endpoint_tag="auth"
)

