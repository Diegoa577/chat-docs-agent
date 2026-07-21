from collections.abc import Callable

# Enqueues asynchronous document processing. Signature:
# (document_id, filename, content_type) -> None
# Defined as a plain callable so any queue backend (Celery, in-process, fake)
# can be injected from the composition root.
TaskRunner = Callable[[str, str, str], None]
