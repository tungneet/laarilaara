"""Profile-manager repository (DynamoDB single-table).

Manager item:  PK = ``PROFILE#{profileId}``   SK = ``MANAGER#{accountId}``

A profile always gets one manager row at creation time for its creating
account (role ``owner``, full permissions). The full invite/accept/revoke
manager system (catalog §5 "Managers and consent") is a later batch — this
module only supports what the lifecycle endpoints need: creating the owner
manager and checking permissions.

For the "one self-profile per account" idempotency rule, the owner's manager
row is additionally indexed on GSI1 (``GSI1PK = ACCOUNT#{accountId}``,
``GSI1SK = SELF``) only when the profile's relationship is ``self``, so it can
be looked up directly without a table scan.
"""
from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import GSI1_NAME, get_table

OWNER_PERMISSIONS = ["profile.read_private", "profile.edit", "profile.publish", "profile.manage_managers"]


class ManagerNotFoundError(Exception):
    pass


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _manager_sk(account_id: str) -> str:
    return f"MANAGER#{account_id}"


def create_owner_manager(
    profile_id: str, account_id: str, *, is_self_profile: bool
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    item = {
        "PK": _profile_pk(profile_id),
        "SK": _manager_sk(account_id),
        "entityType": "ProfileManager",
        "profileId": profile_id,
        "accountId": account_id,
        "role": "owner",
        "permissions": OWNER_PERMISSIONS,
        "isPrimary": True,
        "createdAt": now.isoformat(),
    }
    if is_self_profile:
        item["GSI1PK"] = f"ACCOUNT#{account_id}"
        item["GSI1SK"] = "SELF"
    table.put_item(Item=item)
    return item


def create_manager(
    profile_id: str,
    account_id: str,
    *,
    role: str,
    permissions: list[str],
    is_primary: bool = False,
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    item = {
        "PK": _profile_pk(profile_id),
        "SK": _manager_sk(account_id),
        "entityType": "ProfileManager",
        "profileId": profile_id,
        "accountId": account_id,
        "role": role,
        "permissions": permissions,
        "isPrimary": is_primary,
        "createdAt": now.isoformat(),
    }
    table.put_item(Item=item)
    return item


def get_manager(profile_id: str, account_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(
        Key={"PK": _profile_pk(profile_id), "SK": _manager_sk(account_id)}
    )
    return resp.get("Item")


def list_managers(profile_id: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _profile_pk(profile_id),
            ":sk_prefix": "MANAGER#",
        },
    )
    return resp.get("Items", [])


def list_manager_rows_for_account(account_id: str) -> list[dict]:
    """All manager rows held by ``account_id`` across every profile.

    Table scan filtered in DynamoDB — same dev/test-scale tradeoff as
    ``profiles_repo.list_published_profiles``. A GSI keyed on the account
    would replace this at real scale.
    """
    from boto3.dynamodb.conditions import Attr

    table = get_table()
    resp = table.scan(FilterExpression=Attr("SK").eq(_manager_sk(account_id)))
    return resp.get("Items", [])


def update_manager(
    profile_id: str,
    account_id: str,
    *,
    permissions: list[str] | None = None,
    is_primary: bool | None = None,
) -> dict:
    table = get_table()
    set_clauses = []
    names: dict = {}
    values: dict = {}
    if permissions is not None:
        set_clauses.append("#permissions = :permissions")
        names["#permissions"] = "permissions"
        values[":permissions"] = permissions
    if is_primary is not None:
        set_clauses.append("isPrimary = :isPrimary")
        values[":isPrimary"] = is_primary
    if not set_clauses:
        item = get_manager(profile_id, account_id)
        if item is None:
            raise ManagerNotFoundError(account_id)
        return item

    try:
        kwargs: dict = {
            "Key": {"PK": _profile_pk(profile_id), "SK": _manager_sk(account_id)},
            "UpdateExpression": "SET " + ", ".join(set_clauses),
            "ConditionExpression": "attribute_exists(PK)",
            "ExpressionAttributeValues": values,
            "ReturnValues": "ALL_NEW",
        }
        if names:
            kwargs["ExpressionAttributeNames"] = names
        resp = table.update_item(**kwargs)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ManagerNotFoundError(account_id) from exc
        raise
    return resp["Attributes"]


def unset_primary(profile_id: str, account_id: str) -> None:
    table = get_table()
    table.update_item(
        Key={"PK": _profile_pk(profile_id), "SK": _manager_sk(account_id)},
        UpdateExpression="SET isPrimary = :false",
        ExpressionAttributeValues={":false": False},
    )


def delete_manager(profile_id: str, account_id: str) -> None:
    table = get_table()
    try:
        table.delete_item(
            Key={"PK": _profile_pk(profile_id), "SK": _manager_sk(account_id)},
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ManagerNotFoundError(account_id) from exc
        raise


def find_self_profile_id(account_id: str) -> str | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression="GSI1PK = :pk AND GSI1SK = :sk",
        ExpressionAttributeValues={":pk": f"ACCOUNT#{account_id}", ":sk": "SELF"},
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0]["profileId"] if items else None
