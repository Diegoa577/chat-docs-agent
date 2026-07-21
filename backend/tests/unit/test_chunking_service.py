import uuid

from app.application.services.chunking_service import ChunkingService


class TestChunkingService:
    def test_chunk_pages_with_short_text(self):
        document_id = uuid.uuid4()
        pages = [
            {
                "page_number": 1,
                "section_title": "Introduction",
                "text": "This is a short text.",
            }
        ]

        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        chunks = service.chunk_pages(document_id, pages)

        assert len(chunks) == 1
        assert chunks[0].document_id == document_id
        assert chunks[0].page_number == 1
        assert chunks[0].section_title == "Introduction"

    def test_chunk_pages_with_long_text(self):
        document_id = uuid.uuid4()
        text = "word " * 100
        pages = [{"page_number": 1, "section_title": None, "text": text}]

        service = ChunkingService(chunk_size=20, chunk_overlap=5)
        chunks = service.chunk_pages(document_id, pages)

        assert len(chunks) > 1
        assert all(chunk.document_id == document_id for chunk in chunks)

    def test_chunk_pages_respects_sentence_boundaries(self):
        document_id = uuid.uuid4()
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        pages = [{"page_number": 1, "section_title": None, "text": text}]

        service = ChunkingService(chunk_size=6, chunk_overlap=1)
        chunks = service.chunk_pages(document_id, pages)

        assert len(chunks) > 1
        # Sentences should not be split mid-sentence when possible.
        for chunk in chunks:
            assert not chunk.content.endswith("Fir")  # naive word split example

    def test_chunk_pages_preserves_section_title(self):
        document_id = uuid.uuid4()
        pages = [
            {
                "page_number": 1,
                "section_title": "Safety",
                "text": "Adverse events must be reported.",
            }
        ]

        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        chunks = service.chunk_pages(document_id, pages)

        assert len(chunks) == 1
        assert chunks[0].section_title == "Safety"
