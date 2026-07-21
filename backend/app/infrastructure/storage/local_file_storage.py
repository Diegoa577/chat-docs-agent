from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.domain.ports.file_storage import FileStorage


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.uploads_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _document_dir(self, document_id: UUID) -> Path:
        directory = self.base_dir / str(document_id)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Reject path separators/traversal in upload filenames.

        Filenames are joined into the document directory, so a name like
        ``../../secret`` would escape it. Only a bare file name is allowed.
        """
        safe_name = Path(filename).name
        # Reject path separators explicitly as well: on POSIX a backslash is a
        # valid filename character but on Windows it is a path separator.
        if not safe_name or safe_name != filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename!r}")
        return safe_name

    async def save(self, document_id: UUID, filename: str, content: bytes) -> Path:
        directory = self._document_dir(document_id)
        file_path = directory / self._safe_filename(filename)
        file_path.write_bytes(content)
        return file_path

    async def get_path(self, document_id: UUID, filename: str) -> Path:
        return self._document_dir(document_id) / self._safe_filename(filename)

    async def delete(self, document_id: UUID, filename: str) -> None:
        file_path = await self.get_path(document_id, filename)
        if file_path.exists():
            file_path.unlink()
        directory = self._document_dir(document_id)
        if directory.exists() and not any(directory.iterdir()):
            directory.rmdir()
