"""Router for raw media assets (catalog §6: `POST /v1/uploads`,
`POST /v1/uploads/{uploadId}/complete`, `GET/DELETE /v1/media/{assetId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.media import MediaAccessResponse, UploadCreateRequest, UploadResponse
from app.services import media as media_service

router = APIRouter(tags=["media"])

_ASSET_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="MEDIA_ASSET_NOT_FOUND",
    title="Media asset not found",
)


@router.post("/v1/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    payload: UploadCreateRequest, current: CurrentSession = Depends(get_current_session)
) -> UploadResponse:
    asset = media_service.create_upload(
        current.account_id,
        payload.purpose,
        payload.content_type,
        payload.size_bytes,
        payload.checksum,
    )
    return UploadResponse(**asset)


@router.post(
    "/v1/uploads/{upload_id}/complete",
    response_model=MediaAccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def complete_upload(
    upload_id: str, current: CurrentSession = Depends(get_current_session)
) -> MediaAccessResponse:
    try:
        asset = media_service.complete_upload(current.account_id, upload_id)
    except media_service.AssetNotFoundError as exc:
        raise _ASSET_NOT_FOUND_ERROR from exc
    except media_service.UploadObjectMissingError as exc:
        raise ApiError(
            status=status.HTTP_404_NOT_FOUND,
            code="MEDIA_UPLOAD_OBJECT_MISSING",
            title="Uploaded object not found in storage",
        ) from exc
    except media_service.UploadSizeMismatchError as exc:
        raise ApiError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="MEDIA_UPLOAD_SIZE_MISMATCH",
            title="Uploaded object size does not match declared size",
            detail=f"Declared {exc.declared} bytes, actual {exc.actual} bytes",
        ) from exc
    except media_service.UploadNotCompletableError as exc:
        raise ApiError(
            status=status.HTTP_409_CONFLICT,
            code="MEDIA_UPLOAD_NOT_COMPLETABLE",
            title="Upload cannot be completed from its current state",
            detail=f"Current status: {exc.current_status}",
        ) from exc
    return MediaAccessResponse(**asset, download_url=None)


@router.get(
    "/v1/media/{asset_id}", response_model=MediaAccessResponse, status_code=status.HTTP_200_OK
)
async def get_media(
    asset_id: str, current: CurrentSession = Depends(get_current_session)
) -> MediaAccessResponse:
    try:
        asset = media_service.get_media(current.account_id, asset_id)
    except media_service.AssetNotFoundError as exc:
        raise _ASSET_NOT_FOUND_ERROR from exc
    return MediaAccessResponse(**asset)


@router.delete("/v1/media/{asset_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    asset_id: str, current: CurrentSession = Depends(get_current_session)
) -> None:
    try:
        media_service.delete_media(current.account_id, asset_id)
    except media_service.AssetNotFoundError as exc:
        raise _ASSET_NOT_FOUND_ERROR from exc
