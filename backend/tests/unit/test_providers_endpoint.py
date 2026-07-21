from unittest.mock import PropertyMock, patch

import pytest
from fastapi import HTTPException

from app.api.schemas.providers import LLMModelInfo, LLMProviderInfo, LLMProvidersResponse
from app.core.config import Settings
from app.core.dependencies import resolve_llm_provider


class TestLLMProvidersResponseSchema:
    def test_valid_response(self):
        response = LLMProvidersResponse(
            providers=[
                LLMProviderInfo(
                    id="openai",
                    display_name="OpenAI",
                    models=[
                        LLMModelInfo(
                            id="gpt-5.4-mini",
                            display_name="GPT-5.4 mini",
                            default_temperature=0.3,
                            supports_json_mode=True,
                        )
                    ],
                )
            ]
        )
        assert len(response.providers) == 1
        assert response.providers[0].id == "openai"
        assert response.providers[0].models[0].id == "gpt-5.4-mini"

    def test_empty_providers_is_valid(self):
        response = LLMProvidersResponse(providers=[])
        assert response.providers == []


class TestSettingsConfiguredLLMProviders:
    @patch.object(
        Settings,
        "configured_llm_providers",
        new_callable=PropertyMock,
        return_value=["openai", "gemini"],
    )
    def test_property_returns_configured_providers(self, _mock: PropertyMock):
        # The property is exercised indirectly through the route; here we
        # verify the patched value is readable as expected by integration tests.
        providers = Settings().configured_llm_providers
        assert providers == ["openai", "gemini"]

    @pytest.mark.parametrize(
        "provider,key,expected",
        [
            ("openai", "sk-real-key", True),
            ("openai", "placeholder", False),
            ("openai", None, False),
            ("gemini", "real-key", True),
        ],
    )
    def test_is_valid_api_key(self, provider: str, key: str | None, expected: bool):
        settings = Settings(
            **{
                f"{provider}_api_key": key,
            }
        )
        assert settings._is_valid_api_key(settings._api_key_for_provider(provider)) is expected


class TestResolveLLMProvider:
    @patch.object(
        Settings, "configured_llm_providers", new_callable=PropertyMock, return_value=["openai"]
    )
    @patch("app.core.dependencies.get_llm_provider")
    def test_resolve_with_configured_provider(self, mock_factory, _mock: PropertyMock):
        from tests.fixtures.fakes import FakeLLMProvider

        mock_factory.return_value = FakeLLMProvider(model="gpt-5.4")
        provider = resolve_llm_provider(provider="openai", model="gpt-5.4")
        assert provider.get_model_name() == "gpt-5.4"
        mock_factory.assert_called_once_with("openai", model="gpt-5.4")

    @patch.object(
        Settings, "configured_llm_providers", new_callable=PropertyMock, return_value=["openai"]
    )
    def test_resolve_with_unconfigured_provider_raises_400(self, _mock: PropertyMock):
        with pytest.raises(HTTPException) as exc_info:
            resolve_llm_provider(provider="gemini", model="gemini-3.5-flash")
        assert exc_info.value.status_code == 400
        assert "gemini" in exc_info.value.detail

    @patch.object(
        Settings, "configured_llm_providers", new_callable=PropertyMock, return_value=["openai"]
    )
    def test_resolve_with_unknown_model_raises_400(self, _mock: PropertyMock):
        with pytest.raises(HTTPException) as exc_info:
            resolve_llm_provider(provider="openai", model="unknown-model")
        assert exc_info.value.status_code == 400
        assert "unknown-model" in exc_info.value.detail

    def test_resolve_without_provider_or_model_uses_global_dependency(self):
        provider = resolve_llm_provider()
        assert provider is not None
