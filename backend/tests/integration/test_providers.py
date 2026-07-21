from unittest.mock import PropertyMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app


@pytest.mark.asyncio
async def test_list_llm_providers_returns_empty_when_none_configured():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(
            Settings, "configured_llm_providers", new_callable=PropertyMock, return_value=[]
        ):
            response = await client.get("/providers/llm")

    assert response.status_code == 200
    data = response.json()
    assert data["providers"] == []


@pytest.mark.asyncio
async def test_list_llm_providers_returns_configured_provider_models():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(
            Settings,
            "configured_llm_providers",
            new_callable=PropertyMock,
            return_value=["openai"],
        ):
            response = await client.get("/providers/llm")

    assert response.status_code == 200
    data = response.json()
    assert len(data["providers"]) == 1

    provider = data["providers"][0]
    assert provider["id"] == "openai"
    assert provider["display_name"] == "OpenAI"
    assert len(provider["models"]) > 0
    assert all(
        {"id", "display_name", "default_temperature", "supports_json_mode"} <= set(model.keys())
        for model in provider["models"]
    )


@pytest.mark.asyncio
async def test_list_llm_providers_returns_multiple_configured_providers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(
            Settings,
            "configured_llm_providers",
            new_callable=PropertyMock,
            return_value=["openai", "gemini"],
        ):
            response = await client.get("/providers/llm")

    assert response.status_code == 200
    data = response.json()
    provider_ids = {p["id"] for p in data["providers"]}
    assert provider_ids == {"openai", "gemini"}


@pytest.mark.asyncio
async def test_chat_rejects_unconfigured_provider():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(
            Settings, "configured_llm_providers", new_callable=PropertyMock, return_value=["openai"]
        ):
            response = await client.post(
                "/chat",
                json={
                    "question": "What is the answer?",
                    "provider": "gemini",
                    "model": "gemini-3.5-flash",
                },
            )

    assert response.status_code == 400
    assert "gemini" in response.json()["detail"]
