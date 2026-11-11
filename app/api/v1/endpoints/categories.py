from typing import Dict, List
from fastapi import APIRouter, Depends
from backend.app.schemas.common import APIResponse
from backend.app.services.service_manager import ServiceManager
from backend.app.models.service import ServiceCategory
from backend.app.api.deps import get_service_manager, rate_limit_public

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=APIResponse[Dict[str, int]],
    dependencies=[Depends(rate_limit_public)],
    summary="Get available service categories and their counts (Cached)"
)
async def get_categories(
    service_manager: ServiceManager = Depends(get_service_manager)
):
    counts = await service_manager.get_categories_summary()
    # Ensure all enum categories appear even if count is 0
    all_categories = {cat.value: 0 for cat in ServiceCategory}
    all_categories.update(counts)

    return APIResponse(
        success=True,
        data=all_categories,
        message="Categories summary retrieved successfully."
    )

