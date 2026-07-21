from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class Message:
    role: MessageRole
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    id: UUID = field(default_factory=uuid4)
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def add_message(
        self, role: MessageRole, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self.messages.append(Message(role=role, content=content, metadata=metadata or {}))
        self.updated_at = _utc_now()
