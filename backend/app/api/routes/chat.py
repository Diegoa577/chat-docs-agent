import json
from collections.abc import AsyncIterator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies.rate_limiter import check_chat_rate_limit
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.application.services.chat_service import ChatService
from app.core.dependencies import (
    get_conversation_repository,
    get_llm_provider_dep,
    get_search_engine,
    resolve_llm_provider,
)
from app.domain.ports.llm_provider import LLMProvider
from app.domain.repositories.conversation_repository import ConversationRepository
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine

logger = structlog.get_logger()

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_llm_provider_for_request(
    chat_request: ChatRequest,
    default_provider: Annotated[LLMProvider, Depends(get_llm_provider_dep)],
) -> LLMProvider:
    """Return the LLM provider for the request, honouring FastAPI overrides.

    When the caller does not request a specific provider/model, the globally
    configured provider dependency is used. This lets integration tests inject
    a fake provider via ``app.dependency_overrides[get_llm_provider_dep]``.
    """
    if chat_request.provider or chat_request.model:
        return resolve_llm_provider(chat_request.provider, chat_request.model)
    return default_provider


@router.post("", response_model=ChatResponse)
async def chat(
    http_request: Request,
    chat_request: ChatRequest,
    search_engine: Annotated[HybridSearchEngine, Depends(get_search_engine)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
    llm_provider: Annotated[LLMProvider, Depends(_get_llm_provider_for_request)],
) -> ChatResponse:
    check_chat_rate_limit(http_request)
    service = ChatService(
        search_engine=search_engine,
        conversation_repository=conversation_repository,
        llm_provider=llm_provider,
    )
    try:
        result = await service.ask(
            question=chat_request.question,
            conversation_id=chat_request.conversation_id,
            strict_mode=chat_request.strict_mode,
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("chat_request_failed", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request.",
        ) from exc


async def _stream_events(service: ChatService, chat_request: ChatRequest) -> AsyncIterator[str]:
    try:
        async for event in service.ask_stream(
            question=chat_request.question,
            conversation_id=chat_request.conversation_id,
            strict_mode=chat_request.strict_mode,
        ):
            yield f"{json.dumps(event)}\n"
    except Exception as exc:
        logger.error("chat_stream_failed", error=str(exc), exc_info=True)
        yield f"{json.dumps({'type': 'error', 'detail': 'Error processing chat request.'})}\n"


@router.post("/stream")
async def chat_stream(
    http_request: Request,
    chat_request: ChatRequest,
    search_engine: Annotated[HybridSearchEngine, Depends(get_search_engine)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
    llm_provider: Annotated[LLMProvider, Depends(_get_llm_provider_for_request)],
) -> StreamingResponse:
    check_chat_rate_limit(http_request)
    service = ChatService(
        search_engine=search_engine,
        conversation_repository=conversation_repository,
        llm_provider=llm_provider,
    )
    return StreamingResponse(
        _stream_events(service, chat_request),
        media_type="application/x-ndjson",
    )
