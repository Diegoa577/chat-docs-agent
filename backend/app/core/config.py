from pathlib import Path
from typing import Any

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger()

# Repository-root .env, resolved from this file's location so it is found no
# matter which directory the process starts from (e.g. pytest runs from
# backend/, uvicorn from the repo root). A CWD-local .env is still honoured
# and takes precedence when present.
_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://cda_user:cda_password@localhost:5432/cda_db"
    sync_database_url: str = "postgresql://cda_user:cda_password@localhost:5432/cda_db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    # The active provider (openai | gemini) is still selected
    # via environment. The list of available models per provider lives in the
    # model catalog (models.yaml + built-ins) instead of environment variables.
    llm_provider: str = "openai"
    llm_fallback_provider: str | None = None  # e.g. gemini when openai fails
    llm_model: str | None = None  # optional model_id override from the catalog
    models_catalog_path: str = "models.yaml"  # YAML file with provider models
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # Embeddings
    embedding_provider: str = "bge"  # openai | bge | huggingface
    embedding_fallback_provider: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_model_dimension: int = 1536
    bge_model_name: str = "BAAI/bge-small-en-v1.5"
    bge_model_dimension: int = 384

    @property
    def embedding_dimension(self) -> int:
        # NOTE: The database migration and ChunkModel are aligned to 384-d
        # (BAAI/bge-small-en-v1.5) by default. To use OpenAI embeddings (1536-d)
        # you must regenerate the Alembic migration so the vector column matches.
        if self.embedding_provider == "openai":
            return self.openai_embedding_model_dimension
        return self.bge_model_dimension

    # RAG
    retrieval_top_k: int = 5
    hybrid_alpha: float = 0.5
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Files
    uploads_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    # Observability
    log_level: str = "INFO"
    service_name: str = "clinical-document-agent"

    # Resilience
    provider_max_retries: int = 2
    provider_retry_backoff_seconds: float = 1.0
    provider_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=(_ROOT_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def model_post_init(self, __context: Any, /) -> None:
        if self.llm_fallback_provider and self.llm_fallback_provider == self.llm_provider:
            logger.warning(
                "llm_fallback_provider equals llm_provider; fallback will use the same provider",
                provider=self.llm_provider,
            )
        if (
            self.embedding_fallback_provider
            and self.embedding_fallback_provider == self.embedding_provider
        ):
            logger.warning(
                "embedding_fallback_provider equals embedding_provider; "
                "fallback will use the same provider",
                provider=self.embedding_provider,
            )

    @staticmethod
    def _is_valid_api_key(key: str | None) -> bool:
        if not key:
            return False
        lowered = key.lower()
        # .env.example uses values like "your-openai-api-key".
        if lowered.startswith("your-"):
            return False
        placeholders = {"your-key", "placeholder", "example", "test", "dummy", "xxx"}
        return not any(p in lowered for p in placeholders)

    def _api_key_for_provider(self, provider: str | None) -> str | None:
        if provider == "openai":
            return self.openai_api_key
        if provider == "gemini":
            return self.gemini_api_key
        return None

    @property
    def is_llm_configured(self) -> bool:
        return self._is_valid_api_key(self._api_key_for_provider(self.llm_provider))

    @property
    def is_embedding_configured(self) -> bool:
        # Local embedding providers do not require an API key.
        if self.embedding_provider in {"bge", "huggingface"}:
            return True
        return self._is_valid_api_key(self._api_key_for_provider(self.embedding_provider))

    @property
    def is_llm_fallback_configured(self) -> bool:
        return bool(
            self.llm_fallback_provider and self._api_key_for_provider(self.llm_fallback_provider)
        )

    @property
    def configured_llm_providers(self) -> list[str]:
        """Return LLM providers that have a valid API key configured.

        Only providers with a concrete adapter/factory implementation are
        listed here.
        """
        providers: list[str] = []
        for provider in ("openai", "gemini"):
            if self._is_valid_api_key(self._api_key_for_provider(provider)):
                providers.append(provider)
        return providers

    @property
    def is_embedding_fallback_configured(self) -> bool:
        if not self.embedding_fallback_provider:
            return False
        # Local embedding providers do not require an API key, mirroring
        # is_embedding_configured (enables e.g. openai -> bge fallback).
        if self.embedding_fallback_provider in {"bge", "huggingface"}:
            return True
        return self._is_valid_api_key(self._api_key_for_provider(self.embedding_fallback_provider))


settings = Settings()

# NOTE: the LLM model catalog (models.yaml) is loaded by the application entry
# points (app/main.py, mcp_server, tests/conftest.py), not here, so this module
# stays free of infrastructure imports.
