from fastapi import APIRouter

try:
    from backend.app.api.v1.endpoints import auth, services, categories, health
except ModuleNotFoundError:
    from app.api.v1.endpoints import auth, services, categories, health

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(services.router)

