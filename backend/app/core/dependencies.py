from collections.abc import AsyncIterator
from typing import cast

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.ports.embedding_provider import EmbeddingProvider
from app.domain.ports.file_storage import FileStorage
from app.domain.ports.llm_provider import LLMProvider
from app.domain.ports.task_runner import TaskRunner
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.db.connection import AsyncSessionLocal
from app.infrastructure.db.repositories.postgres_conversation_repository import (
    PostgresConversationRepository,
)
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.embeddings.resilient_provider import get_cached_embedding_provider
from app.infrastructure.llm.factory import get_llm_provider
from app.infrastructure.llm.model_catalog import get_model_config
from app.infrastructure.llm.resilient_provider import ResilientLLMProvider
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.tasks.process_document import process_document


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def get_document_repository(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> DocumentRepository:
    return PostgresDocumentRepository(session)


def get_conversation_repository(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> ConversationRepository:
    return PostgresConversationRepository(session)


def get_file_storage() -> FileStorage:
    return LocalFileStorage()


def get_task_runner() -> TaskRunner:
    """Composition root for the document-processing task queue (Celery)."""
    return cast(TaskRunner, process_document.delay)


def get_llm_provider_dep() -> LLMProvider:
    return ResilientLLMProvider()


def resolve_llm_provider(provider: str | None = None, model: str | None = None) -> LLMProvider:
    """Build an LLM provider for a specific request.

    If neither provider nor model is supplied, falls back to the global
    dependency so existing behaviour and test overrides keep working.
    """
    if provider is None and model is None:
        return get_llm_provider_dep()

    selected_provider = provider or settings.llm_provider

    if selected_provider not in settings.configured_llm_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{selected_provider}' is not configured or has no valid API key.",
        )

    if model is not None and get_model_config(selected_provider, model) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' is not available for provider '{selected_provider}'.",
        )

    return ResilientLLMProvider(primary=get_llm_provider(selected_provider, model=model))


def get_embedding_provider_dep() -> EmbeddingProvider:
    return get_cached_embedding_provider()


def get_search_engine(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider_dep),  # noqa: B008
) -> HybridSearchEngine:
    return HybridSearchEngine(session, embedding_provider=embedding_provider)
