from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID


class FileStorage(ABC):
    @abstractmethod
    async def save(self, document_id: UUID, filename: str, content: bytes) -> Path:
        raise NotImplementedError

    @abstractmethod
    async def get_path(self, document_id: UUID, filename: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: UUID, filename: str) -> None:
        raise NotImplementedError
