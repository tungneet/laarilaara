"""Contact management application services (the authenticated /v1/me/contacts surface)."""
from __future__ import annotations

from app.repositories import challenges as challenges_repo
from app.repositories import contacts as contacts_repo
from app.services.notifications import generate_numeric_code, send_verification_code


class ContactNotFoundError(Exception):
    pass


class ContactInvalidError(Exception):
    """Wrong/expired code, or no pending challenge to verify against."""


class CannotRemoveLastVerifiedContactError(Exception):
    pass


def _mask(contact_type: str, value: str) -> str:
    if contact_type == "email":
        local, _, domain = value.partition("@")
        masked_local = local[0] + "***" if local else "***"
        return f"{masked_local}@{domain}" if domain else masked_local
    # phone: keep only the last 4 digits visible
    return "*" * max(len(value) - 4, 0) + value[-4:]


def _to_view(item: dict) -> dict:
    return {
        "id": item["id"],
        "type": item["type"],
        "masked_value": _mask(item["type"], item["value"]),
        "verified": item["verified"],
        "created_at": item["createdAt"],
    }


def list_contacts(account_id: str) -> list[dict]:
    return [_to_view(item) for item in contacts_repo.list_contacts(account_id)]


def add_contact(account_id: str, contact_type: str, value: str) -> dict:
    """Add a contact, or resend a challenge for an existing unverified one.

    Idempotent: re-adding the same (type, value) pair reuses the existing
    contact record rather than creating a duplicate.
    """
    existing = contacts_repo.find_by_value(account_id, contact_type, value)
    if existing is not None and existing["verified"]:
        return _to_view(existing)

    contact = existing or contacts_repo.create_contact(account_id, contact_type, value)

    code = generate_numeric_code()
    challenge = challenges_repo.create_contact_verification_challenge(
        account_id, code, contact["id"]
    )
    contacts_repo.set_pending_challenge(account_id, contact["id"], challenge.id)
    send_verification_code(value, code, challenge.id)
    return _to_view(contact)


def verify_contact(account_id: str, contact_id: str, code: str) -> dict:
    contact = contacts_repo.get_contact(account_id, contact_id)
    if contact is None:
        raise ContactNotFoundError(contact_id)
    if contact["verified"]:
        return _to_view(contact)
    pending_challenge_id = contact.get("pendingChallengeId")
    if not pending_challenge_id:
        raise ContactInvalidError("no_pending_challenge")

    challenge_account_id, subject_id = challenges_repo.verify_and_consume(
        pending_challenge_id, code, expected_purpose="contact_verification"
    )
    if challenge_account_id != account_id or subject_id != contact_id:
        raise ContactInvalidError("challenge_subject_mismatch")

    contacts_repo.mark_verified(account_id, contact_id)
    contact = contacts_repo.get_contact(account_id, contact_id)
    return _to_view(contact)


def remove_contact(account_id: str, contact_id: str) -> None:
    contact = contacts_repo.get_contact(account_id, contact_id)
    if contact is None:
        raise ContactNotFoundError(contact_id)

    if contact["verified"]:
        other_verified = [
            item
            for item in contacts_repo.list_contacts(account_id)
            if item["id"] != contact_id and item["verified"]
        ]
        if not other_verified:
            raise CannotRemoveLastVerifiedContactError(contact_id)

    contacts_repo.delete_contact(account_id, contact_id)
