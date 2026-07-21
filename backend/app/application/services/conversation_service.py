from typing import Any
from uuid import UUID

from app.domain.models.conversation import Conversation
from app.domain.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    async def list_conversations(self, limit: int = 100, offset: int = 0) -> list[Conversation]:
        return await self.repository.list_conversations(limit=limit, offset=offset)

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        return await self.repository.get_by_id(conversation_id)

    async def delete_conversation(self, conversation_id: UUID) -> None:
        await self.repository.delete(conversation_id)

    @staticmethod
    def conversation_to_dict(conversation: Conversation) -> dict[str, Any]:
        return {
            "id": conversation.id,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                    "metadata": message.metadata,
                }
                for message in conversation.messages
            ],
            "metadata": conversation.metadata,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }
