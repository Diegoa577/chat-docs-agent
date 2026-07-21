import time
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import RETRIEVAL_LATENCY
from app.domain.ports.embedding_provider import EmbeddingProvider
from app.domain.ports.search_engine import SearchEngine
from app.domain.value_objects import RetrievedChunk
from app.infrastructure.db.models import ChunkModel, DocumentModel
from app.infrastructure.embeddings.resilient_provider import get_cached_embedding_provider


class HybridSearchEngine(SearchEngine):
    def __init__(
        self,
        session: AsyncSession | Any,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self._is_async = isinstance(session, AsyncSession)
        self._embedding_provider = embedding_provider or get_cached_embedding_provider()

    async def _execute(self, stmt: Any) -> Any:
        if self._is_async:
            return await self.session.execute(stmt)
        return self.session.execute(stmt)

    async def search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or settings.retrieval_top_k
        alpha = settings.hybrid_alpha
        vector_candidates = max(top_k * 5, 50)

        start_time = time.time()
        embedding = await self._get_query_embedding(query)

        # Keyword search using PostgreSQL FTS
        keyword_stmt = (
            select(
                ChunkModel.id.label("chunk_id"),
                ChunkModel.document_id.label("document_id"),
                ChunkModel.content.label("content"),
                ChunkModel.page_number.label("page_number"),
                ChunkModel.section_title.label("section_title"),
                func.ts_rank_cd(
                    ChunkModel.search_vector,
                    func.plainto_tsquery("english", query),
                ).label("keyword_score"),
            )
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .where(
                ChunkModel.search_vector.bool_op("@@")(func.plainto_tsquery("english", query)),
                DocumentModel.status == "completed",
            )
            .cte("keyword_search")
        )

        # Vector search using pgvector
        vector_stmt = (
            select(
                ChunkModel.id.label("chunk_id"),
                (1 - ChunkModel.embedding.cosine_distance(embedding)).label("vector_score"),
            )
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .where(
                ChunkModel.embedding.is_not(None),
                DocumentModel.status == "completed",
            )
            .order_by(ChunkModel.embedding.cosine_distance(embedding))
            .limit(vector_candidates)
            .cte("vector_search")
        )

        # Combined query
        combined_stmt = (
            select(
                ChunkModel.id.label("chunk_id"),
                ChunkModel.document_id.label("document_id"),
                ChunkModel.content.label("content"),
                ChunkModel.page_number.label("page_number"),
                ChunkModel.section_title.label("section_title"),
                func.coalesce(keyword_stmt.c.keyword_score, 0.0).label("keyword_score"),
                func.coalesce(vector_stmt.c.vector_score, 0.0).label("vector_score"),
                (
                    func.coalesce(keyword_stmt.c.keyword_score, 0.0) * alpha
                    + func.coalesce(vector_stmt.c.vector_score, 0.0) * (1 - alpha)
                ).label("final_score"),
            )
            .select_from(ChunkModel)
            .outerjoin(keyword_stmt, ChunkModel.id == keyword_stmt.c.chunk_id)
            .outerjoin(vector_stmt, ChunkModel.id == vector_stmt.c.chunk_id)
            .where((keyword_stmt.c.chunk_id.is_not(None)) | (vector_stmt.c.chunk_id.is_not(None)))
            .order_by(text("final_score DESC"))
            .limit(top_k)
        )

        result = await self._execute(combined_stmt)
        rows = result.all()

        # Fetch document names
        document_ids = list({row.document_id for row in rows})
        document_names = {}
        if document_ids:
            doc_result = await self._execute(
                select(DocumentModel.id, DocumentModel.filename).where(
                    DocumentModel.id.in_(document_ids)
                )
            )
            document_names = {row.id: row.filename for row in doc_result.all()}

        RETRIEVAL_LATENCY.observe(time.time() - start_time)

        return [
            RetrievedChunk(
                chunk_id=str(row.chunk_id),
                document_id=str(row.document_id),
                document_name=document_names.get(row.document_id, "Unknown"),
                content=row.content,
                page_number=row.page_number,
                section_title=row.section_title,
                keyword_score=float(row.keyword_score),
                vector_score=float(row.vector_score),
                final_score=float(row.final_score),
            )
            for row in rows
        ]

    async def _get_query_embedding(self, query: str) -> list[float]:
        embeddings = await self._embedding_provider.embed([query])
        return embeddings[0]
