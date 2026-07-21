from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import structlog

from app.application.services.agent_service import AgentService
from app.application.services.guardrails import apply_guardrails
from app.domain.models.conversation import Conversation, MessageRole
from app.domain.ports.llm_provider import LLMProvider
from app.domain.ports.search_engine import SearchEngine
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.value_objects import (
    AgentChunkEvent,
    AgentDoneEvent,
    AgentMetadataEvent,
    AgentStreamEvent,
)

logger = structlog.get_logger()

MAX_HISTORY_MESSAGES = 10


class ChatService:
    def __init__(
        self,
        search_engine: SearchEngine,
        conversation_repository: ConversationRepository,
        llm_provider: LLMProvider,
    ):
        self.agent = AgentService(
            search_engine=search_engine,
            llm_provider=llm_provider,
        )
        self.conversation_repository = conversation_repository

    async def ask(
        self,
        question: str,
        conversation_id: UUID | None = None,
        strict_mode: bool = False,
    ) -> dict[str, Any]:
        conversation = await self._get_or_create_conversation(conversation_id)
        conversation.add_message(MessageRole.USER, question)

        allowed, rejection_message, guardrail_category = apply_guardrails(question)
        if not allowed:
            answer = await self._persist_guardrail_rejection(
                conversation, rejection_message, guardrail_category
            )
            return {
                "conversation_id": conversation.id,
                "answer": answer,
                "citations": [],
                "confidence": "low",
                "model": self.agent.llm_provider.get_model_name(),
            }

        result = await self.agent.handle(
            question, history=conversation.messages[:-1][-MAX_HISTORY_MESSAGES:]
        )

        # Strict mode requires high-confidence answers grounded in retrieved context.
        answer = result.answer
        if strict_mode and result.confidence != "high":
            answer = (
                "I don't have enough information to answer with high confidence in strict mode."
            )

        assistant_metadata = {
            "citations": [c.to_dict() for c in result.citations],
            "confidence": result.confidence,
            "model": result.model,
            "intent": result.intent,
            "strict_mode": strict_mode,
            "strict_mode_applied": strict_mode and result.confidence != "high",
        }
        conversation.add_message(MessageRole.ASSISTANT, answer, metadata=assistant_metadata)

        await self.conversation_repository.save(conversation)

        return {
            "conversation_id": conversation.id,
            "answer": answer,
            "citations": [c.to_dict() for c in result.citations],
            "confidence": result.confidence,
            "model": result.model,
        }

    async def ask_stream(
        self,
        question: str,
        conversation_id: UUID | None = None,
        strict_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        conversation = await self._get_or_create_conversation(conversation_id)
        conversation.add_message(MessageRole.USER, question)

        allowed, rejection_message, guardrail_category = apply_guardrails(question)
        if not allowed:
            answer = await self._persist_guardrail_rejection(
                conversation, rejection_message, guardrail_category
            )
            yield self._chat_metadata_event(
                conversation.id,
                intent="rejected",
                confidence="low",
                model=self.agent.llm_provider.get_model_name(),
                citations=[],
                strict_mode_applied=False,
            )
            yield self._chat_chunk_event(conversation.id, answer)
            yield self._chat_done_event(conversation.id)
            return

        await self.conversation_repository.save(conversation)

        answer_parts: list[str] = []
        metadata: dict[str, Any] | None = None
        strict_mode_applied = False
        done_event: dict[str, Any] | None = None

        agent_stream = self.agent.handle_stream(
            question, history=conversation.messages[:-1][-MAX_HISTORY_MESSAGES:]
        )
        try:
            async for event in agent_stream:
                chat_event = self._map_agent_event(event, conversation.id)
                if chat_event is None:
                    continue

                event_type = chat_event.get("type")
                if event_type == "metadata":
                    metadata = chat_event
                    strict_mode_applied = strict_mode and metadata["confidence"] != "high"
                    metadata["strict_mode_applied"] = strict_mode_applied
                    yield metadata
                    if strict_mode_applied:
                        strict_message = (
                            "I don't have enough information to answer with high confidence "
                            "in strict mode."
                        )
                        answer_parts = [strict_message]
                        yield self._chat_chunk_event(conversation.id, strict_message)
                        break
                elif event_type == "chunk":
                    answer_parts.append(chat_event.get("content", ""))
                    yield chat_event
                elif event_type == "done":
                    # Buffer the done event and emit it only after the assistant
                    # message has been persisted, so clients can safely refetch
                    # the conversation as soon as the stream completes.
                    done_event = chat_event
        finally:
            # Strict mode breaks out of the loop early; close the agent stream
            # explicitly so the underlying LLM stream is deterministically
            # released instead of relying on garbage collection.
            await agent_stream.aclose()

        if metadata is None:
            metadata = {
                "intent": "search",
                "confidence": "low",
                "model": self.agent.llm_provider.get_model_name(),
                "citations": [],
                "strict_mode_applied": False,
            }

        answer = "".join(answer_parts)
        assistant_metadata = {
            "citations": metadata.get("citations", []),
            "confidence": metadata.get("confidence", "low"),
            "model": metadata.get("model", self.agent.llm_provider.get_model_name()),
            "intent": metadata.get("intent", "search"),
            "strict_mode": strict_mode,
            "strict_mode_applied": strict_mode_applied,
        }
        conversation.add_message(MessageRole.ASSISTANT, answer, metadata=assistant_metadata)
        await self.conversation_repository.save(conversation)

        yield done_event or self._chat_done_event(conversation.id)

    async def _persist_guardrail_rejection(
        self,
        conversation: Conversation,
        rejection_message: str | None,
        guardrail_category: str | None,
    ) -> str:
        """Record and persist a guardrail rejection as the assistant message."""
        answer = rejection_message or "I cannot answer this question."
        conversation.add_message(
            MessageRole.ASSISTANT,
            answer,
            metadata={"guardrail": guardrail_category or "unknown"},
        )
        await self.conversation_repository.save(conversation)
        return answer

    def _map_agent_event(
        self, event: AgentStreamEvent, conversation_id: UUID
    ) -> dict[str, Any] | None:
        if isinstance(event, AgentMetadataEvent):
            return self._chat_metadata_event(
                conversation_id,
                intent=event.intent,
                confidence=event.confidence,
                model=event.model,
                citations=[c.to_dict() for c in event.citations],
                strict_mode_applied=False,
            )
        if isinstance(event, AgentChunkEvent):
            return self._chat_chunk_event(conversation_id, event.content)
        if isinstance(event, AgentDoneEvent):
            return self._chat_done_event(conversation_id)
        return None

    @staticmethod
    def _chat_metadata_event(
        conversation_id: UUID,
        intent: str,
        confidence: str,
        model: str,
        citations: list[dict[str, Any]],
        strict_mode_applied: bool,
    ) -> dict[str, Any]:
        return {
            "type": "metadata",
            "conversation_id": str(conversation_id),
            "intent": intent,
            "confidence": confidence,
            "model": model,
            "citations": citations,
            "strict_mode_applied": strict_mode_applied,
        }

    @staticmethod
    def _chat_chunk_event(conversation_id: UUID, content: str) -> dict[str, Any]:
        return {
            "type": "chunk",
            "conversation_id": str(conversation_id),
            "content": content,
        }

    @staticmethod
    def _chat_done_event(conversation_id: UUID) -> dict[str, Any]:
        return {
            "type": "done",
            "conversation_id": str(conversation_id),
        }

    async def _get_or_create_conversation(
        self, conversation_id: UUID | None = None
    ) -> Conversation:
        if conversation_id:
            conversation = await self.conversation_repository.get_by_id(conversation_id)
            if conversation:
                return conversation
            logger.warning(
                "Conversation not found, creating new one",
                conversation_id=str(conversation_id),
            )
        return Conversation(id=conversation_id or uuid4())
