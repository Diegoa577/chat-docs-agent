from unittest.mock import PropertyMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready_endpoint_when_unconfigured():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with (
            patch.object(
                Settings,
                "configured_llm_providers",
                new_callable=PropertyMock,
                return_value=[],
            ),
            patch.object(
                Settings,
                "is_embedding_configured",
                new_callable=PropertyMock,
                return_value=False,
            ),
        ):
            response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not ready"
    assert data["checks"]["llm_configured"] is False
    assert "redis" in data["checks"]


@pytest.mark.asyncio
async def test_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "rag_requests_total" in response.text
