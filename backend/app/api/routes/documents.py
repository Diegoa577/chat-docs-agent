from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies.rate_limiter import check_upload_rate_limit
from app.api.schemas.document import DocumentListResponse, DocumentResponse
from app.application.services.document_service import (
    DocumentService,
    DocumentStateConflictError,
)
from app.core.config import settings
from app.core.dependencies import (
    get_document_repository,
    get_file_storage,
    get_task_runner,
)
from app.domain.ports.file_storage import FileStorage
from app.domain.ports.task_runner import TaskRunner
from app.domain.repositories.document_repository import DocumentRepository

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
    task_runner: Annotated[TaskRunner, Depends(get_task_runner)],
) -> DocumentService:
    return DocumentService(repository, file_storage, task_runner)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    http_request: Request,
    file: Annotated[UploadFile, File(...)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    check_upload_rate_limit(http_request)
    if not file.filename or not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file",
        )

    content = await file.read()

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    document = await service.upload_document(
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    return DocumentResponse.model_validate(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    service: Annotated[DocumentService, Depends(get_document_service)],
    limit: int = 100,
    offset: int = 0,
) -> DocumentListResponse:
    documents = await service.list_documents(limit=limit, offset=offset)
    return DocumentListResponse(documents=[DocumentResponse.model_validate(d) for d in documents])


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> FileResponse:
    result = await service.get_document_file(document_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    path, filename, content_type = result
    return FileResponse(path, media_type=content_type, filename=filename)


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_document(
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    try:
        document = await service.reprocess_document(document_id)
    except DocumentStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    try:
        await service.delete_document(document_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
