from collections.abc import AsyncIterator
from typing import Any

import structlog
from google import genai
from google.genai import types

from app.core.config import settings
from app.domain.ports.llm_provider import LLMProvider, LLMResponse
from app.infrastructure.llm.model_catalog import resolve_model_config
from app.infrastructure.llm.provider_errors import classify_provider_error

logger = structlog.get_logger()


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or settings.gemini_api_key
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(settings.provider_timeout_seconds * 1000)),
        )
        self.model_config = resolve_model_config("gemini", model or settings.llm_model)
        self.model = self.model_config.model_id

    def _build_contents_and_config(
        self, messages: list[dict[str, Any]], temperature: float, max_tokens: int
    ) -> tuple[list[types.Content], types.GenerateContentConfig]:
        system_instruction: str | None = None
        contents: list[types.Content] = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                # Accumulate system messages; Gemini uses a dedicated config field.
                system_instruction = (
                    f"{system_instruction}\n\n{content}" if system_instruction else content
                )
            elif role == "user":
                contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=content)])
                )
            elif role == "assistant":
                contents.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=content)])
                )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        return contents, config

    def _warn_if_tools_ignored(self, tools: list[dict[str, Any]] | None) -> None:
        """The LLMProvider port accepts tools, but this adapter does not map them
        to Gemini function calling yet. Warn instead of silently dropping them."""
        if tools:
            logger.warning(
                "tools_not_supported_by_adapter",
                provider="gemini",
                model=self.model,
                tools_count=len(tools),
            )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self._warn_if_tools_ignored(tools)
        contents, config = self._build_contents_and_config(messages, temperature, max_tokens)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise classify_provider_error(exc) from exc

        content = response.text if hasattr(response, "text") and response.text is not None else ""

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
        self._warn_if_tools_ignored(tools)
        contents, config = self._build_contents_and_config(messages, temperature, max_tokens)

        try:
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )
            async for chunk in stream:
                text = chunk.text if hasattr(chunk, "text") and chunk.text is not None else ""
                if text:
                    yield text
        except Exception as exc:
            raise classify_provider_error(exc) from exc

    def get_model_name(self) -> str:
        return self.model
