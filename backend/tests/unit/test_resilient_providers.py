import pytest

from app.domain.ports.embedding_provider import EmbeddingProvider
from app.domain.ports.llm_provider import LLMProvider, LLMResponse
from app.infrastructure.embeddings.resilient_provider import ResilientEmbeddingProvider
from app.infrastructure.llm.resilient_provider import ResilientLLMProvider


class FailingLLMProvider(LLMProvider):
    async def complete(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        raise RuntimeError("primary LLM failed")

    def get_model_name(self):
        return "failing-llm"


class FakeLLMProvider(LLMProvider):
    async def complete(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        return LLMResponse(content="fallback answer", model="fake-llm")

    def get_model_name(self):
        return "fake-llm"


class PartiallyFailingStreamProvider(LLMProvider):
    """Yields some chunks, then fails mid-stream."""

    async def complete(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        return LLMResponse(content="full", model="partial-llm")

    async def stream(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        yield "Hello"
        yield " world"
        raise RuntimeError("stream broke mid-flight")

    def get_model_name(self):
        return "partial-llm"


class FailingStreamProvider(LLMProvider):
    """Fails before yielding any chunk."""

    async def complete(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        raise RuntimeError("failed")

    async def stream(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        raise RuntimeError("stream failed before any chunk")
        yield  # pragma: no cover - makes this an async generator

    def get_model_name(self):
        return "failing-stream-llm"


class FakeStreamingLLMProvider(LLMProvider):
    async def complete(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        return LLMResponse(content="fallback answer", model="fake-stream-llm")

    async def stream(self, messages, tools=None, temperature=0.1, max_tokens=4096):
        yield "fallback "
        yield "stream"

    def get_model_name(self):
        return "fake-stream-llm"


class FailingEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts):
        raise RuntimeError("primary embedding failed")

    def get_dimension(self):
        return 1024

    def get_model_name(self):
        return "failing-embedding"


class FakeEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts):
        return [[0.1] * 1024 for _ in texts]

    def get_dimension(self):
        return 1024

    def get_model_name(self):
        return "fake-embedding"


class TestResilientLLMProvider:
    @pytest.mark.asyncio
    async def test_fallback_to_secondary_llm(self):
        provider = ResilientLLMProvider(
            primary=FailingLLMProvider(),
            fallback=FakeLLMProvider(),
            max_retries=0,
        )
        response = await provider.complete([{"role": "user", "content": "hi"}])
        assert response.content == "fallback answer"

    @pytest.mark.asyncio
    async def test_raises_when_all_llm_providers_fail(self):
        provider = ResilientLLMProvider(
            primary=FailingLLMProvider(),
            fallback=FailingLLMProvider(),
            max_retries=0,
        )
        with pytest.raises(RuntimeError):
            await provider.complete([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_get_model_name_reports_fallback_after_fallback_completes(self):
        provider = ResilientLLMProvider(
            primary=FailingLLMProvider(),
            fallback=FakeLLMProvider(),
            max_retries=0,
        )
        await provider.complete([{"role": "user", "content": "hi"}])
        assert provider.get_model_name() == "fake-llm"

    @pytest.mark.asyncio
    async def test_get_model_name_reports_primary_when_primary_succeeds(self):
        provider = ResilientLLMProvider(
            primary=FakeStreamingLLMProvider(),
            max_retries=0,
        )
        await provider.complete([{"role": "user", "content": "hi"}])
        assert provider.get_model_name() == "fake-stream-llm"

    @pytest.mark.asyncio
    async def test_stream_retries_and_falls_back_before_first_chunk(self):
        provider = ResilientLLMProvider(
            primary=FailingStreamProvider(),
            fallback=FakeStreamingLLMProvider(),
            max_retries=1,
        )
        chunks = [chunk async for chunk in provider.stream([{"role": "user", "content": "hi"}])]
        assert chunks == ["fallback ", "stream"]
        assert provider.get_model_name() == "fake-stream-llm"

    @pytest.mark.asyncio
    async def test_mid_stream_failure_does_not_retry_or_duplicate(self):
        provider = ResilientLLMProvider(
            primary=PartiallyFailingStreamProvider(),
            fallback=FakeStreamingLLMProvider(),
            max_retries=2,
        )
        chunks = []
        with pytest.raises(RuntimeError):
            async for chunk in provider.stream([{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
        # Partial output is preserved and the fallback never restarts the answer.
        assert chunks == ["Hello", " world"]


class TestResilientEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_fallback_to_secondary_embedding(self):
        provider = ResilientEmbeddingProvider(
            primary=FailingEmbeddingProvider(),
            fallback=FakeEmbeddingProvider(),
            max_retries=0,
        )
        embeddings = await provider.embed(["hello"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1024

    @pytest.mark.asyncio
    async def test_raises_when_all_embedding_providers_fail(self):
        provider = ResilientEmbeddingProvider(
            primary=FailingEmbeddingProvider(),
            fallback=FailingEmbeddingProvider(),
            max_retries=0,
        )
        with pytest.raises(RuntimeError):
            await provider.embed(["hello"])

    @pytest.mark.asyncio
    async def test_fallback_with_mismatched_dimension_is_not_used(self):
        class OtherDimensionEmbeddingProvider(EmbeddingProvider):
            def __init__(self):
                self.called = False

            async def embed(self, texts):
                self.called = True
                return [[0.1] * 1536 for _ in texts]

            def get_dimension(self):
                return 1536

            def get_model_name(self):
                return "other-dimension-embedding"

        fallback = OtherDimensionEmbeddingProvider()
        provider = ResilientEmbeddingProvider(
            primary=FailingEmbeddingProvider(),  # 1024-dim
            fallback=fallback,  # 1536-dim
            max_retries=0,
        )
        with pytest.raises(RuntimeError, match="primary embedding failed"):
            await provider.embed(["hello"])
        assert fallback.called is False
