from unittest.mock import patch

import pytest

from app.core.config import settings
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine


@pytest.mark.asyncio
async def test_hybrid_search_returns_relevant_chunks(db_session, seeded_document):
    search_engine = HybridSearchEngine(db_session)

    with patch.object(
        HybridSearchEngine,
        "_get_query_embedding",
        return_value=[0.15] * settings.embedding_dimension,
    ):
        results = await search_engine.search("inclusion criteria", top_k=5)

    assert len(results) > 0
    contents = " ".join(chunk.content.lower() for chunk in results)
    assert "inclusion" in contents


@pytest.mark.asyncio
async def test_hybrid_search_excludes_processing_documents(db_session, seeded_document):
    # Mark the seeded document as processing.
    seeded_document.status = "processing"
    db_session.commit()

    search_engine = HybridSearchEngine(db_session)

    with patch.object(
        HybridSearchEngine,
        "_get_query_embedding",
        return_value=[0.15] * settings.embedding_dimension,
    ):
        results = await search_engine.search("inclusion criteria", top_k=5)

    assert len(results) == 0
