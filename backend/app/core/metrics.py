from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "rag_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "rag_latency_seconds",
    "Request latency",
    ["method", "endpoint"],
)

RETRIEVAL_LATENCY = Histogram(
    "rag_retrieval_latency_seconds",
    "Document retrieval latency",
)

LLM_TOKENS = Counter(
    "rag_llm_tokens_total",
    "Total LLM tokens used",
    ["model", "provider"],
)

FALLBACK_ACTIVATIONS = Counter(
    "rag_fallback_activations_total",
    "Fallback provider activations",
    ["provider_type"],
)

DOCUMENTS_PROCESSED = Counter(
    "rag_documents_processed_total",
    "Documents processed by the ingestion pipeline",
    ["status"],
)

INGESTION_ERRORS = Counter(
    "rag_ingestion_errors_total",
    "Document ingestion errors",
)
