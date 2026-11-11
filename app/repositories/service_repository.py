import math
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select, update, delete, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DistanceSphere, ST_MakePoint, ST_SetSRID

from backend.app.models.service import Service
from backend.app.schemas.service import ServiceCreate, ServiceUpdate
from backend.app.core.logging import logger


class ServiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _create_wkt_point(latitude: float, longitude: float) -> WKTElement:
        # Longitude first, then Latitude in WKT Point (X=Lng, Y=Lat)
        return WKTElement(f"POINT({longitude} {latitude})", srid=4326)

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance between two points in km."""
        R = 6371.0088  # Mean Earth radius in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(R * c, 2)

    async def get_by_id(self, service_id: str) -> Optional[Service]:
        stmt = select(Service).where(Service.id == service_id, Service.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        include_inactive: bool = False
    ) -> Tuple[List[Service], int]:
        query = select(Service)
        count_query = select(func.count(Service.id))

        if not include_inactive:
            query = query.where(Service.is_active == True)
            count_query = count_query.where(Service.is_active == True)

        if category:
            query = query.where(func.lower(Service.category) == category.lower())
            count_query = count_query.where(func.lower(Service.category) == category.lower())

        if search:
            search_filter = Service.name.ilike(f"%{search}%") | Service.address.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Order by created_at desc
        query = query.order_by(desc(Service.created_at)).offset(skip).limit(limit)
        items_result = await self.session.execute(query)
        items = list(items_result.scalars().all())

        return items, total

    async def get_nearby(
        self,
        lat: float,
        lng: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Tuple[Service, float]], int]:
        """
        Geospatial nearby query using PostGIS ST_DistanceSphere and GiST indexing.
        """
        user_point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        radius_meters = radius_km * 1000.0

        # Compute distance using PostGIS ST_DistanceSphere
        distance_meters_expr = ST_DistanceSphere(Service.location, user_point)
        distance_km_expr = (distance_meters_expr / 1000.0).label("distance_km")

        base_query = (
            select(Service, distance_km_expr)
            .where(Service.is_active == True)
            .where(distance_meters_expr <= radius_meters)
        )

        count_query = (
            select(func.count(Service.id))
            .where(Service.is_active == True)
            .where(distance_meters_expr <= radius_meters)
        )

        if category:
            base_query = base_query.where(func.lower(Service.category) == category.lower())
            count_query = count_query.where(func.lower(Service.category) == category.lower())

        # Total count matching criteria
        count_res = await self.session.execute(count_query)
        total = count_res.scalar() or 0

        # Order by nearest distance
        query = base_query.order_by(asc(distance_meters_expr)).offset(skip).limit(limit)
        rows = (await self.session.execute(query)).all()

        results = [(row[0], round(float(row[1]), 2)) for row in rows]
        return results, total

    async def create(self, service_in: ServiceCreate) -> Service:
        point_geom = self._create_wkt_point(service_in.latitude, service_in.longitude)

        service = Service(
            name=service_in.name,
            category=service_in.category,
            latitude=service_in.latitude,
            longitude=service_in.longitude,
            location=point_geom,
            address=service_in.address,
            rating=service_in.rating,
            contact_phone=service_in.contact_phone,
            metadata_json=service_in.metadata or {},
            is_active=True
        )
        self.session.add(service)
        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def update(self, service: Service, service_update: ServiceUpdate) -> Service:
        update_data = service_update.model_dump(exclude_unset=True)
        if "metadata" in update_data:
            update_data["metadata_json"] = update_data.pop("metadata")

        # Update coordinates and geometry if changed
        if "latitude" in update_data or "longitude" in update_data:
            new_lat = update_data.get("latitude", service.latitude)
            new_lng = update_data.get("longitude", service.longitude)
            service.location = self._create_wkt_point(new_lat, new_lng)

        for key, value in update_data.items():
            setattr(service, key, value)

        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def delete(self, service: Service) -> None:
        await self.session.delete(service)
        await self.session.flush()

    async def get_category_counts(self) -> Dict[str, int]:
        stmt = (
            select(Service.category, func.count(Service.id))
            .where(Service.is_active == True)
            .group_by(Service.category)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
