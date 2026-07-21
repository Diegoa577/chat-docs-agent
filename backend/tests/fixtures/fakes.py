from collections.abc import AsyncIterator
from typing import Any

from app.domain.ports.llm_provider import LLMProvider, LLMResponse
from app.domain.value_objects import RetrievedChunk
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine


class FakeLLMProvider(LLMProvider):
    def __init__(self, response: str = "This is a fake answer.", model: str = "fake-model"):
        self.response = response
        self.model = model
        self.complete_calls: list[list[dict[str, Any]]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self.complete_calls.append(messages)
        return LLMResponse(content=self.response, model=self.model)

    def get_model_name(self) -> str:
        return self.model


class FakeStreamingLLMProvider(FakeLLMProvider):
    def __init__(self, chunks: list[str] | None = None, model: str = "fake-model"):
        super().__init__(response="".join(chunks or []), model=model)
        self.chunks = chunks or ["This ", "is ", "a ", "fake ", "answer."]

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        self.complete_calls.append(messages)
        for chunk in self.chunks:
            yield chunk


class FakeSearchEngine(HybridSearchEngine):
    def __init__(self, chunks: list[RetrievedChunk] | None = None):
        # We intentionally do not call super().__init__ to avoid requiring a real session.
        self._chunks = chunks or []
        self.queries: list[str] = []

    async def search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        self.queries.append(query)
        return self._chunks


def make_fake_chunk(
    content: str = "Fake chunk content",
    document_name: str = "fake.pdf",
    final_score: float = 0.9,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_name=document_name,
        content=content,
        page_number=1,
        section_title="Section",
        keyword_score=0.8,
        vector_score=0.9,
        final_score=final_score,
    )
