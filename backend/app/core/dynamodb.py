"""DynamoDB single-table access.

The whole hot path uses one DynamoDB table with a generic key schema:

- ``PK`` (partition) / ``SK`` (sort): primary access pattern.
- ``GSI1PK`` / ``GSI1SK``: one global secondary index for alternate lookups
  (for example email -> account).

Item ``entityType`` distinguishes record kinds. Repositories build the concrete
key strings; nothing outside this layer talks to boto3 directly.

The boto3 resource is created lazily and cached per Lambda execution
environment so warm invocations reuse the client.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3

from app.core.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_dynamodb.service_resource import Table

GSI1_NAME = "GSI1"


@lru_cache
def get_table() -> "Table":
    settings = get_settings()
    resource = boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.storage.dynamodb_endpoint_url,
    )
    return resource.Table(settings.storage.dynamodb_table_name)


def create_table_if_missing() -> None:
    """Create the single table with its GSI. Used for local dev and tests.

    Production tables are provisioned by infrastructure-as-code, not this
    function.
    """
    settings = get_settings()
    client = boto3.client(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.storage.dynamodb_endpoint_url,
    )
    existing = client.list_tables().get("TableNames", [])
    if settings.storage.dynamodb_table_name in existing:
        return

    client.create_table(
        TableName=settings.storage.dynamodb_table_name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI1_NAME,
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    client.get_waiter("table_exists").wait(
        TableName=settings.storage.dynamodb_table_name
    )
