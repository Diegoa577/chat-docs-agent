from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.services.agent_service import AgentService
from app.infrastructure.db.connection import async_engine
from app.infrastructure.llm.resilient_provider import ResilientLLMProvider
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine


@asynccontextmanager
async def get_mcp_session() -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


def build_agent_service(session: AsyncSession) -> AgentService:
    """Build an AgentService wired with resilient providers for MCP tools."""
    return AgentService(
        search_engine=HybridSearchEngine(session),
        llm_provider=ResilientLLMProvider(),
    )
