from abc import ABC, abstractmethod

from app.domain.value_objects import RetrievedChunk


class SearchEngine(ABC):
    """Port for retrieving relevant chunks given a query."""

    @abstractmethod
    async def search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the most relevant chunks for the query."""
        raise NotImplementedError
