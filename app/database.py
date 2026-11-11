from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.app.config import settings
from backend.app.core.logging import logger

Base = declarative_base()

# PostgreSQL Connection Configuration with async connection pooling
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "connect_args": {
        "timeout": 5.0,
        "server_settings": {"application_name": "nearby_services_api"}
    }
}

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize PostgreSQL database tables and PostGIS extension."""
    logger.info(f"Connecting to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL + PostGIS database schemas initialized successfully.")
    except Exception as e:
        logger.error(
            f"Failed to connect to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} ({e}). "
            f"Please ensure PostgreSQL is running (e.g., via 'docker compose up -d postgres')."
        )
        raise
