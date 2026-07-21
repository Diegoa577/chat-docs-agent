import json
from unittest.mock import patch

import pytest

from app.application.services.agent_service import AgentService
from app.domain.models.document import Document, DocumentStatus
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine
from mcp_server.server import (
    compare_documents,
    extract_entities,
    list_documents,
    search_documents,
)
from tests.fixtures.fakes import FakeLLMProvider, make_fake_chunk


def _build_fake_agent(search_engine, llm_provider) -> AgentService:
    return AgentService(search_engine=search_engine, llm_provider=llm_provider)


@pytest.mark.asyncio
async def test_search_documents_returns_results():
    with patch.object(
        HybridSearchEngine,
        "search",
        return_value=[make_fake_chunk()],
    ):
        result = await search_documents("inclusion criteria", top_k=3)
        data = json.loads(result)
        assert data["query"] == "inclusion criteria"
        assert len(data["results"]) == 1
        assert data["results"][0]["document_name"] == "fake.pdf"


@pytest.mark.asyncio
async def test_compare_documents_returns_answer():
    with (
        patch.object(
            HybridSearchEngine,
            "search",
            return_value=[make_fake_chunk(document_name="a.pdf")],
        ),
        patch(
            "mcp_server.dependencies.ResilientLLMProvider",
            return_value=FakeLLMProvider(response="Documents are similar."),
        ),
    ):
        result = await compare_documents(
            "Compare safety windows", document_names=["a.pdf", "b.pdf"]
        )
        data = json.loads(result)
        assert data["answer"] == "Documents are similar."
        assert data["documents"] == ["a.pdf", "b.pdf"]


@pytest.mark.asyncio
async def test_extract_entities_returns_answer():
    with (
        patch.object(
            HybridSearchEngine,
            "search",
            return_value=[make_fake_chunk(document_name="protocol.pdf")],
        ),
        patch(
            "mcp_server.dependencies.ResilientLLMProvider",
            return_value=FakeLLMProvider(response="Primary endpoint: ACR20"),
        ),
    ):
        result = await extract_entities("Extract endpoints", document_names=["protocol.pdf"])
        data = json.loads(result)
        assert data["answer"] == "Primary endpoint: ACR20"


@pytest.mark.asyncio
async def test_list_documents_returns_documents():
    documents = [
        Document(
            filename="protocol.pdf", content_type="application/pdf", status=DocumentStatus.COMPLETED
        ),
        Document(
            filename="sop.pdf", content_type="application/pdf", status=DocumentStatus.PROCESSING
        ),
    ]
    with patch.object(
        PostgresDocumentRepository,
        "list_documents",
        return_value=documents,
    ):
        result = await list_documents(limit=10)
        data = json.loads(result)
        assert data["count"] == 2
        assert data["documents"][0]["document_name"] == "protocol.pdf"
        assert data["documents"][0]["status"] == "completed"
        assert data["documents"][1]["status"] == "processing"


@pytest.mark.asyncio
async def test_tool_error_returns_json_error():
    with patch.object(
        HybridSearchEngine,
        "search",
        side_effect=RuntimeError("database unavailable"),
    ):
        result = await search_documents("anything")
        data = json.loads(result)
        assert "error" in data
        assert "database unavailable" in data["error"]
