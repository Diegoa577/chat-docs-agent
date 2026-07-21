from pathlib import Path
from uuid import UUID

from app.domain.models.document import Document, DocumentStatus
from app.domain.ports.file_storage import FileStorage
from app.domain.ports.task_runner import TaskRunner
from app.domain.repositories.document_repository import DocumentRepository


class DocumentStateConflictError(Exception):
    """Raised when an operation is not allowed for the document's current status."""


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage: FileStorage,
        task_runner: TaskRunner,
    ):
        self.document_repository = document_repository
        self.file_storage = file_storage
        self.task_runner = task_runner

    async def upload_document(self, filename: str, content_type: str, content: bytes) -> Document:
        document = Document(
            filename=filename,
            content_type=content_type,
            metadata={"file_size_bytes": len(content)},
        )
        saved_document = await self.document_repository.save(document)
        await self.file_storage.save(saved_document.id, filename, content)

        # Trigger async processing. If the broker is unreachable the document
        # must not stay "pending" forever: mark it failed and propagate.
        try:
            self.task_runner(
                str(saved_document.id),
                filename,
                content_type,
            )
        except Exception as exc:
            saved_document.mark_failed(f"Failed to enqueue processing task: {exc}")
            await self.document_repository.update(saved_document)
            raise

        return saved_document

    async def get_document(self, document_id: UUID) -> Document | None:
        return await self.document_repository.get_by_id(document_id)

    async def get_document_file(self, document_id: UUID) -> tuple[Path, str, str] | None:
        document = await self.document_repository.get_by_id(document_id)
        if not document:
            return None

        path = await self.file_storage.get_path(document_id, document.filename)
        if not path.exists():
            return None

        return path, document.filename, document.content_type

    async def list_documents(self, limit: int = 100, offset: int = 0) -> list[Document]:
        return await self.document_repository.list_documents(limit=limit, offset=offset)

    async def reprocess_document(self, document_id: UUID) -> Document:
        document = await self.document_repository.get_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.status != DocumentStatus.FAILED:
            raise DocumentStateConflictError(
                f"Document {document_id} is '{document.status}'; "
                "only failed documents can be reprocessed"
            )

        document.reset_for_reprocessing()
        await self.document_repository.update(document)

        # Re-enqueue processing with the stored filename/content_type. If the
        # broker is unreachable the document must not stay "pending" forever:
        # mark it failed again and propagate.
        try:
            self.task_runner(
                str(document.id),
                document.filename,
                document.content_type,
            )
        except Exception as exc:
            document.mark_failed(f"Failed to enqueue processing task: {exc}")
            await self.document_repository.update(document)
            raise

        return document

    async def delete_document(self, document_id: UUID) -> None:
        document = await self.document_repository.get_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Delete the file first: if storage fails, the database row still
        # points at the file and the delete can be retried. The reverse order
        # would leave an orphaned file behind a deleted row.
        await self.file_storage.delete(document_id, document.filename)
        await self.document_repository.delete(document_id)
