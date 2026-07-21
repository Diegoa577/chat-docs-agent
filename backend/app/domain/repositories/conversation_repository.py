from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models.conversation import Conversation


class ConversationRepository(ABC):
    @abstractmethod
    async def save(self, conversation: Conversation) -> Conversation:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        raise NotImplementedError

    @abstractmethod
    async def list_conversations(self, limit: int = 100, offset: int = 0) -> list[Conversation]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> None:
        raise NotImplementedError
