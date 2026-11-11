import math
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from backend.app.schemas.service import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    NearbySearchParams
)
from backend.app.schemas.common import APIResponse, PaginatedResponse
from backend.app.schemas.bulk import BulkUploadResponse
from backend.app.services.service_manager import ServiceManager
from backend.app.services.bulk_upload import BulkUploadService
from backend.app.models.user import AdminUser
from backend.app.api.deps import (
    get_service_manager,
    get_bulk_upload_service,
    get_current_admin,
    rate_limit_public,
    rate_limit_search
)

router = APIRouter(prefix="/services", tags=["Services"])


# ==============================================================================
# Public Endpoints (No Authentication Required)
# ==============================================================================

@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[ServiceResponse]],
    dependencies=[Depends(rate_limit_public)],
    summary="List all services (Public, Cached, Paginated)"
)
async def list_services(
    category: Optional[str] = Query(None, description="Filter by category (e.g. hospitals, atms, shops)"),
    search: Optional[str] = Query(None, description="Search term for service name or address"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    skip = (page - 1) * limit
    items, total = await service_manager.get_services(
        category=category,
        search=search,
        skip=skip,
        limit=limit
    )

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.get(
    "/nearby",
    response_model=APIResponse[PaginatedResponse[ServiceResponse]],
    dependencies=[Depends(rate_limit_search)],
    summary="Search nearby services by coordinates & radius (Public, Geospatial PostGIS, Cached)"
)
async def search_nearby(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Origin latitude"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Origin longitude"),
    radius_km: float = Query(5.0, gt=0.0, le=500.0, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    skip = (page - 1) * limit
    items, total = await service_manager.get_nearby_services(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        category=category,
        skip=skip,
        limit=limit
    )

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.get(
    "/{service_id}",
    response_model=APIResponse[ServiceResponse],
    dependencies=[Depends(rate_limit_public)],
    summary="Get single service details (Public, Cached)"
)
async def get_service(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    service_dict = await service_manager.get_service_by_id(service_id)
    return APIResponse(
        success=True,
        data=service_dict
    )


# ==============================================================================
# Admin Protected Endpoints (Requires Valid Admin Bearer JWT)
# ==============================================================================

@router.post(
    "",
    response_model=APIResponse[ServiceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service location (Admin Only)"
)
async def create_service(
    service_in: ServiceCreate,
    current_admin: AdminUser = Depends(get_current_admin),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    created = await service_manager.create_service(service_in)
    return APIResponse(
        success=True,
        data=created,
        message="Service location created successfully."
    )


@router.put(
    "/{service_id}",
    response_model=APIResponse[ServiceResponse],
    summary="Update an existing service location (Admin Only)"
)
async def update_service(
    service_id: str,
    service_in: ServiceUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    updated = await service_manager.update_service(service_id, service_in)
    return APIResponse(
        success=True,
        data=updated,
        message="Service updated successfully."
    )


@router.delete(
    "/{service_id}",
    response_model=APIResponse[dict],
    summary="Delete a service location (Admin Only)"
)
async def delete_service(
    service_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    await service_manager.delete_service(service_id)
    return APIResponse(
        success=True,
        data={"deleted_id": service_id},
        message="Service deleted successfully."
    )


@router.post(
    "/bulk-upload",
    response_model=APIResponse[BulkUploadResponse],
    summary="Bulk upload services from CSV or JSON file (Admin Only)"
)
async def bulk_upload_services(
    file: UploadFile = File(..., description="CSV or JSON file with service locations"),
    current_admin: AdminUser = Depends(get_current_admin),
    bulk_service: BulkUploadService = Depends(get_bulk_upload_service)
):
    result = await bulk_service.process_file(file)
    return APIResponse(
        success=True,
        data=result,
        message=f"Processed {result.total_records} records: {result.successful_inserts} inserted, {result.failed_inserts} failed."
    )

