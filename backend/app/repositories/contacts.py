"""Contact repository (DynamoDB single-table).

Contact item:
    PK = ``ACCOUNT#{accountId}``   SK = ``CONTACT#{contactId}``

A contact is an email address or phone number attached to the account beyond
(or including) the primary login email. Only the hash of nothing sensitive is
stored here — the contact value itself is stored in the clear (it is PII but
not a credential); responses mask it before it ever leaves the service layer.
No GSI needed: contacts are only ever looked up scoped to their own account.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import get_table


class ContactNotFoundError(Exception):
    pass


def _account_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _contact_sk(contact_id: str) -> str:
    return f"CONTACT#{contact_id}"


def create_contact(account_id: str, contact_type: str, value: str) -> dict:
    table = get_table()
    contact_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _account_pk(account_id),
        "SK": _contact_sk(contact_id),
        "entityType": "Contact",
        "id": contact_id,
        "accountId": account_id,
        "type": contact_type,
        "value": value,
        "verified": False,
        "pendingChallengeId": None,
        "createdAt": now,
        "updatedAt": now,
    }
    table.put_item(Item=item)
    return item


def get_contact(account_id: str, contact_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(
        Key={"PK": _account_pk(account_id), "SK": _contact_sk(contact_id)}
    )
    return resp.get("Item")


def find_by_value(account_id: str, contact_type: str, value: str) -> dict | None:
    for item in list_contacts(account_id):
        if item["type"] == contact_type and item["value"] == value:
            return item
    return None


def list_contacts(account_id: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _account_pk(account_id),
            ":sk_prefix": "CONTACT#",
        },
    )
    return resp.get("Items", [])


def set_pending_challenge(account_id: str, contact_id: str, challenge_id: str) -> None:
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": _contact_sk(contact_id)},
        UpdateExpression="SET pendingChallengeId = :cid, updatedAt = :now",
        ExpressionAttributeValues={
            ":cid": challenge_id,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def mark_verified(account_id: str, contact_id: str) -> None:
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": _contact_sk(contact_id)},
        UpdateExpression="SET verified = :true, pendingChallengeId = :none, updatedAt = :now",
        ExpressionAttributeValues={
            ":true": True,
            ":none": None,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def delete_contact(account_id: str, contact_id: str) -> None:
    table = get_table()
    try:
        table.delete_item(
            Key={"PK": _account_pk(account_id), "SK": _contact_sk(contact_id)},
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ContactNotFoundError(contact_id) from exc
        raise
