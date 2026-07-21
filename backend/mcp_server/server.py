import json

import structlog
from fastmcp import FastMCP

from app.core.config import settings
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.llm.model_catalog import initialise_catalog
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine
from mcp_server.dependencies import build_agent_service, get_mcp_session

logger = structlog.get_logger()

# The MCP server is a separate entry point: it owns the model-catalog bootstrap
# (same as app/main.py) so app/core/config.py stays infrastructure-free.
initialise_catalog(settings.models_catalog_path)

mcp = FastMCP("clinical-document-agent")


@mcp.tool()
async def search_documents(query: str, top_k: int = 5) -> str:
    """Search clinical/regulatory documents using hybrid retrieval.

    Returns relevant excerpts with document names, page numbers, and section titles.
    """
    try:
        async with get_mcp_session() as session:
            search_engine = HybridSearchEngine(session)
            chunks = await search_engine.search(query, top_k=top_k)
            results = [
                {
                    "document_name": chunk.document_name,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "excerpt": chunk.content[:500],
                    "score": chunk.final_score,
                }
                for chunk in chunks
            ]
            return json.dumps({"query": query, "results": results}, indent=2)
    except Exception as exc:
        logger.error("mcp_tool_error", tool="search_documents", error=str(exc))
        return json.dumps({"error": f"search_documents failed: {exc}"})


@mcp.tool()
async def compare_documents(query: str, document_names: list[str]) -> str:
    """Compare two or more clinical/regulatory documents.

    Provide the comparison question and the names of the documents to compare.
    """
    try:
        async with get_mcp_session() as session:
            agent = build_agent_service(session)
            result = await agent.compare(query, document_names=document_names)
            return json.dumps(
                {
                    "query": query,
                    "documents": document_names,
                    "answer": result.answer,
                    "confidence": result.confidence,
                    "citations": [c.to_dict() for c in result.citations],
                },
                indent=2,
            )
    except Exception as exc:
        logger.error("mcp_tool_error", tool="compare_documents", error=str(exc))
        return json.dumps({"error": f"compare_documents failed: {exc}"})


@mcp.tool()
async def extract_entities(query: str, document_names: list[str] | None = None) -> str:
    """Extract structured regulatory entities from clinical documents.

    Provide an optional query and the names of the documents to analyze.
    """
    try:
        async with get_mcp_session() as session:
            agent = build_agent_service(session)
            result = await agent.extract(query, document_names=document_names or [])
            return json.dumps(
                {
                    "query": query,
                    "documents": document_names,
                    "answer": result.answer,
                    "confidence": result.confidence,
                    "citations": [c.to_dict() for c in result.citations],
                },
                indent=2,
            )
    except Exception as exc:
        logger.error("mcp_tool_error", tool="extract_entities", error=str(exc))
        return json.dumps({"error": f"extract_entities failed: {exc}"})


@mcp.tool()
async def list_documents(limit: int = 20) -> str:
    """List ingested documents with their processing status.

    Returns the most recent documents (newest first) including filename,
    status (pending/processing/completed/failed), and chunk count metadata.
    """
    try:
        async with get_mcp_session() as session:
            repository = PostgresDocumentRepository(session)
            documents = await repository.list_documents(limit=limit)
            results = [
                {
                    "document_name": doc.filename,
                    "status": doc.status.value,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                for doc in documents
            ]
            return json.dumps({"count": len(results), "documents": results}, indent=2)
    except Exception as exc:
        logger.error("mcp_tool_error", tool="list_documents", error=str(exc))
        return json.dumps({"error": f"list_documents failed: {exc}"})


if __name__ == "__main__":
    mcp.run()
