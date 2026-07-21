import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.services.chunking_service import ChunkingService
from app.application.services.ingestion_service import IngestionService
from app.core.config import settings
from app.core.metrics import DOCUMENTS_PROCESSED, INGESTION_ERRORS
from app.domain.models.document import DocumentStatus
from app.infrastructure.db.connection import _normalize_async_url
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.embeddings.factory import get_embedding_provider
from app.infrastructure.parsers.document_parser import get_parser
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.infrastructure.workers.celery_app import celery_app

logger = structlog.get_logger()

PROCESSING_TIMEOUT_MINUTES = 10


async def _process_document_async(
    document_id: UUID, filename: str, content_type: str
) -> dict[str, Any]:
    # Create engine inside the async task to avoid event-loop conflicts in forked Celery workers.
    engine = create_async_engine(
        _normalize_async_url(settings.database_url), echo=False, future=True
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        repository = PostgresDocumentRepository(session)
        file_storage = LocalFileStorage()

        document = await repository.get_by_id(document_id)
        if not document:
            logger.error("document_not_found", document_id=str(document_id))
            raise ValueError(f"Document {document_id} not found")

        # Idempotency: skip already completed documents.
        if document.status == DocumentStatus.COMPLETED:
            logger.info("document_already_completed", document_id=str(document_id))
            return {
                "document_id": str(document_id),
                "status": DocumentStatus.COMPLETED.value,
                "chunks_count": document.metadata.get("chunks_count", 0),
            }

        # Concurrency guard: skip if another worker is actively processing.
        if document.status == DocumentStatus.PROCESSING:
            updated_at = document.updated_at
            now = datetime.now(UTC).replace(tzinfo=None)
            if updated_at and (now - updated_at).total_seconds() < PROCESSING_TIMEOUT_MINUTES * 60:
                logger.warning(
                    "document_already_processing",
                    document_id=str(document_id),
                    updated_at=str(updated_at),
                )
                raise ValueError(f"Document {document_id} is already being processed")

        parser = get_parser()
        chunking_service = ChunkingService()
        embedding_provider = get_embedding_provider()

        ingestion_service = IngestionService(
            document_repository=repository,
            file_storage=file_storage,
            parser=parser,
            chunking_service=chunking_service,
            embedding_provider=embedding_provider,
        )

        try:
            result = await ingestion_service.ingest_document(document_id, filename, content_type)
            DOCUMENTS_PROCESSED.labels(status=str(result.get("status", "completed"))).inc()
            return result
        finally:
            await engine.dispose()


@celery_app.task(bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_document(
    self: Task, document_id: str, filename: str, content_type: str
) -> dict[str, Any]:
    """Celery task to process a document: parse, chunk, embed, and store."""
    doc_id = UUID(document_id)
    try:
        return asyncio.run(_process_document_async(doc_id, filename, content_type))
    except Exception as exc:
        logger.error(
            "Document processing failed",
            document_id=document_id,
            error=str(exc),
            retry=self.request.retries,
        )
        if self.request.retries >= self.max_retries:
            INGESTION_ERRORS.inc()
            DOCUMENTS_PROCESSED.labels(status=DocumentStatus.FAILED.value).inc()
            # Keep the uploaded file on disk so the user can retry later via
            # POST /documents/{id}/reprocess. The file is only removed when the
            # document itself is deleted (DELETE /documents/{id}).
            logger.info(
                "document_processing_failed_file_retained",
                document_id=document_id,
                filename=filename,
            )

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from exc
