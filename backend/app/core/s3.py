"""S3 access for media uploads/downloads (catalog §6). Bytes never pass
through API Gateway/Lambda — the API only creates/consumes short-lived
presigned URLs.

The boto3 client is created lazily and cached per Lambda execution
environment, mirroring `app.core.dynamodb.get_table`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_s3.client import S3Client


@lru_cache
def get_s3_client() -> "S3Client":
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=settings.storage.s3_endpoint_url,
    )


def generate_presigned_put_url(bucket: str, key: str, content_type: str, expires_in: int = 900) -> str:
    settings = get_settings()
    if settings.storage.s3_endpoint_url:
        # Moto 5 rejects browser OPTIONS requests carrying its signature query.
        # The local server is credential-free, so use its unsigned object URL.
        endpoint = settings.storage.s3_endpoint_url.rstrip("/")
        return f"{endpoint}/{quote(bucket, safe='')}/{quote(key, safe='/')}"

    client = get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def generate_presigned_get_url(bucket: str, key: str, expires_in: int = 300) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def head_object(bucket: str, key: str) -> dict | None:
    """Return object metadata (including ``ContentLength``), or ``None`` if
    the object does not exist (or the bucket does not exist)."""
    client = get_s3_client()
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchKey", "NoSuchBucket"):
            return None
        raise
