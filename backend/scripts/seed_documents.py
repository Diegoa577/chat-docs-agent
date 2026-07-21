#!/usr/bin/env python3
"""Seed the RAG database with real, publicly available clinical/regulatory documents.

This script runs once at first startup (or whenever the seed container is started).
It is idempotent: documents whose filename already exists in the database are skipped.

Usage:
    python -m scripts.seed_documents
"""

import asyncio
import json
import urllib.request
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.services.document_service import DocumentService
from app.core.config import settings
from app.infrastructure.db.connection import _normalize_async_url
from app.infrastructure.db.models import DocumentModel
from app.infrastructure.db.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.tasks.process_document import process_document

MANIFEST_PATH = Path(__file__).parent / "seed_documents.json"
DOWNLOAD_TIMEOUT_SECONDS = 120


def _guess_content_type(filename: str) -> str:
    if filename.endswith(".pdf"):
        return "application/pdf"
    if filename.endswith((".txt", ".text")):
        return "text/plain"
    return "application/octet-stream"


async def _document_exists(session: AsyncSession, filename: str) -> bool:
    result = await session.execute(select(DocumentModel).where(DocumentModel.filename == filename))
    return result.scalar_one_or_none() is not None


async def seed_documents() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    documents = manifest.get("documents", [])

    engine = create_async_engine(
        _normalize_async_url(settings.database_url),
        echo=False,
        future=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = PostgresDocumentRepository(session)
            file_storage = LocalFileStorage()
            service = DocumentService(
                document_repository=repository,
                file_storage=file_storage,
                task_runner=process_document.delay,
            )

            for item in documents:
                filename = item["filename"]
                url = item["url"]
                content_type = item.get("content_type") or _guess_content_type(filename)

                if await _document_exists(session, filename):
                    print(f"[seed] Already exists, skipping: {filename}")
                    continue

                print(f"[seed] Downloading: {filename} ({url})")
                try:
                    # Some hosts (ICH, FDA) throttle or block requests without a
                    # User-Agent header.
                    request = urllib.request.Request(
                        url,
                        headers={"User-Agent": "clinical-document-agent/0.1 (seed script)"},
                    )
                    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                        content = response.read()
                except Exception as exc:
                    print(f"[seed] Failed to download {filename}: {exc}")
                    continue

                print(f"[seed] Uploading: {filename} ({len(content)} bytes)")
                await service.upload_document(
                    filename=filename,
                    content_type=content_type,
                    content=content,
                )
                print(f"[seed] Queued for processing: {filename}")

        print("[seed] Done.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_documents())
