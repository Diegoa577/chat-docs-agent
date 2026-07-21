import re
from uuid import UUID

from app.core.config import settings
from app.domain.models.chunk import Chunk


class ChunkingService:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_pages(
        self,
        document_id: UUID,
        pages: list[dict[str, str | int | None]],
    ) -> list[Chunk]:
        """Chunk parsed pages into smaller pieces with metadata."""
        chunks = []
        chunk_index = 0

        for page in pages:
            page_number = page.get("page_number")
            section_title = page.get("section_title")
            text = str(page.get("text", ""))

            # Try to split by headers first
            header_splits = self._split_by_headers(text)

            for section_text in header_splits:
                section_chunks = self._split_text(section_text)
                for section_chunk in section_chunks:
                    chunk = Chunk(
                        document_id=document_id,
                        content=section_chunk,
                        chunk_index=chunk_index,
                        page_number=page_number if isinstance(page_number, int) else None,
                        section_title=section_title if isinstance(section_title, str) else None,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

        return chunks

    def _split_by_headers(self, text: str) -> list[str]:
        """Split markdown-style headers if present."""
        pattern = r"(?=\n#{1,3}\s+)"
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip()]

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks of approximately chunk_size words.

        Splits respect paragraph boundaries when possible, then sentence
        boundaries, and finally falls back to words for very long sentences.
        """
        words = text.split()
        if not words:
            return []

        if len(words) <= self.chunk_size:
            return [text]

        # Prefer paragraph boundaries, then sentence boundaries.
        parts = self._split_into_parts(text)
        return self._merge_parts(parts)

    def _split_into_parts(self, text: str) -> list[str]:
        """Split text into natural parts: paragraphs, then sentences, then words."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        parts: list[str] = []
        for paragraph in paragraphs:
            if len(paragraph.split()) <= self.chunk_size:
                parts.append(paragraph)
                continue

            # Paragraph too long: split by sentences.
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(sentence.split()) <= self.chunk_size:
                    parts.append(sentence)
                else:
                    # Sentence too long: split by words.
                    parts.extend(self._split_by_words(sentence))
        return parts

    def _split_by_words(self, text: str) -> list[str]:
        """Split a long text into word-based chunks of ~chunk_size words."""
        words = text.split()
        if not words:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - self.chunk_overlap
            if start >= end:
                start = end
        return chunks

    def _merge_parts(self, parts: list[str]) -> list[str]:
        """Merge natural parts into chunks of ~chunk_size words with overlap."""
        chunks: list[str] = []
        current_parts: list[str] = []
        current_word_count = 0

        for part in parts:
            part_words = part.split()
            part_word_count = len(part_words)

            if not current_parts:
                current_parts.append(part)
                current_word_count = part_word_count
                continue

            if current_word_count + part_word_count <= self.chunk_size:
                current_parts.append(part)
                current_word_count += part_word_count
            else:
                chunks.append(" ".join(current_parts))

                # Build overlap from the end of the current chunk.
                overlap_parts = self._build_overlap(current_parts)
                current_parts = overlap_parts + [part]
                current_word_count = sum(len(p.split()) for p in current_parts)

        if current_parts:
            chunks.append(" ".join(current_parts))

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _build_overlap(self, parts: list[str]) -> list[str]:
        """Return trailing parts that fit within the overlap budget."""
        overlap_words = 0
        overlap_parts: list[str] = []

        for part in reversed(parts):
            part_word_count = len(part.split())
            if overlap_words + part_word_count > self.chunk_overlap:
                break
            overlap_parts.insert(0, part)
            overlap_words += part_word_count

        return overlap_parts
