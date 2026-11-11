from datetime import timedelta
from typing import Dict, Any
from backend.app.config import settings
from backend.app.repositories.user_repository import UserRepository
from backend.app.core.security import verify_password, create_access_token
from backend.app.core.exceptions import UnauthorizedException
from backend.app.schemas.auth import TokenResponse, AdminUserResponse


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_admin(self, username: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_username(username)
        if not user or not user.is_active:
            raise UnauthorizedException(message="Incorrect username or password.")

        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException(message="Incorrect username or password.")

        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "sub": user.id,
            "username": user.username,
            "role": "admin"
        }
        access_token = create_access_token(data=token_data, expires_delta=expires_delta)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=AdminUserResponse.model_validate(user)
        )

