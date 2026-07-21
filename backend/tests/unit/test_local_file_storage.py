from uuid import uuid4

import pytest

from app.infrastructure.storage.local_file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_save_and_get_path(storage: LocalFileStorage):
    document_id = uuid4()
    content = b"clinical protocol content"

    path = await storage.save(document_id, "protocol.txt", content)
    resolved_path = await storage.get_path(document_id, "protocol.txt")

    assert path.exists()
    assert resolved_path == path
    assert resolved_path.read_bytes() == content


@pytest.mark.asyncio
async def test_delete_removes_file_and_directory(storage: LocalFileStorage):
    document_id = uuid4()
    await storage.save(document_id, "protocol.txt", b"content")

    await storage.delete(document_id, "protocol.txt")

    file_path = await storage.get_path(document_id, "protocol.txt")
    assert not file_path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", ["../../etc/passwd", "..\\secret.txt", "sub/dir.pdf", ""])
async def test_save_rejects_path_traversal_filenames(storage: LocalFileStorage, filename: str):
    with pytest.raises(ValueError, match="Invalid filename"):
        await storage.save(uuid4(), filename, b"content")


@pytest.mark.asyncio
async def test_get_path_rejects_path_traversal_filenames(storage: LocalFileStorage):
    with pytest.raises(ValueError, match="Invalid filename"):
        await storage.get_path(uuid4(), "../../etc/passwd")


@pytest.mark.asyncio
async def test_traversal_write_does_not_escape_base_dir(storage: LocalFileStorage, tmp_path):
    with pytest.raises(ValueError):
        await storage.save(uuid4(), "../escaped.txt", b"content")
    assert not (tmp_path / "escaped.txt").exists()
