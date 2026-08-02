"""Data request application services (the authenticated /v1/me/data-requests surface)."""
from __future__ import annotations

from app.repositories import data_requests as data_requests_repo


class DataRequestNotFoundError(Exception):
    pass


def create_request(account_id: str, request_type: str, details: str | None) -> dict:
    return data_requests_repo.create_data_request(account_id, request_type, details)


def get_request(account_id: str, request_id: str) -> dict:
    item = data_requests_repo.get_data_request(account_id, request_id)
    if item is None:
        raise DataRequestNotFoundError(request_id)
    return item
