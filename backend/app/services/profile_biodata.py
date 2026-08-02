"""Biodata generation service (catalog §6:
`POST /v1/profiles/{profileId}/biodata`, `GET /v1/profiles/{profileId}/biodata/{documentId}`).

Reuses the existing `profile_records.py` generic list/CRUD-record repo as-is
(kind=``BIODATA``) — no repo changes needed.

Known simplification (mirrors the `data_requests` "queued always, no worker
exists yet" convention): there is no async rendering Lambda worker in this
codebase, so generated documents stay ``queued`` forever with no
``download_url``. Unlike every §5 Sections write, generating a biodata
document does NOT bump the profile's aggregate version — it is a derived,
generated artifact, not a compatibility/discovery input.
"""
from __future__ import annotations

from app.repositories import profile_records as records_repo
from app.services import profiles as profiles_service

_BIODATA = "BIODATA"


class BiodataNotFoundError(Exception):
    pass


def generate_biodata(account_id: str, profile_id: str, template: str, locale: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    fields = {
        "template": template,
        "locale": locale,
        "status": "queued",
        "download_url": None,
    }
    return records_repo.create_record(profile_id, _BIODATA, fields)


def get_biodata(account_id: str, profile_id: str, document_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    record = records_repo.get_record(profile_id, _BIODATA, document_id)
    if record is None:
        raise BiodataNotFoundError(document_id)
    return record
