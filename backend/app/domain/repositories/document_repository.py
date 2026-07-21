from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models.chunk import Chunk
from app.domain.models.document import Document


class DocumentRepository(ABC):
    @abstractmethod
    async def save(self, document: Document) -> Document:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None:
        raise NotImplementedError

    @abstractmethod
    async def list_documents(self, limit: int = 100, offset: int = 0) -> list[Document]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, document: Document) -> Document:
        raise NotImplementedError

    @abstractmethod
    async def save_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        raise NotImplementedError

    @abstractmethod
    async def delete_chunks_by_document(self, document_id: UUID) -> None:
        """Delete all chunks for a document (used for idempotent reprocessing)."""
        raise NotImplementedError

    @abstractmethod
    async def update_search_vectors(self, document_id: UUID) -> None:
        """Populate TSVECTOR search_vector for all chunks of a document."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: UUID) -> None:
        """Delete a document and its associated chunks."""
        raise NotImplementedError
