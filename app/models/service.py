import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, Float, Text, Boolean, DateTime, JSON
from geoalchemy2 import Geometry
from backend.app.database import Base


class ServiceCategory(str, enum.Enum):
    HOSPITALS = "hospitals"
    ATMS = "atms"
    SHOPS = "shops"
    RESTAURANTS = "restaurants"
    PHARMACIES = "pharmacies"
    OTHERS = "others"


class Service(Base):
    __tablename__ = "services"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    
    # Coordinates stored directly as floats for fast extraction
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # PostGIS spatial point (SRID 4326 = WGS 84 GPS standard)
    # Allows fast GiST spatial index lookups on PostgreSQL
    location = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)

    address = Column(Text, nullable=True)
    rating = Column(Float, nullable=True, default=None)
    contact_phone = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Service(id='{self.id}', name='{self.name}', category='{self.category}')>"
