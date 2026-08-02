"""Shared test fixtures.

Uses moto to mock DynamoDB so tests need no AWS account or local DynamoDB. The
single table is created fresh per test and repository module caches are cleared
so each test gets an isolated table.
"""
from __future__ import annotations

import os

import pytest

# Ensure boto3 never touches real AWS during tests.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# Force the free/deterministic AI provider for the whole test suite, no matter
# what a developer's local .env has configured (e.g. `openai` for real manual
# testing) — tests must never make real, paid, network-dependent AI calls.
# `setdefault` still lets an explicit env var override this on purpose (e.g. a
# dedicated opt-in integration test run against the real provider).
os.environ.setdefault("LAARA_AI__PROVIDER", "fake")
os.environ.setdefault("LAARA_AI__MODERATION_PROVIDER", "fake")


@pytest.fixture()
def dynamo_table():
    from moto import mock_aws

    with mock_aws():
        from app.core import dynamodb

        # Clear the cached table/resource so it binds to the mocked backend.
        dynamodb.get_table.cache_clear()
        dynamodb.create_table_if_missing()
        yield dynamodb.get_table()
        dynamodb.get_table.cache_clear()


@pytest.fixture()
def media_bucket(dynamo_table):
    """Creates the media S3 bucket inside the same `mock_aws()` context as
    `dynamo_table` (moto mocks all AWS services at once, so DynamoDB and S3
    mocking coexist within one active `mock_aws()` block)."""
    from app.core import s3
    from app.core.config import get_settings

    s3.get_s3_client.cache_clear()
    client = s3.get_s3_client()
    settings = get_settings()
    client.create_bucket(Bucket=settings.storage.media_bucket_name)
    yield settings.storage.media_bucket_name
    s3.get_s3_client.cache_clear()
