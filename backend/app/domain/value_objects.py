from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None
    section_title: str | None
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    page_number: int | None
    section_title: str | None
    keyword_score: float
    vector_score: float
    final_score: float

    def to_citation(self) -> Citation:
        return Citation(
            chunk_id=self.chunk_id,
            document_id=self.document_id,
            document_name=self.document_name,
            page_number=self.page_number,
            section_title=self.section_title,
            excerpt=self.content[:2000],
        )


@dataclass(frozen=True)
class AgentResult:
    answer: str
    citations: list[Citation]
    confidence: str
    model: str
    intent: str


@dataclass(frozen=True)
class AgentMetadataEvent:
    intent: str
    confidence: str
    model: str
    citations: list[Citation]


@dataclass(frozen=True)
class AgentChunkEvent:
    content: str


@dataclass(frozen=True)
class AgentDoneEvent:
    pass


AgentStreamEvent = AgentMetadataEvent | AgentChunkEvent | AgentDoneEvent
