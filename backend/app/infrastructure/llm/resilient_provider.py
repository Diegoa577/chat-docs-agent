import asyncio
import random
from collections.abc import AsyncIterator
from typing import Any

import structlog

from app.core.config import settings
from app.core.metrics import FALLBACK_ACTIVATIONS
from app.domain.ports.llm_provider import LLMProvider, LLMResponse
from app.infrastructure.llm.factory import get_llm_provider
from app.infrastructure.llm.provider_errors import NonRetryableError, RetryableError

logger = structlog.get_logger()


class ResilientLLMProvider(LLMProvider):
    """LLM provider wrapper with retry and fallback to a secondary provider."""

    def __init__(
        self,
        primary: LLMProvider | None = None,
        fallback: LLMProvider | None = None,
        max_retries: int | None = None,
        retry_backoff: float | None = None,
    ):
        self.primary = primary or get_llm_provider(settings.llm_provider)
        self.fallback = fallback
        if settings.is_llm_fallback_configured:
            self.fallback = self.fallback or get_llm_provider(settings.llm_fallback_provider)
        self.max_retries = max_retries if max_retries is not None else settings.provider_max_retries
        self.retry_backoff = (
            retry_backoff if retry_backoff is not None else settings.provider_retry_backoff_seconds
        )
        # Tracks which provider produced the last successful response so that
        # get_model_name() does not misreport the primary when the fallback answered.
        self._last_used: LLMProvider = self.primary

    def _should_retry(self, exc: Exception) -> bool:
        """Return True if the exception is worth retrying."""
        if isinstance(exc, NonRetryableError):
            return False
        if isinstance(exc, RetryableError):
            return True
        # Unknown exceptions are retried conservatively.
        return True

    def _backoff_seconds(self, attempt: int) -> float:
        """Exponential backoff with full jitter."""
        base = float(self.retry_backoff * (2**attempt))
        return base + float(random.uniform(0, base))

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.primary.complete(
                    messages, tools=tools, temperature=temperature, max_tokens=max_tokens
                )
                self._last_used = self.primary
                return response
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "primary_llm_attempt_failed",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(exc),
                )
                if attempt < self.max_retries and self._should_retry(exc):
                    await asyncio.sleep(self._backoff_seconds(attempt))
                elif not self._should_retry(exc):
                    break

        if self.fallback:
            FALLBACK_ACTIVATIONS.labels(provider_type="llm").inc()
            logger.warning("falling_back_to_secondary_llm", fallback=settings.llm_fallback_provider)
            try:
                response = await self.fallback.complete(
                    messages, tools=tools, temperature=temperature, max_tokens=max_tokens
                )
                self._last_used = self.fallback
                return response
            except Exception as exc:
                last_error = exc
                logger.error("fallback_llm_failed", error=str(exc))

        raise last_error or RuntimeError("All LLM providers failed")

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        last_error: Exception | None = None
        chunks_yielded = 0

        for attempt in range(self.max_retries + 1):
            try:
                async for chunk in self.primary.stream(
                    messages, tools=tools, temperature=temperature, max_tokens=max_tokens
                ):
                    chunks_yielded += 1
                    yield chunk
                self._last_used = self.primary
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "primary_llm_stream_attempt_failed",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    chunks_yielded=chunks_yielded,
                    error=str(exc),
                )
                if chunks_yielded > 0:
                    # Retrying after partial output would duplicate text on the
                    # client. Surface the error instead of restarting the stream.
                    break
                if attempt < self.max_retries and self._should_retry(exc):
                    await asyncio.sleep(self._backoff_seconds(attempt))
                elif not self._should_retry(exc):
                    break

        if self.fallback and chunks_yielded == 0:
            FALLBACK_ACTIVATIONS.labels(provider_type="llm").inc()
            logger.warning(
                "falling_back_to_secondary_llm_stream", fallback=settings.llm_fallback_provider
            )
            try:
                async for chunk in self.fallback.stream(
                    messages, tools=tools, temperature=temperature, max_tokens=max_tokens
                ):
                    yield chunk
                self._last_used = self.fallback
                return
            except Exception as exc:
                last_error = exc
                logger.error("fallback_llm_stream_failed", error=str(exc))

        raise last_error or RuntimeError("All LLM providers failed")

    def get_model_name(self) -> str:
        return self._last_used.get_model_name()
