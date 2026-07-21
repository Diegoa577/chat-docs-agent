from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "clinical_document_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.process_document"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
)
