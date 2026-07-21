from typing import Any
from uuid import UUID

import structlog

from app.application.services.chunking_service import ChunkingService
from app.domain.models.document import DocumentStatus
from app.domain.ports.document_parser import DocumentParser
from app.domain.ports.embedding_provider import EmbeddingProvider
from app.domain.ports.file_storage import FileStorage
from app.domain.repositories.document_repository import DocumentRepository

logger = structlog.get_logger()


class IngestionService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage: FileStorage,
        parser: DocumentParser,
        chunking_service: ChunkingService,
        embedding_provider: EmbeddingProvider,
    ):
        self.document_repository = document_repository
        self.file_storage = file_storage
        self.parser = parser
        self.chunking_service = chunking_service
        self.embedding_provider = embedding_provider

    async def ingest_document(
        self, document_id: UUID, filename: str, content_type: str
    ) -> dict[str, Any]:
        """End-to-end ingestion: parse, chunk, embed, store, and index a document."""
        logger.info(
            "Starting document ingestion",
            document_id=str(document_id),
            filename=filename,
            content_type=content_type,
        )

        document = await self.document_repository.get_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.mark_processing()
        await self.document_repository.update(document)

        try:
            file_path = await self.file_storage.get_path(document_id, filename)
            pages = self.parser.parse(file_path, content_type)

            chunks = self.chunking_service.chunk_pages(document_id, pages)
            if not chunks:
                raise ValueError("No text could be extracted from the document")

            embeddings = await self.embedding_provider.embed([chunk.content for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise ValueError(
                    f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks"
                )

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                # Store the embedding vector in the chunk metadata until persistence;
                # the domain model does not hold it, so we pass it via the repo if needed.
                # Here we attach it to metadata temporarily for the repository to consume.
                chunk.metadata["embedding"] = embedding

            # Idempotent: remove any previous chunks before inserting the new ones.
            await self.document_repository.delete_chunks_by_document(document_id)
            saved_chunks = await self.document_repository.save_chunks(chunks)
            await self.document_repository.update_search_vectors(document_id)

            document.mark_completed()
            document.metadata["chunks_count"] = len(saved_chunks)
            document.metadata["embedding_model"] = self.embedding_provider.get_model_name()
            await self.document_repository.update(document)

            logger.info(
                "Document ingestion completed",
                document_id=str(document_id),
                chunks_count=len(saved_chunks),
            )

            return {
                "document_id": str(document_id),
                "status": DocumentStatus.COMPLETED.value,
                "chunks_count": len(saved_chunks),
            }

        except Exception as exc:
            logger.error(
                "Document ingestion failed",
                document_id=str(document_id),
                error=str(exc),
            )
            document.mark_failed(str(exc))
            await self.document_repository.update(document)
            raise
