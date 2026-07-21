import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.document import Document
from app.infrastructure.db.repositories.postgres_conversation_repository import (
    PostgresConversationRepository,
)
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from tests.conftest import AsyncTestSessionLocal, _is_db_available

pytestmark = pytest.mark.skipif(not _is_db_available(), reason="Test database is not available")


@pytest.fixture
async def async_session():
    session = AsyncTestSessionLocal()
    try:
        yield session
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_document_repository_lifecycle(async_session: AsyncSession):
    repository = PostgresDocumentRepository(async_session)

    document = Document(filename="test.txt", content_type="text/plain")
    saved = await repository.save(document)
    assert saved.id is not None

    retrieved = await repository.get_by_id(saved.id)
    assert retrieved is not None
    assert retrieved.filename == "test.txt"

    updated_doc = await repository.get_by_id(saved.id)
    assert updated_doc is not None
    updated_doc.mark_completed()
    await repository.update(updated_doc)

    listed = await repository.list_documents()
    assert any(doc.id == saved.id for doc in listed)

    await repository.delete(saved.id)
    assert await repository.get_by_id(saved.id) is None


@pytest.mark.asyncio
async def test_save_and_delete_chunks(async_session: AsyncSession):
    from app.domain.models.chunk import Chunk

    repository = PostgresDocumentRepository(async_session)

    document = Document(filename="chunked.txt", content_type="text/plain")
    saved = await repository.save(document)

    chunks = [
        Chunk(
            document_id=saved.id,
            content="Chunk one",
            chunk_index=0,
            page_number=1,
            section_title="Section A",
        ),
        Chunk(
            document_id=saved.id,
            content="Chunk two",
            chunk_index=1,
            page_number=1,
            section_title="Section A",
        ),
    ]
    await repository.save_chunks(chunks)

    await repository.delete_chunks_by_document(saved.id)

    await repository.delete(saved.id)


@pytest.mark.asyncio
async def test_conversation_repository_lifecycle(async_session: AsyncSession):
    from app.domain.models.conversation import Conversation

    repository = PostgresConversationRepository(async_session)

    conversation = Conversation()
    saved = await repository.save(conversation)
    assert saved.id is not None

    retrieved = await repository.get_by_id(saved.id)
    assert retrieved is not None

    listed = await repository.list_conversations()
    assert any(conv.id == saved.id for conv in listed)

    await repository.delete(saved.id)
    assert await repository.get_by_id(saved.id) is None
