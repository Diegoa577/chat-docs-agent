from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.conversation import Conversation
from app.domain.repositories.conversation_repository import ConversationRepository
from app.infrastructure.db.mappers import conversation_from_model, conversation_to_model
from app.infrastructure.db.models import ConversationModel


class PostgresConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, conversation: Conversation) -> Conversation:
        model = conversation_to_model(conversation)
        persistent_model = await self.session.merge(model)
        await self.session.commit()
        await self.session.refresh(persistent_model)
        return conversation_from_model(persistent_model)

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        return conversation_from_model(model) if model else None

    async def list_conversations(self, limit: int = 100, offset: int = 0) -> list[Conversation]:
        result = await self.session.execute(
            select(ConversationModel)
            .order_by(ConversationModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [conversation_from_model(model) for model in result.scalars().all()]

    async def delete(self, conversation_id: UUID) -> None:
        model = await self.session.get(ConversationModel, conversation_id)
        if not model:
            raise ValueError(f"Conversation {conversation_id} not found")
        await self.session.delete(model)
        await self.session.commit()
