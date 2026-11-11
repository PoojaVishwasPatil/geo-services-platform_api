from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from backend.app.models.service import ServiceCategory


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Name of the service")
    category: str = Field(..., description="Service category (e.g. hospitals, atms, shops, restaurants, pharmacies, others)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS 84 latitude in degrees (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS 84 longitude in degrees (-180 to +180)")
    address: Optional[str] = Field(None, max_length=500, description="Physical address or location hint")
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact telephone number")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom JSON metadata attributes")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        clean = v.strip().lower()
        valid = [c.value for c in ServiceCategory]
        if clean not in valid:
            raise ValueError(f"Category '{v}' is invalid. Must be one of: {', '.join(valid)}")
        return clean


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    address: Optional[str] = None
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    contact_phone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().lower()
        valid = [c.value for c in ServiceCategory]
        if clean not in valid:
            raise ValueError(f"Category '{v}' is invalid. Must be one of: {', '.join(valid)}")
        return clean


class ServiceResponse(BaseModel):
    id: str
    name: str
    category: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    rating: Optional[float] = None
    contact_phone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True
    distance_km: Optional[float] = Field(None, description="Computed distance from user coordinate in kilometers")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NearbySearchParams(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="User's current latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="User's current longitude")
    radius_km: float = Field(5.0, gt=0.0, le=500.0, description="Search radius in kilometers (default 5km)")
    category: Optional[str] = Field(None, description="Optional category filter")
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)

