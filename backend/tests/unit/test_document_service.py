from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.application.services.document_service import (
    DocumentService,
    DocumentStateConflictError,
)
from app.domain.models.document import Document, DocumentStatus
from app.domain.ports.file_storage import FileStorage
from app.domain.repositories.document_repository import DocumentRepository


class FakeDocumentRepository(DocumentRepository):
    def __init__(self):
        self.documents: dict[UUID, Document] = {}
        self.deleted: list[UUID] = []

    async def save(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self.documents.get(document_id)

    async def list_documents(self, limit: int = 100, offset: int = 0) -> list[Document]:
        return list(self.documents.values())

    async def update(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def save_chunks(self, chunks: list) -> list:
        return chunks

    async def delete_chunks_by_document(self, document_id: UUID) -> None:
        pass

    async def update_search_vectors(self, document_id: UUID) -> None:
        pass

    async def delete(self, document_id: UUID) -> None:
        self.deleted.append(document_id)
        self.documents.pop(document_id, None)


class FakeFileStorage(FileStorage):
    def __init__(self):
        self.saved: dict[UUID, bytes] = {}
        self.deleted: list[UUID] = []
        self.paths: dict[UUID, Path] = {}

    async def save(self, document_id: UUID, filename: str, content: bytes):
        self.saved[document_id] = content

    async def get_path(self, document_id: UUID, filename: str):
        if document_id in self.paths:
            return self.paths[document_id]
        return Path("/tmp") / str(document_id) / filename

    async def delete(self, document_id: UUID, filename: str) -> None:
        self.deleted.append(document_id)
        self.saved.pop(document_id, None)


@pytest.fixture
def document_service():
    repository = FakeDocumentRepository()
    file_storage = FakeFileStorage()
    task_calls: list[tuple[str, str, str]] = []

    def fake_task_runner(document_id: str, filename: str, content_type: str) -> None:
        task_calls.append((document_id, filename, content_type))

    service = DocumentService(
        document_repository=repository,
        file_storage=file_storage,
        task_runner=fake_task_runner,
    )
    return service, repository, file_storage, task_calls


@pytest.mark.asyncio
async def test_upload_document_persists_and_triggers_task(document_service):
    service, repository, file_storage, task_calls = document_service

    document = await service.upload_document(
        filename="protocol.txt",
        content_type="text/plain",
        content=b"Inclusion criteria: adult patients.",
    )

    assert document.filename == "protocol.txt"
    assert document.status == DocumentStatus.PENDING
    assert document.metadata["file_size_bytes"] == len(b"Inclusion criteria: adult patients.")
    assert repository.documents[document.id] is not None
    assert file_storage.saved[document.id] == b"Inclusion criteria: adult patients."
    assert len(task_calls) == 1
    assert task_calls[0][0] == str(document.id)


@pytest.mark.asyncio
async def test_get_document_returns_document(document_service):
    service, repository, *_ = document_service
    document = Document(filename="test.txt", content_type="text/plain")
    await repository.save(document)

    result = await service.get_document(document.id)
    assert result is not None
    assert result.filename == "test.txt"


@pytest.mark.asyncio
async def test_get_document_returns_none_when_missing(document_service):
    service, *_ = document_service
    result = await service.get_document(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_documents(document_service):
    service, repository, *_ = document_service
    await repository.save(Document(filename="a.txt", content_type="text/plain"))
    await repository.save(Document(filename="b.txt", content_type="text/plain"))

    results = await service.list_documents()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_document_file_returns_path_filename_and_content_type(document_service, tmp_path):
    service, repository, file_storage, _ = document_service
    document = Document(filename="report.pdf", content_type="application/pdf")
    await repository.save(document)
    file_path = tmp_path / "report.pdf"
    file_path.write_bytes(b"pdf-bytes")
    file_storage.paths[document.id] = file_path

    result = await service.get_document_file(document.id)

    assert result == (file_path, "report.pdf", "application/pdf")


@pytest.mark.asyncio
async def test_get_document_file_returns_none_when_document_missing(document_service):
    service, *_ = document_service
    result = await service.get_document_file(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_document_file_returns_none_when_file_missing_on_disk(document_service):
    service, repository, *_ = document_service
    document = Document(filename="missing.txt", content_type="text/plain")
    await repository.save(document)

    result = await service.get_document_file(document.id)

    assert result is None


@pytest.mark.asyncio
async def test_delete_document_removes_document_and_file(document_service):
    service, repository, file_storage, _ = document_service
    document = Document(filename="test.txt", content_type="text/plain")
    await repository.save(document)
    await file_storage.save(document.id, "test.txt", b"content")

    await service.delete_document(document.id)

    assert document.id in repository.deleted
    assert document.id in file_storage.deleted
    assert await repository.get_by_id(document.id) is None


@pytest.mark.asyncio
async def test_delete_missing_document_raises(document_service):
    service, *_ = document_service
    with pytest.raises(ValueError, match="not found"):
        await service.delete_document(uuid4())


@pytest.mark.asyncio
async def test_reprocess_failed_document_resets_and_reenqueues(document_service):
    service, repository, _, task_calls = document_service
    document = Document(filename="protocol.txt", content_type="text/plain")
    document.mark_failed("transient parse error")
    await repository.save(document)

    result = await service.reprocess_document(document.id)

    assert result.status == DocumentStatus.PENDING
    assert result.error_message is None
    assert task_calls == [(str(document.id), "protocol.txt", "text/plain")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [DocumentStatus.PENDING, DocumentStatus.PROCESSING, DocumentStatus.COMPLETED],
)
async def test_reprocess_non_failed_document_raises_conflict(document_service, status):
    service, repository, _, task_calls = document_service
    document = Document(filename="protocol.txt", content_type="text/plain", status=status)
    await repository.save(document)

    with pytest.raises(DocumentStateConflictError, match="only failed documents"):
        await service.reprocess_document(document.id)

    assert task_calls == []
    assert document.status == status


@pytest.mark.asyncio
async def test_reprocess_missing_document_raises(document_service):
    service, *_ = document_service
    with pytest.raises(ValueError, match="not found"):
        await service.reprocess_document(uuid4())


@pytest.mark.asyncio
async def test_reprocess_marks_document_failed_again_when_enqueue_fails():
    repository = FakeDocumentRepository()
    file_storage = FakeFileStorage()
    document = Document(filename="protocol.txt", content_type="text/plain")
    document.mark_failed("transient parse error")
    await repository.save(document)

    def failing_task_runner(document_id: str, filename: str, content_type: str) -> None:
        raise ConnectionError("broker unreachable")

    service = DocumentService(
        document_repository=repository,
        file_storage=file_storage,
        task_runner=failing_task_runner,
    )

    with pytest.raises(ConnectionError, match="broker unreachable"):
        await service.reprocess_document(document.id)

    assert document.status == DocumentStatus.FAILED
    assert "Failed to enqueue processing task" in (document.error_message or "")


@pytest.mark.asyncio
async def test_upload_marks_document_failed_when_task_enqueue_fails():
    repository = FakeDocumentRepository()
    file_storage = FakeFileStorage()

    def failing_task_runner(document_id: str, filename: str, content_type: str) -> None:
        raise ConnectionError("broker unreachable")

    service = DocumentService(
        document_repository=repository,
        file_storage=file_storage,
        task_runner=failing_task_runner,
    )

    with pytest.raises(ConnectionError, match="broker unreachable"):
        await service.upload_document("protocol.txt", "text/plain", b"content")

    document = next(iter(repository.documents.values()))
    assert document.status == DocumentStatus.FAILED
    assert "Failed to enqueue processing task" in (document.error_message or "")
