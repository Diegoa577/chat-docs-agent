import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_async_session,
    get_llm_provider_dep,
    get_search_engine,
)
from app.infrastructure.db.models import ConversationModel
from app.main import app
from tests.conftest import AsyncTestSessionLocal, _is_db_available
from tests.fixtures.fakes import (
    FakeLLMProvider,
    FakeSearchEngine,
    FakeStreamingLLMProvider,
    make_fake_chunk,
)

pytestmark = pytest.mark.skipif(not _is_db_available(), reason="Test database is not available")


async def _create_client_and_session(
    response_text: str = "The inclusion criteria require informed consent.",
    chunks=None,
    streaming: bool = False,
):
    session = AsyncTestSessionLocal()

    async def _get_async_session():
        yield session

    app.dependency_overrides[get_async_session] = _get_async_session
    app.dependency_overrides[get_search_engine] = lambda: FakeSearchEngine(
        chunks=chunks or [make_fake_chunk()]
    )
    if streaming:
        app.dependency_overrides[get_llm_provider_dep] = lambda: FakeStreamingLLMProvider(
            chunks=["The ", "inclusion ", "criteria ", "require ", "informed ", "consent."]
        )
    else:
        app.dependency_overrides[get_llm_provider_dep] = lambda: FakeLLMProvider(
            response=response_text
        )

    transport = ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client, session


async def _close(client: httpx.AsyncClient, session: AsyncSession):
    await client.aclose()
    await session.close()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_creates_conversation():
    client, session = await _create_client_and_session()
    try:
        response = await client.post(
            "/chat",
            json={"question": "What are the inclusion criteria?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["answer"] == "The inclusion criteria require informed consent."
        assert len(data["citations"]) == 1
        assert data["confidence"] == "high"

        # Verify persistence
        conversation_id = data["conversation_id"]
        result = await session.get(ConversationModel, conversation_id)
        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[0]["role"] == "user"
        assert result.messages[1]["role"] == "assistant"
    finally:
        await _close(client, session)


@pytest.mark.asyncio
async def test_chat_continues_conversation():
    client, session = await _create_client_and_session()
    try:
        # First message
        response1 = await client.post(
            "/chat",
            json={"question": "First question?"},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]

        # Second message with conversation_id
        response2 = await client.post(
            "/chat",
            json={
                "question": "Follow-up question?",
                "conversation_id": conversation_id,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["conversation_id"] == conversation_id

        result = await session.get(ConversationModel, conversation_id)
        assert len(result.messages) == 4
    finally:
        await _close(client, session)


@pytest.mark.asyncio
async def test_chat_stream_returns_ndjson_and_persists():
    client, session = await _create_client_and_session(streaming=True)
    try:
        events = []
        async with client.stream(
            "POST",
            "/chat/stream",
            json={"question": "What are the inclusion criteria?"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/x-ndjson"
            async for line in response.aiter_lines():
                if line.strip():
                    events.append(line.strip())

        assert len(events) >= 3

        import json

        first = json.loads(events[0])
        assert first["type"] == "metadata"
        last = json.loads(events[-1])
        assert last["type"] == "done"

        content = ""
        for line in events:
            data = json.loads(line)
            if data["type"] == "chunk":
                content += data["content"]
        assert content == "The inclusion criteria require informed consent."

        # Extract conversation_id from first event
        metadata = first
        conversation_id = metadata["conversation_id"]
        result = await session.get(ConversationModel, conversation_id)
        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[0]["role"] == "user"
        assert result.messages[1]["role"] == "assistant"
        assert result.messages[1]["content"] == content
    finally:
        await _close(client, session)
