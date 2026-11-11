from datetime import datetime, timezone
import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.schemas.common import APIResponse, HealthStatus
from backend.app.api.deps import get_redis

router = APIRouter(prefix="/health", tags=["Health & Observability"])

_app_start_time = time.time()


@router.get(
    "",
    response_model=APIResponse[HealthStatus],
    summary="Health check endpoint for container orchestration and uptime monitoring"
)
async def check_health(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    # Check Database
    db_status = {"status": "ok", "type": "postgres" if "postgres" in settings.DATABASE_URL else "sqlite"}
    try:
        start_ts = time.time()
        res = await db.execute(text("SELECT 1;"))
        res.scalar()
        db_status["latency_ms"] = round((time.time() - start_ts) * 1000, 2)
    except Exception as e:
        db_status["status"] = "error"
        db_status["error"] = str(e)

    # Check Redis
    redis_status = {"status": "ok"}
    if redis_client:
        try:
            start_ts = time.time()
            await redis_client.ping()
            redis_status["latency_ms"] = round((time.time() - start_ts) * 1000, 2)
        except Exception as e:
            redis_status["status"] = "error"
            redis_status["error"] = str(e)
    else:
        redis_status["status"] = "fallback_in_memory"

    overall_status = "healthy" if db_status["status"] == "ok" else "degraded"

    payload = HealthStatus(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    return APIResponse(
        success=overall_status == "healthy",
        data=payload,
        message=f"System is {overall_status}"
    )

