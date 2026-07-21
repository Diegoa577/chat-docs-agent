import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.api.routes import chat, conversations, documents, providers
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.infrastructure.db.connection import AsyncSessionLocal
from app.infrastructure.llm.model_catalog import initialise_catalog

configure_logging()

# Load provider model definitions from the external catalog file. This keeps
# model lists out of environment variables and code while still allowing the
# provider selection (LLM_PROVIDER) to be configured via env. Entry points own
# this bootstrap so app/core/config.py stays infrastructure-free.
initialise_catalog(settings.models_catalog_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import os

    os.makedirs(settings.uploads_dir, exist_ok=True)

    if not settings.configured_llm_providers:
        import structlog

        logger = structlog.get_logger()
        logger.warning(
            "No LLM provider configured",
            detail="Set at least one provider API key in .env to enable chat responses.",
        )

    if not settings.is_embedding_configured:
        import structlog

        logger = structlog.get_logger()
        logger.warning(
            "Embedding provider not configured",
            provider=settings.embedding_provider,
            detail="Set the corresponding API key in .env to enable document ingestion and search.",
        )

    yield


app = FastAPI(
    title="Clinical Document Intelligence Agent",
    description="RAG-based assistant for clinical and regulatory documents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start_time = time.time()
    response: Response = await call_next(request)
    duration = time.time() - start_time

    # Use the route path template (e.g. /documents/{document_id}) instead of the
    # raw URL to keep Prometheus label cardinality bounded. Unmatched routes
    # (404s) get a fixed label for the same reason.
    route = request.scope.get("route")
    path = getattr(route, "path", None) or "unmatched"
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

    return response


app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(providers.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name}


async def _check_redis() -> bool:
    """Ping Redis (Celery broker) to verify worker connectivity is possible."""
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False


@app.get("/ready", tags=["health"])
async def readiness_check() -> Response:
    checks: dict[str, bool] = {
        "llm_configured": bool(settings.configured_llm_providers),
        "embedding_configured": settings.is_embedding_configured,
    }

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception:
        checks["database"] = False

    checks["redis"] = await _check_redis()

    ready = all(checks.values())
    status_code = 200 if ready else 503

    return JSONResponse(
        content={"status": "ready" if ready else "not ready", "checks": checks},
        status_code=status_code,
    )


@app.get("/metrics", tags=["metrics"])
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
