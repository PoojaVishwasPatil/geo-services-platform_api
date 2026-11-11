import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "Bearer"
    assert data["data"]["user"]["username"] == "testadmin"


@pytest.mark.asyncio
async def test_admin_login_invalid_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_protected_routes_reject_unauthenticated(client: AsyncClient):
    # Attempt to create a service without token
    response = await client.post(
        "/api/v1/services",
        json={
            "name": "Unauthorized Clinic",
            "category": "hospitals",
            "latitude": 19.0,
            "longitude": 72.0
        }
    )
    assert response.status_code == 401
    assert response.json()["success"] is False

