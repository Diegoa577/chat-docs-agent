from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport

from app.api.routes.documents import get_document_service
from app.application.services.document_service import DocumentService
from app.core.dependencies import get_async_session
from app.domain.models.document import DocumentStatus
from app.infrastructure.db.models import DocumentModel
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.main import app
from tests.conftest import AsyncTestSessionLocal, _is_db_available

pytestmark = pytest.mark.skipif(not _is_db_available(), reason="Test database is not available")


async def _create_client(tmp_path):
    session = AsyncTestSessionLocal()
    file_storage = LocalFileStorage(base_dir=str(tmp_path))
    task_calls: list[tuple[str, str, str]] = []

    def fake_task_runner(document_id: str, filename: str, content_type: str) -> None:
        task_calls.append((document_id, filename, content_type))

    async def _get_async_session():
        yield session

    def _get_document_service() -> DocumentService:
        return DocumentService(
            document_repository=PostgresDocumentRepository(session),
            file_storage=file_storage,
            task_runner=fake_task_runner,
        )

    app.dependency_overrides[get_async_session] = _get_async_session
    app.dependency_overrides[get_document_service] = _get_document_service

    transport = ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client, session, file_storage, task_calls


async def _close(client: httpx.AsyncClient, session):
    await client.aclose()
    await session.close()
    app.dependency_overrides.clear()


async def _seed_document(session, status: DocumentStatus, error_message: str | None = None):
    document = DocumentModel(
        id=uuid4(),
        filename="protocol.txt",
        content_type="text/plain",
        status=status,
        error_message=error_message,
    )
    session.add(document)
    await session.commit()
    return document


@pytest.mark.asyncio
async def test_reprocess_failed_document_returns_202_and_resets(tmp_path):
    client, session, _, task_calls = await _create_client(tmp_path)
    try:
        document = await _seed_document(
            session, DocumentStatus.FAILED, error_message="transient parse error"
        )

        response = await client.post(f"/documents/{document.id}/reprocess")

        assert response.status_code == 202
        data = response.json()
        assert data["id"] == str(document.id)
        assert data["status"] == "pending"
        assert data["error_message"] is None
        assert task_calls == [(str(document.id), "protocol.txt", "text/plain")]

        await session.refresh(document)
        assert document.status == DocumentStatus.PENDING
        assert document.error_message is None
    finally:
        await _close(client, session)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [DocumentStatus.PENDING, DocumentStatus.PROCESSING, DocumentStatus.COMPLETED],
)
async def test_reprocess_non_failed_document_returns_409(tmp_path, status):
    client, session, _, task_calls = await _create_client(tmp_path)
    try:
        document = await _seed_document(session, status)

        response = await client.post(f"/documents/{document.id}/reprocess")

        assert response.status_code == 409
        assert "only failed documents" in response.json()["detail"]
        assert task_calls == []

        await session.refresh(document)
        assert document.status == status
    finally:
        await _close(client, session)


@pytest.mark.asyncio
async def test_reprocess_missing_document_returns_404(tmp_path):
    client, session, _, task_calls = await _create_client(tmp_path)
    try:
        response = await client.post(f"/documents/{uuid4()}/reprocess")

        assert response.status_code == 404
        assert task_calls == []
    finally:
        await _close(client, session)


@pytest.mark.asyncio
async def test_delete_failed_document_removes_file_from_disk(tmp_path):
    """A failed document keeps its file, but deleting it must not leave orphans."""
    client, session, file_storage, _ = await _create_client(tmp_path)
    try:
        document = await _seed_document(
            session, DocumentStatus.FAILED, error_message="permanent failure"
        )
        file_path = await file_storage.save(UUID(str(document.id)), "protocol.txt", b"content")
        assert file_path.exists()

        response = await client.delete(f"/documents/{document.id}")

        assert response.status_code == 204
        assert not file_path.exists()
    finally:
        await _close(client, session)
