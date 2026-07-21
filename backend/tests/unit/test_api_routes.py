"""Unit tests for FastAPI route modules using dependency overrides."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import documents as documents_module
from app.core.config import Settings
from app.core.dependencies import (
    get_conversation_repository,
    get_document_repository,
    get_file_storage,
    get_llm_provider_dep,
    get_search_engine,
    get_task_runner,
)
from app.domain.models.chunk import Chunk
from app.domain.models.conversation import Conversation, MessageRole
from app.domain.models.document import Document, DocumentStatus
from app.domain.ports.file_storage import FileStorage
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.main import app
from tests.fixtures.fakes import FakeLLMProvider, FakeSearchEngine, make_fake_chunk


class _FakeDocumentRepository(DocumentRepository):
    def __init__(self, documents: list[Document] | None = None):
        self._documents = {d.id: d for d in (documents or [])}

    async def save(self, document: Document) -> Document:
        self._documents[document.id] = document
        return document

    async def update(self, document: Document) -> Document:
        self._documents[document.id] = document
        return document

    async def save_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        return chunks

    async def delete_chunks_by_document(self, document_id: UUID) -> None:
        return None

    async def update_search_vectors(self, document_id: UUID) -> None:
        return None

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self._documents.get(document_id)

    async def list_documents(
        self, limit: int = 100, offset: int = 0
    ) -> list[Document]:
        docs = list(self._documents.values())
        return docs[offset : offset + limit]

    async def delete(self, document_id: UUID) -> None:
        if document_id not in self._documents:
            raise ValueError("Document not found")
        del self._documents[document_id]


class _FakeConversationRepository(ConversationRepository):
    def __init__(self, conversations: list[Conversation] | None = None):
        self._conversations = {c.id: c for c in (conversations or [])}

    async def save(self, conversation: Conversation) -> Conversation:
        self._conversations[conversation.id] = conversation
        return conversation

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self._conversations.get(conversation_id)

    async def list_conversations(
        self, limit: int = 100, offset: int = 0
    ) -> list[Conversation]:
        convs = list(self._conversations.values())
        return convs[offset : offset + limit]

    async def delete(self, conversation_id: UUID) -> None:
        if conversation_id not in self._conversations:
            raise ValueError("Conversation not found")
        del self._conversations[conversation_id]


class _FakeFileStorage(FileStorage):
    def __init__(self, base_path: Path | None = None):
        self._base_path = base_path
        self._files: dict[tuple[UUID, str], bytes] = {}

    async def save(self, document_id: UUID, filename: str, content: bytes) -> Path:
        path = await self.get_path(document_id, filename)
        if self._base_path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self._files[(document_id, filename)] = content
        return path

    async def get_path(self, document_id: UUID, filename: str) -> Path:
        if self._base_path is not None:
            return self._base_path / str(document_id) / filename
        return Path(str(document_id)) / filename

    async def delete(self, document_id: UUID, filename: str) -> None:
        self._files.pop((document_id, filename), None)


def _fake_task_runner(document_id: str, filename: str, content_type: str) -> None:
    """No-op task runner for route tests (avoids the real Celery broker)."""


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_search_engine] = lambda: FakeSearchEngine(
        chunks=[make_fake_chunk()]
    )
    app.dependency_overrides[get_llm_provider_dep] = lambda: FakeLLMProvider()
    app.dependency_overrides[get_document_repository] = lambda: _FakeDocumentRepository()
    app.dependency_overrides[get_conversation_repository] = lambda: _FakeConversationRepository()
    app.dependency_overrides[get_file_storage] = lambda: _FakeFileStorage()
    # Hermetic: never hit the real Celery broker from route tests.
    app.dependency_overrides[get_task_runner] = lambda: _fake_task_runner

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _make_document(
    filename: str = "test.pdf",
    status: DocumentStatus = DocumentStatus.COMPLETED,
) -> Document:
    return Document(
        id=uuid4(),
        filename=filename,
        content_type="application/pdf",
        status=status,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )


def _make_conversation() -> Conversation:
    conv = Conversation(
        id=uuid4(),
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )
    conv.add_message(MessageRole.USER, "Hello")
    return conv


class TestDocumentsRoutes:
    def test_list_documents(self, client: TestClient) -> None:
        repo = _FakeDocumentRepository([_make_document(), _make_document("other.txt")])
        app.dependency_overrides[get_document_repository] = lambda: repo

        response = client.get("/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["documents"][0]["filename"] == "test.pdf"

    def test_get_document(self, client: TestClient) -> None:
        document = _make_document()
        repo = _FakeDocumentRepository([document])
        app.dependency_overrides[get_document_repository] = lambda: repo

        response = client.get(f"/documents/{document.id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(document.id)

    def test_get_missing_document_returns_404(self, client: TestClient) -> None:
        response = client.get(f"/documents/{uuid4()}")
        assert response.status_code == 404

    @patch.object(documents_module.settings, "max_upload_size_mb", 100)
    def test_upload_document(self, client: TestClient) -> None:
        response = client.post(
            "/documents",
            files={"file": ("report.pdf", b"PDF content", "application/pdf")},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["filename"] == "report.pdf"
        assert data["content_type"] == "application/pdf"
        assert data["status"] == "pending"

    @patch.object(documents_module.settings, "max_upload_size_mb", 1)
    def test_upload_oversized_file_returns_413(self, client: TestClient) -> None:
        response = client.post(
            "/documents",
            files={"file": ("large.pdf", b"x" * (2 * 1024 * 1024), "application/pdf")},
        )
        assert response.status_code == 413

    def test_delete_document(self, client: TestClient) -> None:
        document = _make_document()
        repo = _FakeDocumentRepository([document])
        app.dependency_overrides[get_document_repository] = lambda: repo

        response = client.delete(f"/documents/{document.id}")

        assert response.status_code == 204
        assert len(repo._documents) == 0

    def test_delete_missing_document_returns_404(self, client: TestClient) -> None:
        response = client.delete(f"/documents/{uuid4()}")
        assert response.status_code == 404

    def test_download_document(self, client: TestClient, tmp_path: Path) -> None:
        document = _make_document()
        repo = _FakeDocumentRepository([document])
        storage = _FakeFileStorage(tmp_path)
        # Create the file on disk so the route can serve it.
        file_path = tmp_path / str(document.id) / document.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"PDF content")

        app.dependency_overrides[get_document_repository] = lambda: repo
        app.dependency_overrides[get_file_storage] = lambda: storage

        response = client.get(f"/documents/{document.id}/download")

        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("attachment")
        assert response.content == b"PDF content"

    def test_download_missing_document_returns_404(self, client: TestClient) -> None:
        response = client.get(f"/documents/{uuid4()}/download")
        assert response.status_code == 404

    def test_download_missing_file_returns_404(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        document = _make_document()
        repo = _FakeDocumentRepository([document])
        storage = _FakeFileStorage(tmp_path)
        app.dependency_overrides[get_document_repository] = lambda: repo
        app.dependency_overrides[get_file_storage] = lambda: storage

        response = client.get(f"/documents/{document.id}/download")

        assert response.status_code == 404

    def test_reprocess_failed_document_returns_202(self, client: TestClient) -> None:
        document = _make_document()
        document.mark_failed("parse error")
        repo = _FakeDocumentRepository([document])
        app.dependency_overrides[get_document_repository] = lambda: repo

        response = client.post(f"/documents/{document.id}/reprocess")

        assert response.status_code == 202
        assert response.json()["status"] == "pending"

    def test_reprocess_non_failed_document_returns_409(
        self, client: TestClient
    ) -> None:
        document = _make_document(status=DocumentStatus.COMPLETED)
        repo = _FakeDocumentRepository([document])
        app.dependency_overrides[get_document_repository] = lambda: repo

        response = client.post(f"/documents/{document.id}/reprocess")

        assert response.status_code == 409

    def test_reprocess_missing_document_returns_404(self, client: TestClient) -> None:
        response = client.post(f"/documents/{uuid4()}/reprocess")
        assert response.status_code == 404


class TestConversationsRoutes:
    def test_list_conversations(self, client: TestClient) -> None:
        repo = _FakeConversationRepository([_make_conversation(), _make_conversation()])
        app.dependency_overrides[get_conversation_repository] = lambda: repo

        response = client.get("/conversations")

        assert response.status_code == 200
        assert len(response.json()["conversations"]) == 2

    def test_get_conversation(self, client: TestClient) -> None:
        conversation = _make_conversation()
        repo = _FakeConversationRepository([conversation])
        app.dependency_overrides[get_conversation_repository] = lambda: repo

        response = client.get(f"/conversations/{conversation.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(conversation.id)
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"

    def test_get_missing_conversation_returns_404(self, client: TestClient) -> None:
        response = client.get(f"/conversations/{uuid4()}")
        assert response.status_code == 404

    def test_delete_conversation(self, client: TestClient) -> None:
        conversation = _make_conversation()
        repo = _FakeConversationRepository([conversation])
        app.dependency_overrides[get_conversation_repository] = lambda: repo

        response = client.delete(f"/conversations/{conversation.id}")

        assert response.status_code == 204
        assert len(repo._conversations) == 0


class TestChatRoutes:
    def test_chat_returns_answer(self, client: TestClient) -> None:
        response = client.post(
            "/chat",
            json={"question": "What is the dosage?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "model" in data

    def test_chat_stream_returns_ndjson(self, client: TestClient) -> None:
        response = client.post(
            "/chat/stream",
            json={"question": "What is the dosage?"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"
        body = response.content.decode("utf-8")
        assert "done" in body


class TestProvidersRoute:
    @patch.object(
        Settings,
        "configured_llm_providers",
        new_callable=PropertyMock,
        return_value=["openai"],
    )
    def test_list_llm_providers(self, _mock: PropertyMock, client: TestClient) -> None:
        response = client.get("/providers/llm")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
