import socket
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.db.models import Base, ChunkModel, DocumentModel
from app.infrastructure.llm.model_catalog import initialise_catalog

# Tests are their own entry point: bootstrap the model catalog here (mirrors
# app/main.py) instead of relying on a side effect of importing settings.
initialise_catalog(settings.models_catalog_path)

TEST_SYNC_DATABASE_URL = settings.sync_database_url.replace("/cda_db", "/cda_test_db")
# Force asyncpg for the async test engine regardless of environment overrides.
TEST_ASYNC_DATABASE_URL = settings.database_url.replace("/cda_db", "/cda_test_db").replace(
    "postgresql://", "postgresql+asyncpg://"
)

_db_engine = None
_async_test_engine = None
_db_available = None


def _is_db_available() -> bool:
    """Check whether the test database is reachable.

    Both the sync and async test URLs are checked: the sync one with a real
    connection, the async one with a TCP probe (its host/port may differ when
    environment variables override the defaults).
    """
    global _db_available
    if _db_available is not None:
        return _db_available

    try:
        engine = create_engine(TEST_SYNC_DATABASE_URL, echo=False, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        async_url = make_url(TEST_ASYNC_DATABASE_URL)
        with socket.create_connection(
            (async_url.host or "localhost", async_url.port or 5432), timeout=2
        ):
            pass
        _db_available = True
    except Exception:
        _db_available = False
    return _db_available


def _get_db_engine():
    """Lazy initializer for the synchronous test engine."""
    global _db_engine
    if _db_engine is None:
        _db_engine = create_engine(TEST_SYNC_DATABASE_URL, echo=False, future=True)
        Base.metadata.create_all(bind=_db_engine)
    return _db_engine


def _get_async_test_engine():
    """Lazy initializer for the asynchronous test engine."""
    global _async_test_engine
    if _async_test_engine is None:
        _async_test_engine = create_async_engine(
            TEST_ASYNC_DATABASE_URL,
            echo=False,
            future=True,
        )
    return _async_test_engine


AsyncTestSessionLocal = async_sessionmaker(
    _get_async_test_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(autouse=True)
def _truncate_test_tables():
    """Reset the test database tables around each test that needs the DB.

    This keeps integration tests isolated even when they commit data through
    their own async sessions.
    """
    if _is_db_available():
        engine = _get_db_engine()
        # Close any pooled connections left behind by previous tests. Otherwise
        # the TRUNCATE can block on locks held by idle-in-transaction connections.
        engine.dispose()
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE chunks, documents, conversations CASCADE"))

    yield

    if _is_db_available():
        engine = _get_db_engine()
        # Clean up after the test as well so the next test starts from a blank slate.
        engine.dispose()
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE chunks, documents, conversations CASCADE"))


@pytest.fixture
def db_session():
    if not _is_db_available():
        pytest.skip("Test database is not available")

    connection = _get_db_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def seeded_document(db_session):
    """Seed a document with chunks for retrieval tests."""
    doc_id = uuid4()
    document = DocumentModel(
        id=doc_id,
        filename="test_protocol.txt",
        content_type="text/plain",
        status="completed",
    )
    db_session.add(document)
    db_session.flush()

    chunks = [
        ChunkModel(
            document_id=doc_id,
            content="Inclusion criteria: adult patients aged 18 to 65 years with rheumatoid arthritis may be included. Informed consent is required.",
            chunk_index=0,
            page_number=1,
            section_title="Inclusion Criteria",
            embedding=[0.1] * settings.embedding_dimension,
        ),
        ChunkModel(
            document_id=doc_id,
            content="Serious adverse events must be reported to the sponsor within 24 hours of awareness.",
            chunk_index=1,
            page_number=2,
            section_title="Safety Monitoring",
            embedding=[0.2] * settings.embedding_dimension,
        ),
        ChunkModel(
            document_id=doc_id,
            content="The primary objective is to evaluate ACR20 response at Week 12.",
            chunk_index=2,
            page_number=1,
            section_title="Objectives",
            embedding=[0.3] * settings.embedding_dimension,
        ),
    ]
    db_session.add_all(chunks)
    db_session.flush()

    db_session.execute(
        text(
            "UPDATE chunks SET search_vector = to_tsvector('english', content) WHERE document_id = :document_id"
        ),
        {"document_id": str(doc_id)},
    )
    db_session.commit()

    yield document
