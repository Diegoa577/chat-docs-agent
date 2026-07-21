from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass
class Chunk:
    document_id: UUID
    content: str
    chunk_index: int
    id: UUID = field(default_factory=uuid4)
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
