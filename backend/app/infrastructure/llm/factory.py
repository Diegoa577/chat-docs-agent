from app.core.config import settings
from app.domain.ports.llm_provider import LLMProvider
from app.infrastructure.llm.gemini_provider import GeminiProvider
from app.infrastructure.llm.openai_provider import OpenAIProvider


def get_llm_provider(provider_name: str | None = None, model: str | None = None) -> LLMProvider:
    provider = provider_name or settings.llm_provider
    if provider == "openai":
        return OpenAIProvider(model=model)
    if provider == "gemini":
        return GeminiProvider(model=model)
    raise ValueError(f"Unsupported LLM provider: {provider}")
