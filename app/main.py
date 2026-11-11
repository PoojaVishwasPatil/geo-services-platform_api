import os
import sys

# Ensure project root is in sys.path whether uvicorn is started from root or backend/
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT_DIR, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.exceptions import RequestValidationError

try:
    from backend.app.config import settings
    from backend.app.core.logging import logger
    from backend.app.core.exceptions import (
        AppException,
        app_exception_handler,
        validation_exception_handler,
        global_exception_handler
    )
    from backend.app.database import init_db, AsyncSessionLocal
    from backend.app.repositories.user_repository import UserRepository
    from backend.app.services.cache_service import cache_service
    from backend.app.api.v1.router import api_router
except ModuleNotFoundError:
    from app.config import settings
    from app.core.logging import logger
    from app.core.exceptions import (
        AppException,
        app_exception_handler,
        validation_exception_handler,
        global_exception_handler
    )
    from app.database import init_db, AsyncSessionLocal
    from app.repositories.user_repository import UserRepository
    from app.services.cache_service import cache_service
    from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Sequence
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode...")
    if settings.ENVIRONMENT != "testing":
        try:
            await init_db()
            # Seed default admin user if not exists
            import backend.app.database as db_module
            async with db_module.AsyncSessionLocal() as session:
                user_repo = UserRepository(session)
                admin = await user_repo.get_by_username(settings.ADMIN_DEFAULT_USERNAME)
                if not admin:
                    await user_repo.create_admin(
                        username=settings.ADMIN_DEFAULT_USERNAME,
                        email=settings.ADMIN_DEFAULT_EMAIL,
                        password=settings.ADMIN_DEFAULT_PASSWORD
                    )
                    await session.commit()
                    logger.info(f"Default admin user created: '{settings.ADMIN_DEFAULT_USERNAME}'")
                else:
                    logger.info(f"Admin user '{settings.ADMIN_DEFAULT_USERNAME}' already verified.")
        except Exception as e:
            logger.error(f"Error during application startup initialization: {e}")

        # Check cache
        await cache_service.get_redis()

    yield

    # Shutdown Sequence
    if settings.ENVIRONMENT != "testing":
        logger.info("Shutting down application and closing cache connections...")
        await cache_service.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Scalable Geo Full-Stack API for Nearby Services Platform with PostGIS, Redis Caching, and Rate Limiting.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"]
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")
