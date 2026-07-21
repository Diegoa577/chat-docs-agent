import asyncio
from concurrent.futures import ThreadPoolExecutor

from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.domain.ports.embedding_provider import EmbeddingProvider

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bge_embed_")


class BGEEmbeddingProvider(EmbeddingProvider):
    """Local Hugging Face embedding provider using sentence-transformers.

    Default model: BAAI/bge-small-en-v1.5 (free, local, 384 dimensions).
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.bge_model_name
        # Lazy-load the model on first use to avoid import-time overhead.
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # sentence-transformers is synchronous and CPU-bound; offload to a thread.
        model = self._get_model()
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            _executor,
            lambda: model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
        )
        return [embedding.tolist() for embedding in embeddings]

    def get_dimension(self) -> int:
        return settings.bge_model_dimension

    def get_model_name(self) -> str:
        return self.model_name
