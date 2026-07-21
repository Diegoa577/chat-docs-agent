from pathlib import Path

import fitz  # pymupdf
from docx import Document as DocxDocument

from app.domain.ports.document_parser import DocumentParser


class PyMuPDFParser(DocumentParser):
    def parse(self, file_path: Path, content_type: str) -> list[dict[str, str | int | None]]:
        if content_type == "application/pdf":
            return self._parse_pdf(file_path)
        if content_type in (
            "text/plain",
            "application/text",
        ):
            return self._parse_text(file_path)
        if content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return self._parse_docx(file_path)
        raise ValueError(f"Unsupported content type: {content_type}")

    def _parse_pdf(self, file_path: Path) -> list[dict[str, str | int | None]]:
        pages: list[dict[str, str | int | None]] = []
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if text:
                    pages.append(
                        {
                            "page_number": page_num,
                            "section_title": None,
                            "text": text,
                        }
                    )
        return pages

    def _parse_text(self, file_path: Path) -> list[dict[str, str | int | None]]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return [{"page_number": 1, "section_title": None, "text": text}]

    def _parse_docx(self, file_path: Path) -> list[dict[str, str | int | None]]:
        doc = DocxDocument(str(file_path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        return [{"page_number": 1, "section_title": None, "text": text}]


def get_parser() -> DocumentParser:
    return PyMuPDFParser()
