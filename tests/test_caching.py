import pytest
from httpx import AsyncClient
from backend.app.services.cache_service import cache_service


@pytest.mark.asyncio
async def test_caching_and_invalidation(client: AsyncClient, auth_headers: dict):
    # 1. Warm the cache for nearby search
    params = {"lat": 19.0760, "lng": 72.8777, "radius_km": 10.0}
    res1 = await client.get("/api/v1/services/nearby", params=params)
    assert res1.status_code == 200
    initial_total = res1.json()["data"]["total"]

    # 2. Check that the cache key was populated
    cache_key = cache_service.build_nearby_key(19.076, 72.878, 10.0, None, 0, 50)
    cached_val = await cache_service.get(cache_key)
    assert cached_val is not None
    assert cached_val["total"] == initial_total

    # 3. Add a new service right in the search circle as admin
    new_svc = {
        "name": "Cache Invalidator Hospital",
        "category": "hospitals",
        "latitude": 19.0765,
        "longitude": 72.8778,
        "address": "Close By",
        "rating": 4.9
    }
    create_res = await client.post("/api/v1/services", json=new_svc, headers=auth_headers)
    assert create_res.status_code == 201

    # 4. Verify that cache was automatically invalidated on creation
    evicted_cache = await cache_service.get(cache_key)
    assert evicted_cache is None

    # 5. Re-fetching nearby results reflects the newly added service
    res2 = await client.get("/api/v1/services/nearby", params=params)
    assert res2.status_code == 200
    new_total = res2.json()["data"]["total"]
    assert new_total == initial_total + 1

