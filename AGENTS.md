# Agent Guide — Clinical Document Intelligence Agent

This file is written for AI coding agents working on this repository. It assumes no prior knowledge of the project. All facts below were derived from the actual files in the repository.

## Project Overview

The **Clinical Document Intelligence Agent** is a full-stack RAG (Retrieval-Augmented Generation) application for clinical and regulatory document intelligence. It is built as a technical assessment for Newpage Solutions (client: Pfizer).

The product helps life sciences teams get verifiable answers from protocols, SOPs, and regulatory submissions. Key capabilities include source attribution, confidence scoring, audit trails, an intent-routing agent loop, guardrails, and provider resilience.

- **Project slug / package name**: `clinical-document-agent`
- **Version**: `0.1.0`
- **Default branch in this clone**: `main` (CI triggers on `main`)
- **Language of comments and docs**: English

## Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 14.2.5 + React 18.3.1 + TypeScript 5.4.5 | README refers to Next.js 15; `package.json` pins 14.2.5 |
| Styling | Material UI v6 + Tailwind CSS 3.4.4 | MUI components + Tailwind utilities |
| Backend | FastAPI 0.111+ + Python 3.12 (requires >=3.11) | Uvicorn ASGI server |
| Database | PostgreSQL + pgvector | Unified relational, vector, and full-text search |
| ORM / Migrations | SQLAlchemy 2.0 (async) + Alembic | |
| Async Workers | Celery 5.4+ + Redis 7 | Document parsing, chunking, embedding |
| LLM Providers | OpenAI, Google Gemini | Configurable via `LLM_PROVIDER`; model catalog in `backend/models.yaml` |
| Embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers (default, 384 dims) | OpenAI embeddings optional (1536 dims) |
| Document Parsing | PyMuPDF (PDF), python-docx (DOCX), plain text | |
| MCP | FastMCP | Separate MCP server entry point |
| Observability | structlog (JSON), prometheus-client | Metrics endpoint `/metrics` |
| Config | Pydantic Settings + `.env` | Case-insensitive, with placeholder filtering |

## Repository Layout

```
.
├── backend/                  # FastAPI application
│   ├── app/                  # Main backend source (hexagonal architecture)
│   ├── mcp_server/           # FastMCP server entry point
│   ├── migrations/           # Alembic migrations
│   ├── tests/                # pytest tests (unit, integration, evals)
│   ├── uploads/              # Local file storage for uploaded documents
│   ├── Dockerfile            # Multi-stage (builder + slim runtime)
│   ├── .pre-commit-config.yaml # ruff + ruff-format + mypy hooks
│   └── pyproject.toml        # Python packaging + tool configuration
├── frontend/                 # Next.js application
│   ├── app/                  # App Router pages
│   ├── components/           # React client components
│   ├── lib/                  # API client helpers
│   ├── Dockerfile
│   └── package.json
├── docs/                     # Additional architecture docs
├── .github/workflows/        # CI workflow
├── docker-compose.yml        # Full stack orchestration
├── .env.example              # Environment variable template
├── README.md                 # Human-facing project overview
├── ARCHITECTURE.md           # Architecture Decision Record (ADR)
├── Assignment v3.docx        # Assignment brief (not used by code)
└── JD-FDE -EU (2).pdf        # Job description (not used by code)
```

## Backend Architecture

The backend follows **hexagonal / clean architecture** (DDD). Code lives under `backend/app/`.

```
app/
├── api/                      # FastAPI routers, Pydantic schemas, dependencies
│   ├── routes/               # documents.py (upload, list, get, download, delete,
│   │                         # reprocess),
│   │                         # chat.py, conversations.py
│   ├── schemas/              # request/response DTOs
│   └── dependencies/         # rate_limiter.py (in-memory sliding window)
├── application/              # Use-case orchestration & services
│   └── services/             # agent_service, chat_service, chunking_service,
│                             # document_service, ingestion_service,
│                             # conversation_service, guardrails
├── domain/                   # Business entities, value objects, ports
│   ├── models/               # Document, Chunk, Conversation
│   ├── ports/                # LLMProvider, EmbeddingProvider, FileStorage,
│   │                         # DocumentParser, SearchEngine, TaskRunner
│   ├── repositories/         # DocumentRepository, ConversationRepository
│   └── value_objects.py
├── infrastructure/           # Concrete adapters
│   ├── db/                   # SQLAlchemy models, mappers, Postgres repositories
│   ├── embeddings/           # BGE, OpenAI, resilient/fallback providers
│   ├── llm/                  # OpenAI, Gemini, resilient/fallback
│   │                         # providers, provider_errors.py classification
│   ├── parsers/              # Document parser factory
│   ├── search/               # HybridSearchEngine (FTS + vector)
│   ├── storage/              # LocalFileStorage
│   └── workers/              # Celery app setup
├── tasks/                    # Celery task definitions
│   └── process_document.py
├── core/                     # Cross-cutting concerns
│   ├── config.py             # Pydantic Settings
│   ├── dependencies.py       # FastAPI dependency providers
│   ├── logging.py
│   └── metrics.py
└── main.py                   # FastAPI app factory & entry point
```

A separate `backend/mcp_server/` directory provides a FastMCP server exposing tools that reuse the same domain services:
- `search_documents(query, top_k)`
- `compare_documents(query, document_names)`
- `extract_entities(query, document_names)`
- `list_documents(limit)`

All MCP tools return JSON and wrap failures into a readable `error` field instead of raising.

## Frontend Architecture

The frontend is a Next.js 14 App Router application under `frontend/`.

```
frontend/
├── app/
│   ├── chat/                 # new conversation
│   │   ├── [conversationId]/ # existing conversation
│   │   └── layout.tsx        # chat section shell (ChatProvider; registers
│   │                         # ConversationSidebar into the AppShell slot via
│   │                         # AppContext, persists across conversation switches)
│   ├── documents/            # document management
│   │   └── [documentId]/     # document detail
│   ├── globals.css           # Tailwind + MUI coexistence
│   ├── layout.tsx            # root layout + MUI providers
│   ├── loading.tsx           # global loading state
│   ├── not-found.tsx         # 404 page
│   └── page.tsx              # dashboard
├── components/
│   ├── AppShell.tsx          # persistent layout mounted once in the root
│   │                         # layout (app bar + drawer); sidebar content is
│   │                         # injected through the AppContext sidebar slot
│   ├── ChatWindow.tsx        # chat UI with streaming
│   ├── ChatInput.tsx         # input + strict mode toggle + stop
│   ├── DocumentUploader.tsx  # drag & drop upload
│   ├── DocumentList.tsx      # document list with polling
│   ├── MessageBubble.tsx     # message rendering + citations + metadata
│   ├── CitationCard.tsx      # expandable source card
│   ├── ConversationSidebar.tsx # recent conversations
│   ├── SystemStatus.tsx      # backend status indicator
│   └── ThemeRegistry.tsx     # MUI theme + CSS baseline
├── lib/
│   ├── api.ts                # API client + streaming parser
│   ├── constants.ts          # app constants
│   ├── theme.ts              # MUI custom theme
│   └── hooks/                # useDocuments, useConversations, useConversation
├── context/
│   ├── AppContext.tsx        # snackbar + mobile drawer + sidebar slot state
│   └── ChatContext.tsx       # chat section state (conversation list refresh,
│                             # LLM provider catalog + provider/model selection,
│                             # per-conversation messages cache)
└── (config files)
```

- All page components are client components (`"use client"`) because they rely on browser APIs (`fetch`, `ReadableStream`, `AbortController`).
- Local React state + custom hooks for data fetching; a lightweight `AppContext` for global UI state (snackbars, mobile drawer, sidebar slot) and a `ChatContext` for chat data (conversations, providers, messages cache).
- `AppShell` is rendered once in `app/layout.tsx` and persists across all client-side navigations; pages must NOT wrap themselves in `AppShell`. The chat section injects its `ConversationSidebar` into the shell via `AppContext.setSidebar`.
- `useConversation` seeds messages synchronously from the `ChatContext` messages cache (the `GET /conversations` list endpoint already returns full messages), so switching conversations renders instantly without a loading flash; it only fetches `GET /conversations/{id}` on a cache miss. The new-chat page defers `router.replace("/chat/[id]")` until streaming finishes to avoid aborting the in-flight stream.
- `app/chat/layout.tsx` owns `ChatContext`, so switching conversations does not refetch anything (messages come from the cache) — the conversation list, LLM providers, and provider/model selection are not refetched or reset.
- The frontend calls the backend directly from the browser (`http://localhost:8000` by default, configurable via `NEXT_PUBLIC_API_URL`).
- Chat uses `POST /chat/stream` and renders tokens as they arrive.
- Document status is polled automatically every 2 seconds until completed/failed.
- Tailwind path alias `@/` maps to the project root.

## Configuration and Environment

1. Copy the template:
   ```bash
   cp .env.example .env
   ```
2. Add at least one real LLM API key (`OPENAI_API_KEY` or `GEMINI_API_KEY`).
3. Embeddings do not require an API key by default (BGE is downloaded locally).

Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Active LLM provider (`openai`, `gemini`) |
| `LLM_MODEL` | — | Optional model_id from the catalog; defaults to the first model for the provider |
| `MODELS_CATALOG_PATH` | `models.yaml` | YAML file with provider model definitions |
| `EMBEDDING_PROVIDER` | `bge` | Active embedding provider (`bge` or `openai`) |
| `OPENAI_API_KEY` | placeholder | OpenAI API key |
| `GEMINI_API_KEY` | placeholder | Google Gemini API key |
| `LOG_LEVEL` | `INFO` | Logging level |

LLM models are no longer defined by environment variables. The catalog in `backend/models.yaml` lists the available models per provider and is loaded at startup by `backend/app/infrastructure/llm/model_catalog.py` (the built-in model list is intentionally empty). The catalog bootstrap (`initialise_catalog`) is owned by the entry points — `app/main.py`, `mcp_server/server.py`, and `tests/conftest.py` — so `app/core/config.py` stays free of infrastructure imports. Provider adapters resolve the active model from the catalog at startup.

The backend config (`backend/app/core/config.py`) filters placeholder keys such as `your-key` or `placeholder` and exposes helper properties like `is_llm_configured` and `is_embedding_configured`.

When running under Docker Compose, database/Redis URLs are hardcoded in `docker-compose.yml`; API keys and provider choices are taken from `.env`.

## Build and Run Commands

### Full stack (recommended for development)

```bash
# from the project root
docker-compose up --build -d

# enable pgvector and run migrations
docker-compose exec postgres psql -U cda_user -d cda_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker-compose exec backend alembic upgrade head
```

After startup:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/ready
- Metrics: http://localhost:8000/metrics

### Backend only (local Python)

```bash
cd backend
pip install -e ".[dev]"

# start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# run migrations
alembic upgrade head

# start MCP server
python -m mcp_server.server
```

### Frontend only (local Node)

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run lint         # ESLint via Next.js
```

> **Note:** `npm run build` has been observed to hang on some Windows hosts due to the build tooling. The production build runs successfully inside Docker (`docker build -f Dockerfile -t cda-frontend .`). CI on Ubuntu is expected to build without issues.

Available frontend scripts:
- `npm run dev` — development server
- `npm run build` — production build
- `npm run start` — production server
- `npm run lint` — ESLint via Next.js

Docker images:
- `frontend/Dockerfile` — production-optimized standalone image (used by `docker-compose`).
- `frontend/Dockerfile.dev` — development image with hot reload.

### Celery worker (local)

```bash
cd backend
celery -A app.infrastructure.workers.celery_app worker --loglevel=info
```

## Testing Instructions

### Backend

```bash
cd backend

# all tests (requires configured DB/Redis and API keys for evals)
pytest -v

# unit tests only
pytest tests/unit -v

# integration tests (run isolated with --no-cov; the coverage floor is
# evaluated on the combined run below)
pytest tests/integration -v --no-cov

# combined run (used in CI; enforces the coverage floor)
pytest tests/unit tests/integration -v

# retrieval / LLM-as-judge evals
pytest tests/evals -v
```

Test organization:

```
tests/
├── conftest.py               # shared fixtures (engines, seeded document)
├── fixtures/                 # fake providers and data builders
├── unit/                     # chunking, guardrails, agent router, chat/ingestion/
│                             # document services, parsers, storage, rate limiter,
│                             # provider errors, resilient providers, API schemas
├── integration/              # chat, end-to-end, MCP server, health, hybrid search,
│                             # Postgres repositories (DB tests skip when unavailable)
└── evals/                    # retrieval recall, faithfulness, relevance,
                              # intent accuracy, live RAG quality (pytest -m llm)
```

- Frameworks: `pytest` + `pytest-asyncio` (auto mode, session-scoped loop).
- External calls are mocked in unit/integration tests.
- Integration tests that need PostgreSQL skip gracefully when no database is reachable (see `conftest.py`).
- Evals may require real LLM provider configuration.

### Frontend

The frontend uses **Jest 29 + React Testing Library** (via `next/jest` with the SWC transform).

```bash
cd frontend

# all frontend tests
npm test

# watch mode
npm run test:watch

# coverage run (used in CI; enforces the coverage floor of 70%
# statements/functions/lines configured in jest.config.js)
npm run test:coverage
```

Test organization:

```
frontend/
├── jest.config.js            # next/jest config; transforms the ESM-only
│                             # react-markdown/unified ecosystem; coverage floor
├── jest.setup.ts             # jest-dom, TextEncoder/Decoder + web-stream
│                             # polyfills, global next/navigation mock
├── __mocks__/next/
│   └── navigation.ts         # manual mock: mockPush/mockReplace/usePathname/...
└── __tests__/
    ├── test-utils.tsx        # renderWithProviders, fixture factories
    │                         # (makeDocument/makeConversation/...), NDJSON
    │                         # stream helpers, setupUser for fake timers
    ├── lib/                  # api client, streamChat NDJSON parsing, citation linkify
    ├── hooks/                # useDocuments (2s conditional polling), useConversations,
    │                         # useConversation (optimistic streaming, abort, cache)
    ├── context/              # AppContext (snackbar auto-dismiss), ChatContext
    │                         # (providers, selection, messages cache)
    ├── components/           # ChatInput, MessageBubble, citations, uploader,
    │                         # document list/card, sidebar, SystemStatus, AppShell
    └── app/                  # page-level tests (dashboard, chat, documents pages)
```

- `next/navigation` is mocked globally via `__mocks__/next/navigation.ts`; override per test with e.g. `(usePathname as jest.Mock).mockReturnValue("/documents")`.
- The API layer is mocked with `jest.mock("@/lib/api")`; fetch-level tests stub `global.fetch`.
- Fake timers are needed for polling tests (useDocuments 2s, SystemStatus 15s, snackbar 6s); use `setupUser()` from `test-utils` so `user-event` advances them.

## Code Style and Linting

### Backend

- **Formatter / Linter**: Ruff (configured in `pyproject.toml`)
  - Line length: 100
  - Target Python: 3.11
  - Selected rules: `E`, `F`, `I`, `N`, `W`, `UP`, `B`, `C4`, `SIM`
  - Ignored: `E501`
- **Type checker**: mypy in strict mode, Python 3.12 target
  - `ignore_missing_imports = true`
  - Excludes `migrations/` and `tests/`
- **Import order**: standard library → third-party → local (Ruff enforces `I`)
- **Naming**: `snake_case` for modules/functions/variables, `PascalCase` for classes
- **Async-first**: SQLAlchemy 2.0 async sessions, async repository methods

Commands:

```bash
cd backend
ruff check .           # lint
ruff format .          # format
mypy .                 # type check
```

Pre-commit hooks (ruff, ruff-format, mypy) are configured in `backend/.pre-commit-config.yaml`; enable them with `pre-commit install`.

### Frontend

- **Linter**: ESLint with `eslint-config-next` (default Next.js rules)
- **TypeScript**: strict mode enabled
- **Styling**: Tailwind CSS utility-first
- **Imports**: path alias `@/` resolves to the project root
- No Prettier or custom ESLint config is present

Commands:

```bash
cd frontend
npm run lint           # lint
npm run build          # type-check + build
```

## Deployment and Docker

### Services

`docker-compose.yml` defines five services:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | `ankane/pgvector:latest` | 5432 | PostgreSQL with pgvector |
| `redis` | `redis:7-alpine` | 6379 | Celery broker |
| `backend` | `./backend/Dockerfile` | 8000 | FastAPI API |
| `worker` | `./backend/Dockerfile` | — | Celery worker |
| `frontend` | `./frontend/Dockerfile` | 3000 | Next.js dev server |

Named volumes: `postgres_data`, `uploaded_files`, `huggingface_cache`.

### Dockerfiles

- `backend/Dockerfile` is a **multi-stage build** on `python:3.12-slim`: a builder stage installs build tools, the package (editable, with dev dependencies), and pre-downloads `BAAI/bge-small-en-v1.5`; the runtime stage copies only the installed packages and model cache, without compilers, and runs as a non-root `appuser` (UID 1000).
- `frontend/Dockerfile` is a **production multi-stage build** on `node:20-alpine` (deps → build → standalone runtime) and runs as the non-root `nextjs` user. `frontend/Dockerfile.dev` is the development image with hot reload (`npm run dev`) and runs as the non-root `node` user.

### Health Endpoints

- `GET /health` — liveness
- `GET /ready` — readiness (checks provider configuration, database, and Redis connectivity)
- `GET /metrics` — Prometheus metrics (includes business counters `rag_documents_processed_total` and `rag_ingestion_errors_total`)

## Security Considerations

- **No authentication/authorization** is implemented in this demo. The README explicitly notes production would need OAuth2/JWT and RBAC.
- API keys are loaded from `.env` and validated against placeholder strings to detect unconfigured providers.
- CORS is configured for `http://localhost:3000`.
- In-memory sliding-window rate limiting per client IP: 30 chat requests/min, 10 uploads/min (returns HTTP 429).
- Guardrails include:
  - Refusing personal medical advice (English/Spanish patterns)
  - Returning "I don't have enough information" when retrieval scores are low
  - Rejecting out-of-domain questions
  - Detecting prompt-injection attempts
  - Detecting PII/PHI patterns (email, SSN, phone) for audit logging (logged as flags only)
- File uploads are stored locally under `uploads/` (or the `uploaded_files` Docker volume).
- Input validation is performed via Pydantic schemas.
- This is a technical assessment and is **not intended for production use** without further hardening.

## CI/CD

The repository has one workflow: `.github/workflows/ci.yml`.

Triggers:
- `push` and `pull_request` to branch `main`

Jobs:
- **backend**:
  - Sets up Python 3.12
  - Installs backend dependencies (`pip install -e ".[dev]"`)
  - Enables pgvector extension
  - Runs Alembic migrations
  - Runs `pytest tests/unit tests/integration -v` (single run with combined coverage)
  - Lints with `ruff check .`
  - Type-checks with `mypy app`
- **frontend**:
  - Sets up Node 20 with npm cache keyed to `frontend/package-lock.json`
  - Runs `npm ci`
  - Runs `npm run lint`
  - Runs `npm run test:coverage` (Jest; enforces the 70% coverage floor)
  - Runs `npm run build`
- **smoke** (pull requests only, 30 min timeout):
  - Copies `.env.example` to `.env`
  - Runs `docker compose up --build -d`
  - Polls `http://localhost:8000/health` until healthy (up to 3 minutes)
  - Tears down with `docker compose down -v`

There is no deploy or CD stage.

## Development Conventions

- Backend follows **hexagonal / clean architecture**:
  - `domain/` — entities, value objects, abstract ports
  - `application/` — use-case services
  - `infrastructure/` — concrete adapters (Postgres, OpenAI, local storage)
  - Dependency inversion via repository and provider ports
- **Repository pattern**: `PostgresDocumentRepository`, `PostgresConversationRepository`
- **Provider pattern**: `LLMProvider` / `EmbeddingProvider` with OpenAI/Gemini/BGE adapters
- **Resilience wrappers**: `ResilientLLMProvider`, `ResilientEmbeddingProvider` add retry (only for classified `RetryableError`, with jittered backoff) + fallback; `NonRetryableError` fails fast
- **Worker idempotency**: Celery tasks skip completed/currently-processing documents; re-ingestion deletes existing chunks before saving; failed processing retains the uploaded file so it can be reprocessed via `POST /documents/{id}/reprocess` (the file is only removed when the document is deleted)
- **Agent loop**: lightweight LLM-based intent router classifies questions into `search`, `compare`, `extract`, `summarize` (plus `clarify`, which short-circuits with a clarification request instead of retrieval); when the conversation has history, the question is first rewritten into a standalone query (query contextualization) and recent turns are injected as chat messages into the answering prompt, so follow-up questions stay on-topic
- **Observability**: structured JSON logs via `structlog`; Prometheus counters/histograms for requests, latency, retrieval, tokens, fallback activations
- **Migrations**: managed with Alembic; initial migration is present in `backend/migrations/versions/`

## Known Caveats and Inconsistencies

- The `chunks.embedding` column dimension comes from `settings.embedding_dimension` (384 for the default BGE model, 1536 for OpenAI). Switching `EMBEDDING_PROVIDER` requires recreating the database or regenerating the Alembic migration.
- `frontend/app/chat/` and `frontend/app/documents/` route directories exist under the App Router; check nested `[conversationId]` / `[documentId]` segments for the actual pages.
- A `DATABASE_URL` without an async driver (e.g. plain `postgresql://`) is normalized to `postgresql+asyncpg://` in `app/infrastructure/db/connection.py`; environment variables take precedence over `.env`.
- Integration tests skip gracefully when PostgreSQL is unavailable; the MCP server tests run without a database via patched providers.
- Unit-test coverage is ~63% (floor: 60%, configured in `pyproject.toml`).
- The working tree has many uncommitted changes relative to the initial commit; exercise caution before assuming the repository matches `HEAD`.
