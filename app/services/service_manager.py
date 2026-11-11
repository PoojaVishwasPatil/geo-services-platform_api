from typing import Any, Dict, List, Optional, Tuple
from backend.app.models.service import Service
from backend.app.schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse
from backend.app.repositories.service_repository import ServiceRepository
from backend.app.services.cache_service import cache_service
from backend.app.core.exceptions import NotFoundException
from backend.app.core.logging import logger


class ServiceManager:
    def __init__(self, repository: ServiceRepository):
        self.repository = repository

    @staticmethod
    def _to_response_dict(service: Service, distance_km: Optional[float] = None) -> Dict[str, Any]:
        return {
            "id": service.id,
            "name": service.name,
            "category": service.category,
            "latitude": service.latitude,
            "longitude": service.longitude,
            "address": service.address,
            "rating": service.rating,
            "contact_phone": service.contact_phone,
            "metadata": service.metadata_json or {},
            "is_active": service.is_active,
            "distance_km": distance_km,
            "created_at": service.created_at.isoformat() if service.created_at else None,
            "updated_at": service.updated_at.isoformat() if service.updated_at else None,
        }

    async def get_services(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        # Check cache if not searching with dynamic query
        use_cache = search is None
        cache_key = cache_service.build_list_key(category=category, skip=skip, limit=limit)

        if use_cache:
            cached = await cache_service.get(cache_key)
            if cached is not None:
                return cached["items"], cached["total"]

        services, total = await self.repository.get_all(
            category=category,
            search=search,
            skip=skip,
            limit=limit
        )

        items = [self._to_response_dict(s) for s in services]

        if use_cache:
            await cache_service.set(cache_key, {"items": items, "total": total}, ttl_seconds=300)

        return items, total

    async def get_nearby_services(
        self,
        lat: float,
        lng: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        cache_key = cache_service.build_nearby_key(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            category=category,
            skip=skip,
            limit=limit
        )

        cached = await cache_service.get(cache_key)
        if cached is not None:
            return cached["items"], cached["total"]

        results, total = await self.repository.get_nearby(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            category=category,
            skip=skip,
            limit=limit
        )

        items = [self._to_response_dict(svc, dist) for svc, dist in results]

        await cache_service.set(cache_key, {"items": items, "total": total}, ttl_seconds=180)
        return items, total

    async def get_service_by_id(self, service_id: str) -> Dict[str, Any]:
        cache_key = cache_service.build_detail_key(service_id)
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return cached

        service = await self.repository.get_by_id(service_id)
        if not service:
            raise NotFoundException(message=f"Service with id '{service_id}' was not found.")

        data = self._to_response_dict(service)
        await cache_service.set(cache_key, data, ttl_seconds=600)
        return data

    async def create_service(self, service_in: ServiceCreate) -> Dict[str, Any]:
        service = await self.repository.create(service_in)
        # Invalidate caches across the board
        await cache_service.invalidate_service_caches()
        return self._to_response_dict(service)

    async def update_service(self, service_id: str, service_in: ServiceUpdate) -> Dict[str, Any]:
        service = await self.repository.get_by_id(service_id)
        if not service:
            raise NotFoundException(message=f"Service with id '{service_id}' was not found.")

        updated = await self.repository.update(service, service_in)
        # Invalidate caches
        await cache_service.invalidate_service_caches()
        return self._to_response_dict(updated)

    async def delete_service(self, service_id: str) -> None:
        service = await self.repository.get_by_id(service_id)
        if not service:
            raise NotFoundException(message=f"Service with id '{service_id}' was not found.")

        await self.repository.delete(service)
        # Invalidate caches
        await cache_service.invalidate_service_caches()

    async def get_categories_summary(self) -> Dict[str, int]:
        cache_key = cache_service.build_categories_key()
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return cached

        counts = await self.repository.get_category_counts()
        await cache_service.set(cache_key, counts, ttl_seconds=300)
        return counts

