from httpx import AsyncClient


async def test_root_and_health_endpoints(client: AsyncClient) -> None:
    root_res = await client.get("/")
    assert root_res.status_code == 200
    assert root_res.json()["health"] == "/health"

    health_res = await client.get("/health")
    assert health_res.status_code == 200
    data = health_res.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"

    v1_health_res = await client.get("/api/v1/health")
    assert v1_health_res.status_code == 200
    assert v1_health_res.json()["status"] == "ok"

