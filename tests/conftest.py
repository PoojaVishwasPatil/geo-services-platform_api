import asyncio
import os
import sys
import pytest
import pytest_asyncio

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Force testing configuration
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["RATE_LIMIT_ENABLED"] = "true"
os.environ["RATE_LIMIT_PUBLIC_PER_MINUTE"] = "100"
os.environ["RATE_LIMIT_SEARCH_PER_MINUTE"] = "100"
os.environ["RATE_LIMIT_AUTH_PER_MINUTE"] = "5"

from backend.app.config import settings

settings.ENVIRONMENT = "testing"
settings.RATE_LIMIT_ENABLED = True
settings.RATE_LIMIT_PUBLIC_PER_MINUTE = 100
settings.RATE_LIMIT_SEARCH_PER_MINUTE = 100
settings.RATE_LIMIT_AUTH_PER_MINUTE = 5

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.service import Service, ServiceCategory
from backend.app.models.user import AdminUser
from backend.app.core.security import get_password_hash, create_access_token
from backend.app.services.cache_service import cache_service

# Test SQLite Engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Clear caches
    await cache_service.invalidate_service_caches()

    # Seed Admin User and Benchmark Services
    async with TestSessionLocal() as session:
        admin = AdminUser(
            id="test-admin-id",
            username="testadmin",
            email="testadmin@example.com",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True
        )
        session.add(admin)

        # 3 Benchmark services around Mumbai Center (19.0760, 72.8777)
        # S1: ~0.5 km away
        s1 = Service(
            name="Near Care Hospital",
            category="hospitals",
            latitude=19.0790,
            longitude=72.8790,
            address="Near Street 1",
            rating=4.8,
            is_active=True
        )
        # S2: ~2.0 km away
        s2 = Service(
            name="City Express ATM",
            category="atms",
            latitude=19.0900,
            longitude=72.8850,
            address="Midway Ave",
            rating=4.2,
            is_active=True
        )
        # S3: ~25.0 km away (Outside 5km radius)
        s3 = Service(
            name="Faraway Supermarket",
            category="shops",
            latitude=19.2800,
            longitude=72.9500,
            address="Distant Way",
            rating=4.5,
            is_active=True
        )
        session.add_all([s1, s2, s3])
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture
def admin_token() -> str:
    return create_access_token({"sub": "test-admin-id", "username": "testadmin", "role": "admin"})


@pytest_asyncio.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
