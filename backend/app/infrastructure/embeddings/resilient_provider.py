import asyncio
import functools
import random

import structlog

from app.core.config import settings
from app.core.metrics import FALLBACK_ACTIVATIONS
from app.domain.ports.embedding_provider import EmbeddingProvider
from app.infrastructure.embeddings.factory import get_embedding_provider
from app.infrastructure.llm.provider_errors import NonRetryableError, RetryableError

logger = structlog.get_logger()


class ResilientEmbeddingProvider(EmbeddingProvider):
    """Embedding provider wrapper with retry and fallback to a secondary provider."""

    def __init__(
        self,
        primary: EmbeddingProvider | None = None,
        fallback: EmbeddingProvider | None = None,
        max_retries: int | None = None,
        retry_backoff: float | None = None,
    ):
        self.primary = primary or get_embedding_provider(settings.embedding_provider)
        self.fallback = fallback
        if settings.is_embedding_fallback_configured:
            self.fallback = self.fallback or get_embedding_provider(
                settings.embedding_fallback_provider
            )
        self.max_retries = max_retries if max_retries is not None else settings.provider_max_retries
        self.retry_backoff = (
            retry_backoff if retry_backoff is not None else settings.provider_retry_backoff_seconds
        )

    def _should_retry(self, exc: Exception) -> bool:
        """Return True if the exception is worth retrying."""
        if isinstance(exc, NonRetryableError):
            return False
        if isinstance(exc, RetryableError):
            return True
        return True

    def _backoff_seconds(self, attempt: int) -> float:
        """Exponential backoff with full jitter."""
        base = float(self.retry_backoff * (2**attempt))
        return base + float(random.uniform(0, base))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self.primary.embed(texts)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "primary_embedding_attempt_failed",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(exc),
                )
                if attempt < self.max_retries and self._should_retry(exc):
                    await asyncio.sleep(self._backoff_seconds(attempt))
                elif not self._should_retry(exc):
                    break

        if self.fallback:
            if self.fallback.get_dimension() != self.primary.get_dimension():
                # Falling back across embedding dimensions would produce
                # vectors that neither fit the pgvector column nor live in the
                # same embedding space. Fail explicitly instead.
                logger.error(
                    "embedding_fallback_dimension_mismatch",
                    primary_dimension=self.primary.get_dimension(),
                    fallback_dimension=self.fallback.get_dimension(),
                )
            else:
                FALLBACK_ACTIVATIONS.labels(provider_type="embedding").inc()
                logger.warning(
                    "falling_back_to_secondary_embedding",
                    fallback=settings.embedding_fallback_provider,
                )
                try:
                    return await self.fallback.embed(texts)
                except Exception as exc:
                    last_error = exc
                    logger.error("fallback_embedding_failed", error=str(exc))

        raise last_error or RuntimeError("All embedding providers failed")

    def get_dimension(self) -> int:
        return self.primary.get_dimension()

    def get_model_name(self) -> str:
        return self.primary.get_model_name()


@functools.lru_cache(maxsize=1)
def get_cached_embedding_provider() -> EmbeddingProvider:
    """Process-wide singleton resilient embedding provider.

    The BGE provider lazy-loads the SentenceTransformer model per instance, so
    building a new provider per request would reload the model into memory on
    every call. Share one instance per process instead. FastAPI
    dependency_overrides and injected fakes still take precedence in tests.
    """
    return ResilientEmbeddingProvider()
