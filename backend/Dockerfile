# Builder stage: install dependencies with build tooling available.
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Hatchling needs the package sources present for the editable install.
COPY pyproject.toml ./
COPY app ./app
COPY mcp_server ./mcp_server
RUN pip install -e ".[dev]"

# Pre-download the default local embedding model so containers start quickly.
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Runtime stage: slim image without compilers or build tooling.
FROM python:3.12-slim AS runtime

ARG APP_USER=appuser
ARG APP_UID=1000
ARG APP_GID=1000

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface

# postgresql-client is needed by the entrypoint to create the pgvector extension.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid ${APP_GID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home ${APP_USER}

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app/.cache /app/.cache
COPY . .

# Ensure the entrypoint is executable and writable directories are owned by the app user.
RUN chmod +x scripts/entrypoint.sh \
    && mkdir -p /app/uploads /app/.cache/huggingface \
    && chown -R ${APP_USER}:${APP_USER} /app/uploads /app/.cache/huggingface

EXPOSE 8000

USER ${APP_UID}:${APP_GID}

CMD ["./scripts/entrypoint.sh"]
