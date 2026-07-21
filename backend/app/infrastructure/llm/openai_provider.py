from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.metrics import LLM_TOKENS
from app.domain.ports.llm_provider import LLMProvider, LLMResponse
from app.infrastructure.llm.model_catalog import resolve_model_config
from app.infrastructure.llm.provider_errors import classify_provider_error


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            timeout=settings.provider_timeout_seconds,
        )
        self.model_config = resolve_model_config("openai", model or settings.llm_model)
        self.model = self.model_config.model_id

    def _merge_kwargs(
        self,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        stream: bool = False,
    ) -> dict[str, Any]:
        kwargs = self.model_config.get_generation_kwargs()
        # Newer OpenAI models (gpt-5.x, o-series) reject `max_tokens` in favor
        # of `max_completion_tokens`, and only accept temperature=1 — the
        # catalog flags those with `requires_temperature_one`.
        effective_temperature = 1.0 if self.model_config.requires_temperature_one else temperature
        kwargs.update(
            {
                "model": self.model,
                "messages": messages,
                "temperature": effective_temperature,
                "max_completion_tokens": max_tokens,
            }
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
        return kwargs

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs = self._merge_kwargs(messages, temperature, max_tokens, tools)

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise classify_provider_error(exc) from exc

        content = response.choices[0].message.content or ""

        if response.usage:
            total_tokens = response.usage.prompt_tokens + response.usage.completion_tokens
            LLM_TOKENS.labels(model=self.model, provider="openai").inc(total_tokens)

        return LLMResponse(
            content=content,
            model=self.model,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        kwargs = self._merge_kwargs(messages, temperature, max_tokens, tools, stream=True)

        total_tokens = 0
        try:
            stream = await self.client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
                if chunk.usage:
                    total_tokens = chunk.usage.total_tokens
        except Exception as exc:
            raise classify_provider_error(exc) from exc

        if total_tokens:
            LLM_TOKENS.labels(model=self.model, provider="openai").inc(total_tokens)

    def get_model_name(self) -> str:
        return self.model
