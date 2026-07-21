from app.core.config import settings
from app.domain.ports.embedding_provider import EmbeddingProvider
from app.infrastructure.embeddings.bge_embedding_provider import BGEEmbeddingProvider
from app.infrastructure.embeddings.openai_embedding_provider import OpenAIEmbeddingProvider


def get_embedding_provider(provider_name: str | None = None) -> EmbeddingProvider:
    provider = provider_name or settings.embedding_provider
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    if provider in {"bge", "huggingface"}:
        return BGEEmbeddingProvider()
    raise ValueError(f"Unsupported embedding provider: {provider}")
