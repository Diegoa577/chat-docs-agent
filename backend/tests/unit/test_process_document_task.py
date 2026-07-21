from uuid import uuid4

import pytest
from celery.exceptions import Retry

from app.tasks import process_document as process_document_module


class FakeFileStorage:
    def __init__(self):
        self.deleted: list[tuple[str, str]] = []

    async def delete(self, document_id, filename: str) -> None:
        self.deleted.append((str(document_id), filename))


def _run_failing_task(monkeypatch, retries: int):
    """Run process_document with a failing pipeline and return the fake storage."""
    fake_storage = FakeFileStorage()

    async def failing_process(*args, **kwargs):
        raise RuntimeError("transient embedding outage")

    monkeypatch.setattr(process_document_module, "_process_document_async", failing_process)
    monkeypatch.setattr(process_document_module, "LocalFileStorage", lambda: fake_storage)

    task = process_document_module.process_document
    # In eager mode with throw=True Celery re-raises the original exception
    # instead of MaxRetriesExceededError once retries are exhausted.
    expected = RuntimeError if retries >= task.max_retries else Retry
    with pytest.raises(expected):
        task.apply(
            args=[str(uuid4()), "protocol.txt", "text/plain"],
            retries=retries,
            throw=True,
        )

    return fake_storage


def test_failed_processing_retains_file_after_final_retry(monkeypatch):
    """Once Celery retries are exhausted the uploaded file must stay on disk
    so the user can retry via POST /documents/{id}/reprocess."""
    task = process_document_module.process_document
    fake_storage = _run_failing_task(monkeypatch, retries=task.max_retries)

    assert fake_storage.deleted == []


def test_failed_processing_does_not_delete_file_before_final_retry(monkeypatch):
    fake_storage = _run_failing_task(monkeypatch, retries=1)

    assert fake_storage.deleted == []
