from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class MessageResponse(BaseModel):
    role: str
    content: str
    metadata: dict[str, Any]


class ConversationResponse(BaseModel):
    id: UUID
    messages: list[MessageResponse]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
