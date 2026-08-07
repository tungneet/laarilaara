"""Account repository (DynamoDB single-table).

Key design for accounts:

- Account item:  PK = ``ACCOUNT#{id}``      SK = ``PROFILE``
- Email lookup:  a separate item keyed on GSI1 so we can find/uniquely reserve
  an account by email hash:
      PK = ``EMAILHASH#{hash}``  SK = ``EMAIL``  -> stores accountId
  Uniqueness is enforced with a conditional put (``attribute_not_exists``).
- Phone lookup: identical pattern, keyed by phone hash instead:
      PK = ``PHONEHASH#{hash}``  SK = ``PHONE``  -> stores accountId

Only this module knows the concrete key strings for accounts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from app.core.dynamodb import get_table
from app.core.security import email_lookup_hash, normalize_email, sha256_hex
from app.domain.accounts import Account, AccountRole, AccountStatus, AccountTier


class EmailAlreadyRegisteredError(Exception):
    pass


class PhoneAlreadyRegisteredError(Exception):
    pass


def _account_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _email_pk(email_hash: str) -> str:
    return f"EMAILHASH#{email_hash}"


def _phone_pk(phone_hash: str) -> str:
    return f"PHONEHASH#{phone_hash}"


def _to_item(account: Account, password_hash: str) -> dict:
    return {
        "PK": _account_pk(account.id),
        "SK": "PROFILE",
        "entityType": "Account",
        "id": account.id,
        "email": account.email,
        "phone": account.phone,
        "displayName": account.display_name,
        "gender": account.gender,
        "oauthProvider": account.oauth_provider,
        "oauthSubject": account.oauth_subject,
        "emailHash": email_lookup_hash(account.email) if account.email else None,
        "phoneHash": sha256_hex(account.phone) if account.phone else None,
        "passwordHash": password_hash,
        "status": account.status.value,
        "tier": account.tier.value,
        "role": account.role.value,
        "locale": account.locale,
        "createdAt": account.created_at.isoformat(),
        "updatedAt": account.updated_at.isoformat(),
    }


def _from_item(item: dict) -> Account:
    return Account(
        id=item["id"],
        email=item.get("email"),
        phone=item.get("phone"),
        display_name=item.get("displayName"),
        gender=item.get("gender"),
        oauth_provider=item.get("oauthProvider"),
        oauth_subject=item.get("oauthSubject"),
        status=AccountStatus(item["status"]),
        tier=AccountTier(item["tier"]),
        role=AccountRole(item.get("role", AccountRole.MEMBER.value)),
        locale=item.get("locale", "en"),
        created_at=item["createdAt"],
        updated_at=item["updatedAt"],
    )


def create_account(
    email: str,
    password_hash: str,
    locale: str = "en",
    display_name: str | None = None,
    gender: str | None = None,
) -> Account:
    """Create a new pending account, reserving the email atomically.

    Raises ``EmailAlreadyRegisteredError`` if the email is already taken.
    """
    table = get_table()
    normalized = normalize_email(email)
    email_hash = email_lookup_hash(normalized)
    account = Account(
        id=uuid.uuid4().hex,
        email=normalized,
        display_name=display_name,
        gender=gender,
        status=AccountStatus.PENDING_VERIFICATION,
        tier=AccountTier.FREE,
        locale=locale,
    )

    # Reserve the email first with a conditional put so concurrent registrations
    # for the same email cannot both succeed.
    try:
        table.put_item(
            Item={
                "PK": _email_pk(email_hash),
                "SK": "EMAIL",
                "entityType": "EmailReservation",
                "accountId": account.id,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise EmailAlreadyRegisteredError(email) from exc
        raise

    table.put_item(Item=_to_item(account, password_hash))
    return account


def get_account_by_id(account_id: str) -> Account | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _account_pk(account_id), "SK": "PROFILE"})
    item = resp.get("Item")
    return _from_item(item) if item else None


def create_phone_account(
    phone: str,
    display_name: str | None = None,
    gender: str | None = None,
    locale: str = "en",
) -> Account:
    """Create a new pending account for a first-time phone sign-in.

    Mirrors `create_account`'s email-reservation pattern exactly, but keyed
    by phone hash instead, and with no password (phone sign-in is always
    OTP-based, never a password) — stores the same kind of random, never-used
    password hash as OAuth accounts so `passwordHash` is never null.

    Raises ``PhoneAlreadyRegisteredError`` if the phone is already taken.
    """
    from app.core.security import generate_opaque_token, hash_password

    table = get_table()
    phone_hash = sha256_hex(phone)
    account = Account(
        id=uuid.uuid4().hex,
        phone=phone,
        display_name=display_name,
        gender=gender,
        status=AccountStatus.PENDING_VERIFICATION,
        tier=AccountTier.FREE,
        locale=locale,
    )
    unusable_password_hash = hash_password(generate_opaque_token())

    try:
        table.put_item(
            Item={
                "PK": _phone_pk(phone_hash),
                "SK": "PHONE",
                "entityType": "PhoneReservation",
                "accountId": account.id,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise PhoneAlreadyRegisteredError(phone) from exc
        raise

    table.put_item(Item=_to_item(account, unusable_password_hash))
    return account


def get_account_id_by_phone(phone: str) -> str | None:
    table = get_table()
    phone_hash = sha256_hex(phone)
    resp = table.get_item(Key={"PK": _phone_pk(phone_hash), "SK": "PHONE"})
    item = resp.get("Item")
    return item["accountId"] if item else None


def create_oauth_account(
    email: str,
    oauth_provider: str,
    oauth_subject: str,
    display_name: str | None = None,
    locale: str = "en",
) -> Account:
    """Create an account for a first-time OAuth sign-in (e.g. Google).

    The provider has already verified the email address, so the account is
    created directly ``active`` — no email-verification challenge needed.
    A random, never-used password hash is still stored so `passwordHash` is
    never null/missing (existing repo/login code assumes it's always a
    string); the account simply has no usable password until the holder
    later sets one via the password-reset flow.
    """
    from app.core.security import generate_opaque_token, hash_password

    table = get_table()
    normalized = normalize_email(email)
    email_hash = email_lookup_hash(normalized)
    account = Account(
        id=uuid.uuid4().hex,
        email=normalized,
        display_name=display_name,
        oauth_provider=oauth_provider,
        oauth_subject=oauth_subject,
        status=AccountStatus.ACTIVE,
        tier=AccountTier.FREE,
        locale=locale,
    )
    unusable_password_hash = hash_password(generate_opaque_token())

    try:
        table.put_item(
            Item={
                "PK": _email_pk(email_hash),
                "SK": "EMAIL",
                "entityType": "EmailReservation",
                "accountId": account.id,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise EmailAlreadyRegisteredError(email) from exc
        raise

    table.put_item(Item=_to_item(account, unusable_password_hash))
    return account


def set_oauth_identity(account_id: str, oauth_provider: str, oauth_subject: str) -> None:
    """Link an existing (e.g. email/password) account to an OAuth identity,
    the first time its verified email address is used to sign in via that
    provider."""
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": "PROFILE"},
        UpdateExpression="SET oauthProvider = :provider, oauthSubject = :subject, updatedAt = :now",
        ExpressionAttributeValues={
            ":provider": oauth_provider,
            ":subject": oauth_subject,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def get_account_id_by_email(email: str) -> str | None:
    table = get_table()
    email_hash = email_lookup_hash(normalize_email(email))
    resp = table.get_item(Key={"PK": _email_pk(email_hash), "SK": "EMAIL"})
    item = resp.get("Item")
    return item["accountId"] if item else None


def get_credentials_by_email(email: str) -> tuple[Account, str] | None:
    """Return (account, password_hash) for login, or None if no such email."""
    account_id = get_account_id_by_email(email)
    if account_id is None:
        return None

    table = get_table()
    resp = table.get_item(Key={"PK": _account_pk(account_id), "SK": "PROFILE"})
    item = resp.get("Item")
    if item is None:
        return None
    return _from_item(item), item["passwordHash"]


def mark_account_active(account_id: str) -> None:
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": "PROFILE"},
        UpdateExpression="SET #status = :active, updatedAt = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":active": AccountStatus.ACTIVE.value,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def set_password_hash(account_id: str, password_hash: str) -> None:
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": "PROFILE"},
        UpdateExpression="SET passwordHash = :hash, updatedAt = :now",
        ExpressionAttributeValues={
            ":hash": password_hash,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def update_locale(account_id: str, locale: str) -> None:
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": "PROFILE"},
        UpdateExpression="SET locale = :locale, updatedAt = :now",
        ExpressionAttributeValues={
            ":locale": locale,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def set_role(account_id: str, role: AccountRole) -> None:
    """White-box helper (catalog §15): grant/revoke the admin role.

    There is no API endpoint that calls this — matches the "no self-serve
    admin creation" gap noted in `app/domain/accounts.py`. Used by ops
    tooling (out of band) and directly by tests that need an admin session.
    """
    table = get_table()
    table.update_item(
        Key={"PK": _account_pk(account_id), "SK": "PROFILE"},
        UpdateExpression="SET #role = :role, updatedAt = :now",
        ExpressionAttributeNames={"#role": "role"},
        ExpressionAttributeValues={
            ":role": role.value,
            ":now": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def list_all_accounts() -> list[Account]:
    """Admin-only directory listing (catalog §15). Table scan — same
    documented "dev/test scale" tradeoff as `profiles_repo.list_all_profiles`.
    """
    table = get_table()
    items: list[dict] = []
    scan_kwargs: dict = {"FilterExpression": Attr("entityType").eq("Account")}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return [_from_item(item) for item in items]
