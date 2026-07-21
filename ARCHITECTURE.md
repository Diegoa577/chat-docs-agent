# Architecture Decision Record

## Overview

The Clinical Document Intelligence Agent is a monolithic FastAPI backend following hexagonal / clean architecture principles. The frontend is a Next.js 14 (App Router) application.

## Key Decisions

### 1. Monolith over microservices

**Decision**: Use a single deployable backend service.

**Rationale**:
- The assignment explicitly says "start simple."
- A single service keeps deployment, testing, and debugging straightforward.
- The workload is I/O-bound (LLM calls, DB, file parsing), so horizontal scaling of one service is sufficient for an interview demo.

### 2. PostgreSQL + pgvector as the unified store

**Decision**: Store relational document metadata, chunk text, embeddings, and full-text search vectors in PostgreSQL.

**Rationale**:
- Avoids operational complexity of a separate vector database.
- Enables ACID transactions across relational and vector data.
- Allows native hybrid retrieval (FTS + vector) in a single query.
- pgvector HNSW index supports efficient approximate nearest neighbor search.

### 3. Hybrid retrieval

**Decision**: Combine PostgreSQL full-text search (keyword/BM25-like) with pgvector cosine similarity.

**Rationale**:
- Keyword search excels at technical terms, IDs, and acronyms common in clinical/regulatory documents.
- Vector search captures semantic similarity and paraphrases.
- A weighted combination (`hybrid_alpha`) improves recall across query types.

### 4. Provider-agnostic LLM and embedding abstractions

**Decision**: Define `LLMProvider` and `EmbeddingProvider` ports with concrete adapters for OpenAI, Gemini, and a local Hugging Face/Sentence Transformers embedding provider.

**Rationale**:
- Avoids vendor lock-in.
- The default embedding provider (`BAAI/bge-small-en-v1.5`, 384 dimensions) runs locally and is free, eliminating embedding API costs.
- Makes testing with fakes trivial.
- Allows fallback between providers.

### 5. Router-based agent loop

**Decision**: Implement intent classification with a lightweight router rather than native LLM tool-use.

**Rationale**:
- Works consistently across all providers, including Gemini which has limited tool support.
- Easier to test and debug than tool-call parsing.
- Can be evolved to native tool-use later without changing the public API.

Supported intents:
- `search` — standard RAG Q&A
- `compare` — compare documents
- `extract` — extract structured regulatory entities
- `summarize` — summarize a section or document

Router output is validated with a Pydantic model (`IntentResult`); invalid or unparseable classifications fall back to `search`. When the knowledge base is empty, the agent short-circuits and asks the user to upload documents instead of calling the LLM.

### 6. Resilient provider wrappers

**Decision**: Wrap primary LLM and embedding providers with retry + fallback logic.

**Rationale**:
- LLM APIs are occasionally rate-limited or unavailable.
- A fallback provider improves availability without code changes in callers.
- Exponential backoff reduces retry storms.

**Implementation notes**:
- Provider exceptions are classified into `RetryableError` (rate limits, timeouts, 5xx) and `NonRetryableError` (auth, invalid requests); only retryable errors are retried.
- Backoff includes random jitter to avoid thundering herds.
- LLM clients are configured with a timeout (`provider_timeout_seconds`, default 60s).
- `LLMResponse.usage` is `None` when a provider does not report token usage.

### 7. Conversation persistence as JSON

**Decision**: Store conversation messages as a JSON array in the `conversations` table.

**Rationale**:
- Message schema is simple and unlikely to require complex querying.
- Avoids a separate `messages` table and join overhead.
- Metadata (retrieved chunks, confidence, model) is stored per assistant message for audit.

### 8. Async workers for ingestion

**Decision**: Use Celery + Redis for document parsing, chunking, and embedding.

**Rationale**:
- Ingestion is slow and should not block the upload API.
- Celery provides retries, monitoring, and horizontal worker scaling.

**Idempotency**:
- The task skips documents already `completed` (or recently `processing`) to avoid duplicate work on redelivery.
- Re-ingestion deletes existing chunks for the document before saving new ones (`delete_chunks_by_document`), so reprocessing never duplicates chunks.
- On final failure (retries exhausted), the uploaded file is removed from storage.

### 9. MCP server as a separate entry point

**Decision**: Provide a FastMCP server in `backend/mcp_server` that reuses the same domain services.

**Rationale**:
- Exposes document intelligence to external agents (e.g., an MCP-compatible client).
- Shares the same search engine and resilient LLM providers as the API.

Tools: `search_documents`, `compare_documents`, `extract_entities`, `list_documents`. Every tool wraps failures and returns a JSON `error` field instead of raising.

### 10. Domain ports for parsing and search

**Decision**: `DocumentParser` and `SearchEngine` are domain ports (`app/domain/ports/`), with concrete adapters in infrastructure (`PyMuPDFParser` factory, `HybridSearchEngine`).

**Rationale**:
- Application services depend only on domain abstractions (no infrastructure imports in `application/`), keeping the hexagon clean.
- The embedding provider is injected into the search engine, so query embeddings reuse the same resilient provider as ingestion.
- Hybrid search only returns chunks from `completed` documents and skips chunks without embeddings.

## Layer Structure

```
app/
├── api/              # FastAPI routes, schemas, middleware
├── application/      # Services and use-case orchestration
├── domain/           # Entities, value objects, repository ports, provider ports
├── infrastructure/   # Concrete adapters: DB, LLM, embeddings, parsers, search
├── core/             # Config, logging, metrics, dependencies
└── tasks/            # Celery tasks
```

## Testing Strategy

- **Unit tests**: chunking, guardrails, agent router, chat service, ingestion, document service, parsers, storage, rate limiter, resilient providers, API schemas.
- **Integration tests**: API routes, MCP tools, Postgres repositories, health endpoints, end-to-end upload/chat/delete flows. Integration tests skip gracefully when PostgreSQL is unavailable.
- **Evals**: retrieval recall, LLM-as-judge faithfulness and relevance.
- All external calls are mocked in CI.
- `mypy`, `ruff`, and `pytest --cov` run in CI with a 60% coverage floor.

## Observability

Prometheus metrics exposed at `/metrics`:
- `rag_requests_total`
- `rag_latency_seconds`
- `rag_retrieval_latency_seconds`
- `rag_llm_tokens_total`
- `rag_fallback_activations_total`
- `rag_documents_processed_total` (by status)
- `rag_ingestion_errors_total`

Readiness (`/ready`) checks provider configuration, database connectivity, and Redis (Celery broker) connectivity.

Structured logs use `structlog` with JSON formatting.

## Security & Guardrails

- Input validation via Pydantic schemas.
- Out-of-domain question detection (keyword-based).
- Personal medical advice refusal (English/Spanish patterns).
- Prompt-injection detection.
- PII/PHI pattern detection (email, SSN, phone) for audit purposes; detections are logged as flags, never with contents.
- In-memory sliding-window rate limiting per client IP (chat: 30/min, uploads: 10/min).
- File upload size limits enforced at the API boundary.
- `strict_mode` on chat rejects non-high-confidence answers to reduce hallucination risk.
- No authentication in this demo; production would add OAuth2/JWT and RBAC.

> **Note:** guardrails are intentionally simple for the demo. A production system would use a trained classifier and a dedicated policy engine.
