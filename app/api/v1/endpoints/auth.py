from fastapi import APIRouter, Depends, status
from backend.app.schemas.auth import LoginRequest, TokenResponse, AdminUserResponse
from backend.app.schemas.common import APIResponse
from backend.app.services.auth_service import AuthService
from backend.app.models.user import AdminUser
from backend.app.api.deps import get_auth_service, get_current_admin, rate_limit_auth

router = APIRouter(prefix="/auth", tags=["Admin Authentication"])


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_auth)],
    summary="Admin Login (Rate Limited to prevent brute-force)"
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    token_response = await auth_service.authenticate_admin(
        username=request.username,
        password=request.password
    )
    return APIResponse(
        success=True,
        data=token_response,
        message="Login successful"
    )


@router.get(
    "/me",
    response_model=APIResponse[AdminUserResponse],
    summary="Get current authenticated admin user"
)
async def get_current_user_profile(
    current_admin: AdminUser = Depends(get_current_admin)
):
    return APIResponse(
        success=True,
        data=AdminUserResponse.model_validate(current_admin),
        message="Authenticated admin profile"
    )

