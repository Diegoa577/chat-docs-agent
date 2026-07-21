from openai import AsyncOpenAI

from app.core.config import settings
from app.domain.ports.embedding_provider import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model or settings.openai_embedding_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Replace newlines to improve embedding quality
        texts = [t.replace("\n", " ") for t in texts]
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def get_dimension(self) -> int:
        return settings.openai_embedding_model_dimension

    def get_model_name(self) -> str:
        return self.model
