from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    strict_mode: bool = False
    provider: str | None = None
    model: str | None = None


class CitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None
    section_title: str | None
    excerpt: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    citations: list[CitationResponse]
    confidence: str  # high | medium | low
    model: str
