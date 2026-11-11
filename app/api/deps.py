from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from backend.app.database import get_db
from backend.app.core.rate_limiter import (
    public_rate_limiter,
    search_rate_limiter,
    auth_rate_limiter,
    RateLimiter
)
from backend.app.core.security import decode_access_token
from backend.app.core.exceptions import UnauthorizedException, ForbiddenException
from backend.app.services.cache_service import cache_service
from backend.app.repositories.service_repository import ServiceRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.service_manager import ServiceManager
from backend.app.services.auth_service import AuthService
from backend.app.services.bulk_upload import BulkUploadService
from backend.app.models.user import AdminUser

security_scheme = HTTPBearer(auto_error=False)


async def get_redis() -> Optional[aioredis.Redis]:
    return await cache_service.get_redis()


def rate_limit_dependency(limiter: RateLimiter):
    async def _rate_limiter_dep(
        request: Request,
        response: Response,
        redis_client: Optional[aioredis.Redis] = Depends(get_redis)
    ) -> None:
        limit, remaining, reset_ts = await limiter.check_rate_limit(request, redis_client)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_ts)

    return _rate_limiter_dep


# Rate limiting dependencies for different endpoints
rate_limit_public = rate_limit_dependency(public_rate_limiter)
rate_limit_search = rate_limit_dependency(search_rate_limiter)
rate_limit_auth = rate_limit_dependency(auth_rate_limiter)


def get_service_repository(db: AsyncSession = Depends(get_db)) -> ServiceRepository:
    return ServiceRepository(session=db)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session=db)


def get_service_manager(repo: ServiceRepository = Depends(get_service_repository)) -> ServiceManager:
    return ServiceManager(repository=repo)


def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(user_repo=repo)


def get_bulk_upload_service(repo: ServiceRepository = Depends(get_service_repository)) -> BulkUploadService:
    return BulkUploadService(repository=repo)


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    user_repo: UserRepository = Depends(get_user_repository)
) -> AdminUser:
    if not credentials:
        raise UnauthorizedException(message="Authentication credentials were not provided.")

    token = credentials.credentials
    payload = decode_access_token(token)

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Malformed authentication token.")

    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise ForbiddenException(message="Admin account is inactive or does not exist.")

    return user

