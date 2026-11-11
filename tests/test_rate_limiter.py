import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limiting_headers_injected(client: AsyncClient):
    response = await client.get("/api/v1/services")
    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
    assert "x-ratelimit-reset" in response.headers


@pytest.mark.asyncio
async def test_auth_rate_limiting_triggers_429(client: AsyncClient):
    # Auth limit configured to 5 requests per minute
    # Sending 6 requests from same client IP should trigger 429
    responses = []
    for _ in range(6):
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "WrongPassword!"}
        )
        responses.append(res)

    # The 6th request must be throttled with HTTP 429
    assert responses[-1].status_code == 429
    data = responses[-1].json()
    assert data["success"] is False
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry-after" in responses[-1].headers

