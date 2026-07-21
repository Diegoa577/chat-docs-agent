from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class Document:
    filename: str
    content_type: str
    status: DocumentStatus = DocumentStatus.PENDING
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    error_message: str | None = None

    def mark_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING
        self.updated_at = _utc_now()

    def mark_completed(self) -> None:
        self.status = DocumentStatus.COMPLETED
        self.updated_at = _utc_now()

    def mark_failed(self, error_message: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error_message = error_message
        self.updated_at = _utc_now()

    def reset_for_reprocessing(self) -> None:
        self.status = DocumentStatus.PENDING
        self.error_message = None
        self.updated_at = _utc_now()
