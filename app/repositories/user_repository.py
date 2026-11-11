from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import AdminUser
from backend.app.core.security import get_password_hash


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> Optional[AdminUser]:
        stmt = select(AdminUser).where(AdminUser.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> Optional[AdminUser]:
        stmt = select(AdminUser).where(AdminUser.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_admin(self, username: str, email: str, password: str) -> AdminUser:
        hashed_pw = get_password_hash(password)
        user = AdminUser(
            username=username,
            email=email,
            hashed_password=hashed_pw,
            is_active=True
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

