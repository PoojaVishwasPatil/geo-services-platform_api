import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_services_public(client: AsyncClient):
    response = await client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] >= 3
    assert len(data["data"]["items"]) >= 3


@pytest.mark.asyncio
async def test_list_services_category_filter(client: AsyncClient):
    response = await client.get("/api/v1/services?category=hospitals")
    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Near Care Hospital"
    assert items[0]["category"] == "hospitals"


@pytest.mark.asyncio
async def test_nearby_search_radius_filter(client: AsyncClient):
    # Origin at Mumbai center: (19.0760, 72.8777)
    # Radius = 5.0 km
    # Expect s1 and s2 to be returned, but NOT s3 (which is 25 km away)
    response = await client.get(
        "/api/v1/services/nearby",
        params={"lat": 19.0760, "lng": 72.8777, "radius_km": 5.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    items = data["data"]["items"]
    assert len(items) == 2

    # Check that items are sorted by nearest distance
    assert items[0]["distance_km"] <= items[1]["distance_km"]
    assert items[0]["distance_km"] is not None
    assert items[0]["name"] == "Near Care Hospital"


@pytest.mark.asyncio
async def test_nearby_search_category_filter(client: AsyncClient):
    response = await client.get(
        "/api/v1/services/nearby",
        params={"lat": 19.0760, "lng": 72.8777, "radius_km": 5.0, "category": "atms"}
    )
    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "City Express ATM"


@pytest.mark.asyncio
async def test_admin_crud_workflow(client: AsyncClient, auth_headers: dict):
    # 1. Create a new service as admin
    new_payload = {
        "name": "New Downtown Clinic",
        "category": "hospitals",
        "latitude": 19.0770,
        "longitude": 72.8780,
        "address": "Downtown Suite 10",
        "rating": 4.9,
        "contact_phone": "+91-9988776655",
        "metadata": {"icu": True}
    }
    create_res = await client.post("/api/v1/services", json=new_payload, headers=auth_headers)
    assert create_res.status_code == 201
    created_data = create_res.json()["data"]
    service_id = created_data["id"]
    assert created_data["name"] == "New Downtown Clinic"

    # 2. Get detail
    get_res = await client.get(f"/api/v1/services/{service_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == service_id

    # 3. Update service
    update_res = await client.put(
        f"/api/v1/services/{service_id}",
        json={"name": "Updated Clinic Name", "rating": 5.0},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Updated Clinic Name"
    assert update_res.json()["data"]["rating"] == 5.0

    # 4. Delete service
    del_res = await client.delete(f"/api/v1/services/{service_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 5. Verify 404 after deletion
    get_after_del = await client.get(f"/api/v1/services/{service_id}")
    assert get_after_del.status_code == 404

