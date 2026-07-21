import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_async_session,
    get_llm_provider_dep,
    get_search_engine,
)
from app.infrastructure.db.models import DocumentModel
from app.main import app
from tests.conftest import AsyncTestSessionLocal, _is_db_available
from tests.fixtures.fakes import FakeLLMProvider, FakeSearchEngine, make_fake_chunk

pytestmark = pytest.mark.skipif(not _is_db_available(), reason="Test database is not available")


async def _create_client_and_session(
    response_text: str = "The answer is 42.",
    chunks=None,
):
    session = AsyncTestSessionLocal()

    async def _get_async_session():
        yield session

    app.dependency_overrides[get_async_session] = _get_async_session
    app.dependency_overrides[get_search_engine] = lambda: FakeSearchEngine(
        chunks=chunks or [make_fake_chunk()]
    )
    app.dependency_overrides[get_llm_provider_dep] = lambda: FakeLLMProvider(response=response_text)

    transport = ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client, session


async def _close(client: httpx.AsyncClient, session: AsyncSession):
    await client.aclose()
    await session.close()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_document_returns_accepted():
    client, session = await _create_client_and_session()
    try:
        response = await client.post(
            "/documents",
            files={
                "file": (
                    "protocol.txt",
                    b"Inclusion criteria: adult patients aged 18-65 with RA.",
                    "text/plain",
                )
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert data["filename"] == "protocol.txt"
        assert data["status"] == "pending"

        # Document was persisted
        document = await session.get(DocumentModel, data["id"])
        assert document is not None
        assert document.filename == "protocol.txt"
    finally:
        await _close(client, session)


@pytest.mark.asyncio
async def test_delete_document_removes_it():
    client, session = await _create_client_and_session()
    try:
        # Upload a document
        upload_response = await client.post(
            "/documents",
            files={
                "file": (
                    "protocol.txt",
                    b"Inclusion criteria: adult patients aged 18-65 with RA.",
                    "text/plain",
                )
            },
        )
        assert upload_response.status_code == 202
        document_id = upload_response.json()["id"]

        # Delete it
        delete_response = await client.delete(f"/documents/{document_id}")
        assert delete_response.status_code == 204

        # Verify it no longer exists
        get_response = await client.get(f"/documents/{document_id}")
        assert get_response.status_code == 404
    finally:
        await _close(client, session)


async def test_delete_missing_document_returns_404():
    client, session = await _create_client_and_session()
    try:
        from uuid import uuid4

        response = await client.delete(f"/documents/{uuid4()}")
        assert response.status_code == 404
    finally:
        await _close(client, session)


async def test_upload_document_rejects_oversized_file():
    client, session = await _create_client_and_session()
    try:
        # Create content larger than the configured 50MB limit.
        oversized_content = b"x" * (51 * 1024 * 1024)
        response = await client.post(
            "/documents",
            files={
                "file": (
                    "huge.txt",
                    oversized_content,
                    "text/plain",
                )
            },
        )
        assert response.status_code == 413
        assert "exceeds" in response.json()["detail"].lower()
    finally:
        await _close(client, session)


async def test_chat_after_seeded_document():
    """Simulate chat when a completed document already exists in the database."""
    client, session = await _create_client_and_session()
    try:
        # Seed a completed document directly
        from uuid import uuid4

        document = DocumentModel(
            id=uuid4(),
            filename="seeded.txt",
            content_type="text/plain",
            status="completed",
        )
        session.add(document)
        await session.commit()

        response = await client.post(
            "/chat",
            json={"question": "What are the inclusion criteria?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["answer"] == "The answer is 42."
        assert len(data["citations"]) == 1
    finally:
        await _close(client, session)
