"""Media upload/access service (catalog §6: `POST /v1/uploads`,
`POST /v1/uploads/{uploadId}/complete`, `GET/DELETE /v1/media/{assetId}`).

Known simplification (documented for later): there is no SQS queue or media
worker Lambda in this codebase yet, so `complete_upload` performs the
head-object/size validation synchronously and transitions the asset straight
to ``ready`` — no async virus/content scanning or quarantine step exists yet.
A profile cannot be published with unscanned/rejected/quarantined media per
the catalog, but since nothing ever produces `rejected`/`quarantined` today,
that publish-time check has nothing to enforce against yet.
"""
from __future__ import annotations

from app.core import s3
from app.core.config import get_settings
from app.repositories import media_assets as media_assets_repo


class AssetNotFoundError(Exception):
    pass


class AssetForbiddenError(Exception):
    pass


class UploadNotCompletableError(Exception):
    def __init__(self, current_status: str) -> None:
        super().__init__(f"cannot complete upload in state: {current_status}")
        self.current_status = current_status


class UploadObjectMissingError(Exception):
    pass


class UploadSizeMismatchError(Exception):
    def __init__(self, declared: int, actual: int) -> None:
        super().__init__(f"declared size {declared} does not match uploaded size {actual}")
        self.declared = declared
        self.actual = actual


def _get_owned_asset(account_id: str, asset_id: str) -> dict:
    asset = media_assets_repo.get_asset(asset_id)
    if asset is None:
        raise AssetNotFoundError(asset_id)
    if asset["account_id"] != account_id:
        # Existence-masking: report not-found rather than forbidden.
        raise AssetNotFoundError(asset_id)
    return asset


def create_upload(
    account_id: str, purpose: str, content_type: str, size_bytes: int, checksum: str
) -> dict:
    existing = media_assets_repo.find_by_account_checksum(account_id, checksum)
    if existing is not None and existing["status"] in ("pending", "ready"):
        asset = existing
    else:
        asset = media_assets_repo.create_upload(
            account_id, purpose, content_type, size_bytes, checksum
        )

    settings = get_settings()
    upload_url = s3.generate_presigned_put_url(
        settings.storage.media_bucket_name, asset["storage_key"], asset["content_type"]
    )
    return {k: v for k, v in asset.items() if k != "storage_key"} | {"upload_url": upload_url}


def complete_upload(account_id: str, asset_id: str) -> dict:
    asset = _get_owned_asset(account_id, asset_id)
    if asset["status"] == "ready":
        return {k: v for k, v in asset.items() if k != "storage_key"}
    if asset["status"] != "pending":
        raise UploadNotCompletableError(asset["status"])

    settings = get_settings()
    head = s3.head_object(settings.storage.media_bucket_name, asset["storage_key"])
    if head is None:
        raise UploadObjectMissingError(asset_id)
    actual_size = head.get("ContentLength")
    if actual_size is not None and actual_size != asset["size_bytes"]:
        raise UploadSizeMismatchError(asset["size_bytes"], actual_size)

    updated = media_assets_repo.mark_ready(asset_id)
    return {k: v for k, v in updated.items() if k != "storage_key"}


def get_media(account_id: str, asset_id: str) -> dict:
    asset = _get_owned_asset(account_id, asset_id)
    download_url = None
    if asset["status"] == "ready":
        settings = get_settings()
        download_url = s3.generate_presigned_get_url(
            settings.storage.media_bucket_name, asset["storage_key"]
        )
    return {k: v for k, v in asset.items() if k != "storage_key"} | {"download_url": download_url}


def delete_media(account_id: str, asset_id: str) -> None:
    asset = _get_owned_asset(account_id, asset_id)
    if asset["status"] == "deleted":
        return
    media_assets_repo.soft_delete(asset_id)
