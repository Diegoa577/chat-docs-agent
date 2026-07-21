from fastapi import APIRouter

from app.api.schemas.providers import LLMModelInfo, LLMProviderInfo, LLMProvidersResponse
from app.core.config import settings
from app.infrastructure.llm.model_catalog import get_models_for_provider

router = APIRouter(prefix="/providers", tags=["providers"])

_PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
}


@router.get("/llm", response_model=LLMProvidersResponse)
async def list_llm_providers() -> LLMProvidersResponse:
    """List LLM providers that are configured with a valid API key.

    Each provider includes the models available in the runtime catalog.
    Providers without a valid API key or without catalogued models are omitted.
    """
    providers: list[LLMProviderInfo] = []

    for provider_id in settings.configured_llm_providers:
        models = get_models_for_provider(provider_id)
        if not models:
            continue

        providers.append(
            LLMProviderInfo(
                id=provider_id,
                display_name=_PROVIDER_DISPLAY_NAMES.get(provider_id, provider_id),
                models=[
                    LLMModelInfo(
                        id=model.model_id,
                        display_name=model.display_name,
                        default_temperature=model.default_temperature,
                        supports_json_mode=model.supports_json_mode,
                    )
                    for model in models
                ],
            )
        )

    return LLMProvidersResponse(providers=providers)
