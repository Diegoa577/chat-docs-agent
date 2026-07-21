from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.chunk import Chunk
from app.domain.models.document import Document
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.db.mappers import (
    chunk_from_model,
    chunk_to_model,
    document_from_model,
    document_to_model,
)
from app.infrastructure.db.models import DocumentModel


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, document: Document) -> Document:
        model = document_to_model(document)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return document_from_model(model)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        return document_from_model(model) if model else None

    async def list_documents(self, limit: int = 100, offset: int = 0) -> list[Document]:
        result = await self.session.execute(
            select(DocumentModel)
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [document_from_model(model) for model in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        model = await self.session.get(DocumentModel, document.id)
        if not model:
            raise ValueError(f"Document {document.id} not found")

        model.status = document.status
        model.error_message = document.error_message
        model.metadata_ = document.metadata
        model.updated_at = document.updated_at

        await self.session.commit()
        await self.session.refresh(model)
        return document_from_model(model)

    async def save_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        models = [chunk_to_model(chunk) for chunk in chunks]
        self.session.add_all(models)
        await self.session.commit()
        for model in models:
            await self.session.refresh(model)
        return [chunk_from_model(model) for model in models]

    async def delete_chunks_by_document(self, document_id: UUID) -> None:
        await self.session.execute(
            text("DELETE FROM chunks WHERE document_id = :document_id"),
            {"document_id": str(document_id)},
        )
        await self.session.commit()

    async def update_search_vectors(self, document_id: UUID) -> None:
        await self.session.execute(
            text("""
                UPDATE chunks
                SET search_vector = to_tsvector('english', content)
                WHERE document_id = :document_id AND search_vector IS NULL
            """),
            {"document_id": str(document_id)},
        )
        await self.session.commit()

    async def delete(self, document_id: UUID) -> None:
        model = await self.session.get(DocumentModel, document_id)
        if not model:
            raise ValueError(f"Document {document_id} not found")

        await self.session.delete(model)
        await self.session.commit()
