from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.conversation import (
    ConversationListResponse,
    ConversationResponse,
)
from app.application.services.conversation_service import ConversationService
from app.core.dependencies import get_conversation_repository
from app.domain.repositories.conversation_repository import ConversationRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service(
    repository: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> ConversationService:
    return ConversationService(repository)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    limit: int = 100,
    offset: int = 0,
) -> ConversationListResponse:
    conversations = await service.list_conversations(limit=limit, offset=offset)
    return ConversationListResponse(
        conversations=[
            ConversationResponse.model_validate(service.conversation_to_dict(conversation))
            for conversation in conversations
        ]
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationResponse.model_validate(service.conversation_to_dict(conversation))


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    try:
        await service.delete_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
