from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str
    model: str


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        raise NotImplementedError

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Yield text deltas as they are generated.

        The default implementation falls back to `complete()` and yields the
        full content at once. Concrete providers should override this with
        native streaming for better UX.
        """
        response = await self.complete(messages, tools, temperature, max_tokens)
        yield response.content

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError
