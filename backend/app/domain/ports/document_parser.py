from abc import ABC, abstractmethod
from pathlib import Path


class DocumentParser(ABC):
    """Port for parsing documents into pages/sections with metadata."""

    @abstractmethod
    def parse(self, file_path: Path, content_type: str) -> list[dict[str, str | int | None]]:
        """Return list of pages/sections with text and metadata.

        Each item should contain at least:
        - "text": str
        - "page_number": int | None
        - "section_title": str | None
        """
        raise NotImplementedError
