from pathlib import Path
from uuid import UUID

import pytest

from app.application.services.chunking_service import ChunkingService
from app.application.services.ingestion_service import IngestionService
from app.domain.models.chunk import Chunk
from app.domain.models.document import Document, DocumentStatus
from app.domain.ports.document_parser import DocumentParser
from app.domain.ports.embedding_provider import EmbeddingProvider
from app.domain.ports.file_storage import FileStorage
from app.domain.repositories.document_repository import DocumentRepository


class FakeDocumentRepository(DocumentRepository):
    def __init__(self):
        self.documents: dict[UUID, Document] = {}
        self.chunks: dict[UUID, list[Chunk]] = {}
        self.deleted_chunks: list[UUID] = []

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

    async def save_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        for chunk in chunks:
            self.chunks.setdefault(chunk.document_id, []).append(chunk)
        return chunks

    async def delete_chunks_by_document(self, document_id: UUID) -> None:
        self.deleted_chunks.append(document_id)
        self.chunks.pop(document_id, None)

    async def update_search_vectors(self, document_id: UUID) -> None:
        pass

    async def delete(self, document_id: UUID) -> None:
        self.documents.pop(document_id, None)


class FakeFileStorage(FileStorage):
    def __init__(self):
        self.files: dict[UUID, bytes] = {}

    async def save(self, document_id: UUID, filename: str, content: bytes) -> Path:
        self.files[document_id] = content
        return Path(f"/tmp/{document_id}/{filename}")

    async def get_path(self, document_id: UUID, filename: str) -> Path:
        return Path(f"/tmp/{document_id}/{filename}")

    async def delete(self, document_id: UUID, filename: str) -> None:
        self.files.pop(document_id, None)


class FakeDocumentParser(DocumentParser):
    def __init__(self, pages: list[dict[str, str | int | None]] | None = None):
        self.pages = (
            pages
            if pages is not None
            else [
                {
                    "page_number": 1,
                    "section_title": "Introduction",
                    "text": "This is the introduction. It has enough text to form a chunk.",
                }
            ]
        )

    def parse(self, file_path: Path, content_type: str) -> list[dict[str, str | int | None]]:
        return self.pages


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.dimension for _ in texts]

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return "fake-embedding"


@pytest.fixture
def ingestion_service():
    repository = FakeDocumentRepository()
    file_storage = FakeFileStorage()
    parser = FakeDocumentParser()
    chunking_service = ChunkingService(chunk_size=20, chunk_overlap=2)
    embedding_provider = FakeEmbeddingProvider()

    service = IngestionService(
        document_repository=repository,
        file_storage=file_storage,
        parser=parser,
        chunking_service=chunking_service,
        embedding_provider=embedding_provider,
    )
    return service, repository


@pytest.mark.asyncio
async def test_ingest_document_completes_successfully(ingestion_service):
    service, repository = ingestion_service
    document = Document(filename="test.txt", content_type="text/plain")
    await repository.save(document)

    result = await service.ingest_document(document.id, "test.txt", "text/plain")

    assert result["status"] == DocumentStatus.COMPLETED.value
    assert result["chunks_count"] > 0

    updated = await repository.get_by_id(document.id)
    assert updated is not None
    assert updated.status == DocumentStatus.COMPLETED


@pytest.mark.asyncio
async def test_ingest_document_marks_failed_on_error(ingestion_service):
    service, repository = ingestion_service
    document = Document(filename="test.txt", content_type="text/plain")
    await repository.save(document)

    # Force parser to return no text.
    service.parser = FakeDocumentParser(pages=[])

    with pytest.raises(ValueError, match="No text could be extracted"):
        await service.ingest_document(document.id, "test.txt", "text/plain")

    updated = await repository.get_by_id(document.id)
    assert updated is not None
    assert updated.status == DocumentStatus.FAILED


@pytest.mark.asyncio
async def test_ingest_document_is_idempotent(ingestion_service):
    service, repository = ingestion_service
    document = Document(filename="test.txt", content_type="text/plain")
    await repository.save(document)

    await service.ingest_document(document.id, "test.txt", "text/plain")
    first_chunks = len(repository.chunks.get(document.id, []))

    await service.ingest_document(document.id, "test.txt", "text/plain")
    second_chunks = len(repository.chunks.get(document.id, []))

    assert first_chunks == second_chunks
    assert repository.deleted_chunks.count(document.id) == 2
