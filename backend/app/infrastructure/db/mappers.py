from datetime import UTC, datetime

from app.domain.models.chunk import Chunk
from app.domain.models.conversation import Conversation, Message, MessageRole
from app.domain.models.document import Document
from app.infrastructure.db.models import ChunkModel, ConversationModel, DocumentModel


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def document_to_model(document: Document) -> DocumentModel:
    return DocumentModel(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        status=document.status,
        metadata=document.metadata,
        error_message=document.error_message,
        created_at=_to_naive_utc(document.created_at),
        updated_at=_to_naive_utc(document.updated_at),
    )


def document_from_model(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        filename=model.filename,
        content_type=model.content_type,
        status=model.status,
        metadata=model.metadata_,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def chunk_to_model(chunk: Chunk) -> ChunkModel:
    return ChunkModel(
        id=chunk.id,
        document_id=chunk.document_id,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        page_number=chunk.page_number,
        section_title=chunk.section_title,
        embedding=chunk.metadata.get("embedding"),
        metadata={k: v for k, v in chunk.metadata.items() if k != "embedding"},
    )


def chunk_from_model(model: ChunkModel) -> Chunk:
    return Chunk(
        id=model.id,
        document_id=model.document_id,
        content=model.content,
        chunk_index=model.chunk_index,
        page_number=model.page_number,
        section_title=model.section_title,
        metadata=model.metadata_,
    )


def conversation_to_model(conversation: Conversation) -> ConversationModel:
    return ConversationModel(
        id=conversation.id,
        messages=[
            {"role": m.role.value, "content": m.content, "metadata": m.metadata}
            for m in conversation.messages
        ],
        metadata=conversation.metadata,
        created_at=_to_naive_utc(conversation.created_at),
        updated_at=_to_naive_utc(conversation.updated_at),
    )


def conversation_from_model(model: ConversationModel) -> Conversation:
    conversation = Conversation(
        id=model.id,
        metadata=model.metadata_,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
    conversation.messages = [
        Message(
            role=MessageRole(m["role"]),
            content=m["content"],
            metadata=m.get("metadata", {}),
        )
        for m in model.messages
    ]
    return conversation
