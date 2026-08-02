"""End-to-end connection smoke test against a RUNNING dev server (real HTTP).

Complements the in-process pytest suite (which already covers the full
contract) by verifying the deployed-style wiring: real uvicorn server, real
HTTP, auth headers, CORS preflight, and a representative endpoint from every
catalog section that is reachable without white-box seeding.

Two phases, because email verification codes are delivered out-of-band (the
dev server logs them; the operator reads them from the server terminal):

    python scripts/smoke_test.py phase_a
        → health/reference checks + registers two accounts (prints emails)
    python scripts/smoke_test.py phase_b --a-chal ID --a-code C --b-chal ID --b-code C
        → verify/login both, then walk the full cross-profile journey.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
FRONTEND_ORIGIN = "http://localhost:3000"
PASSWORD = "correct horse battery staple"
WEBHOOK_SECRET = "insecure-local-dev-webhook-secret-change-me"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, info: str = "") -> None:
    RESULTS.append((name, ok, info))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({info})" if info else ""))


def report() -> None:
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED:")
        for name, _, info in failed:
            print(f"  - {name} {info}")
        sys.exit(1)


def phase_a(client: httpx.Client) -> None:
    r = client.get(f"{BASE}/health/live")
    check("health/live 200", r.status_code == 200, str(r.status_code))
    r = client.get(f"{BASE}/health/ready")
    check("health/ready 200", r.status_code == 200, str(r.status_code))

    r = client.get(f"{BASE}/openapi.json")
    check("openapi schema served", r.status_code == 200 and "paths" in r.json())

    r = client.get(f"{BASE}/v1/context")
    check("reference /v1/context", r.status_code == 200)
    r = client.get(f"{BASE}/v1/reference/communities")
    check("reference communities list", r.status_code == 200 and len(r.json()) > 0)

    # CORS preflight exactly as the browser frontend would send it.
    r = client.options(
        f"{BASE}/v1/auth/login",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    check(
        "CORS preflight allows frontend origin",
        r.status_code == 200
        and r.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN,
        f"status={r.status_code} allow-origin={r.headers.get('access-control-allow-origin')}",
    )

    for label in ("a", "b"):
        r = client.post(
            f"{BASE}/v1/auth/register",
            json={"email": f"smoke-{label}@example.com", "password": PASSWORD},
        )
        check(f"register account {label.upper()} (202)", r.status_code == 202, str(r.status_code))

    print("\nNow read the two challenge ids + codes from the dev-server log and run phase_b.")
    report()


def _login(client: httpx.Client, email: str) -> dict:
    r = client.post(f"{BASE}/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, f"login {email} -> {r.status_code}: {r.text}"
    return r.json()


def phase_b(client: httpx.Client, args: argparse.Namespace) -> None:
    # --- §4 auth: verify + login + me + refresh ---
    for label, chal, code in (("A", args.a_chal, args.a_code), ("B", args.b_chal, args.b_code)):
        r = client.post(f"{BASE}/v1/auth/challenges/{chal}/verify", json={"code": code})
        check(f"verify challenge {label}", r.status_code == 200, str(r.status_code))

    tokens_a = _login(client, "smoke-a@example.com")
    tokens_b = _login(client, "smoke-b@example.com")
    check("login A+B returns tokens", bool(tokens_a["access_token"] and tokens_b["access_token"]))
    ha = {"Authorization": f"Bearer {tokens_a['access_token']}"}
    hb = {"Authorization": f"Bearer {tokens_b['access_token']}"}

    r = client.get(f"{BASE}/v1/me", headers=ha)
    check("GET /v1/me", r.status_code == 200 and r.json()["email"] == "smoke-a@example.com")

    r = client.post(f"{BASE}/v1/auth/refresh", json={"refresh_token": tokens_a["refresh_token"]})
    check("refresh rotates tokens", r.status_code == 200 and r.json()["access_token"])
    ha = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get(f"{BASE}/v1/me")
    check("unauthenticated /v1/me rejected (401)", r.status_code == 401, str(r.status_code))

    # --- §5 profiles: create, sections, submit, publish ---
    profiles = {}
    for label, headers, gender, dob in (("a", ha, "male", "1996-02-11"), ("b", hb, "female", "1997-08-23")):
        r = client.post(f"{BASE}/v1/profiles", json={"relationship": "self"}, headers=headers)
        check(f"create profile {label.upper()}", r.status_code == 201)
        pid = r.json()["id"]
        profiles[label] = pid
        r = client.patch(
            f"{BASE}/v1/profiles/{pid}/personal-details",
            json={"gender": gender, "date_of_birth": dob},
            headers=headers,
        )
        check(f"patch personal-details {label.upper()}", r.status_code == 200)
        r = client.put(
            f"{BASE}/v1/profiles/{pid}/communities", json={"values": ["jatt-sikh"]}, headers=headers
        )
        check(f"put communities {label.upper()}", r.status_code == 200, str(r.status_code))
        r = client.post(f"{BASE}/v1/profiles/{pid}/submit", headers=headers)
        check(f"submit profile {label.upper()}", r.status_code == 200, str(r.status_code))
        r = client.post(f"{BASE}/v1/profiles/{pid}/publish", headers=headers)
        check(f"publish profile {label.upper()}", r.status_code == 200, str(r.status_code))

    pa, pb = profiles["a"], profiles["b"]

    r = client.get(f"{BASE}/v1/profiles/{pa}/completion", headers=ha)
    check("profile completion view", r.status_code == 200)

    # Existence masking: B's profile details must 404 for A's direct get.
    r = client.get(f"{BASE}/v1/profiles/{pb}", headers=ha)
    check("non-manager profile get masked (404)", r.status_code == 404, str(r.status_code))

    # --- §7 discovery ---
    r = client.post(
        f"{BASE}/v1/discovery/search",
        params={"acting_profile_id": pa},
        json={"filters": {"gender": "female", "min_age": 20, "max_age": 40}},
        headers=ha,
    )
    found = r.status_code == 200 and any(i["profile_id"] == pb for i in r.json()["items"])
    check("discovery search finds published B", found, str(r.status_code))

    r = client.put(
        f"{BASE}/v1/shortlist/{pb}",
        params={"acting_profile_id": pa},
        json={"note": "promising match"},
        headers=ha,
    )
    check("shortlist add", r.status_code in (200, 201), str(r.status_code))

    r = client.post(
        f"{BASE}/v1/saved-searches",
        params={"acting_profile_id": pa},
        json={"name": "smoke", "filters": {"gender": "female"}},
        headers=ha,
    )
    check("saved search create", r.status_code == 201, str(r.status_code))

    # --- §8 interests -> match ---
    r = client.post(
        f"{BASE}/v1/interests",
        params={"acting_profile_id": pa},
        json={"target_profile_id": pb, "message": "Sat Sri Akal!"},
        headers=ha,
    )
    check("send interest A->B", r.status_code == 201, str(r.status_code))
    interest_id = r.json()["id"]

    r = client.post(
        f"{BASE}/v1/interests/{interest_id}/accept",
        params={"acting_profile_id": pb},
        headers=hb,
    )
    ok = r.status_code == 200 and r.json().get("match_id")
    check("accept interest -> match", bool(ok), str(r.status_code))
    match_id = r.json()["match_id"]

    r = client.get(
        f"{BASE}/v1/matches/{match_id}", params={"acting_profile_id": pa}, headers=ha
    )
    conversation_id = r.json().get("conversation_id") if r.status_code == 200 else None
    check("match carries conversation_id", bool(conversation_id), str(r.status_code))

    # --- §9 messaging (REST) ---
    r = client.post(
        f"{BASE}/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": pa},
        json={"client_message_id": uuid.uuid4().hex, "body": "Hello from the smoke test"},
        headers=ha,
    )
    check("send message", r.status_code == 201, str(r.status_code))

    r = client.get(
        f"{BASE}/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": pb},
        headers=hb,
    )
    got = r.status_code == 200 and any(
        m["body"] == "Hello from the smoke test" for m in r.json()["items"]
    )
    check("other participant reads message", got, str(r.status_code))

    r = client.post(f"{BASE}/v1/realtime-tokens", json={"profile_id": pa}, headers=ha)
    check("realtime token minted", r.status_code in (200, 201) and bool(r.json().get("token")), str(r.status_code))

    # --- §10 AI (artifact queued; no worker by design) ---
    r = client.post(
        f"{BASE}/v1/profiles/{pa}/ai/bio-drafts",
        json={"tone": "warm"},
        headers=ha,
    )
    check("AI bio-draft queued", r.status_code == 202 and r.json().get("status") == "queued", str(r.status_code))

    # --- §11 trust ---
    r = client.get(f"{BASE}/v1/profiles/{pa}/trust-summary", params={"acting_profile_id": pa}, headers=ha)
    check("trust summary", r.status_code == 200)

    # --- §12 notifications ---
    r = client.get(f"{BASE}/v1/notification-preferences", headers=ha)
    check("notification preferences (default)", r.status_code == 200)

    # --- §13 billing/entitlements ---
    r = client.get(f"{BASE}/v1/entitlements", headers=ha)
    check("entitlements view", r.status_code == 200)
    r = client.get(f"{BASE}/v1/billing/subscription", headers=ha)
    check("subscription (lazy free)", r.status_code == 200 and r.json().get("plan_id") == "free", str(r.status_code))

    # --- §14 webhooks (HMAC, no bearer) ---
    body = json.dumps({"id": f"evt_{uuid.uuid4().hex}", "amount": 100}).encode()
    ts = str(int(time.time()))
    sig = hmac.new(WEBHOOK_SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    r = client.post(
        f"{BASE}/v1/webhooks/billing/stripe",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": ts,
            "X-Webhook-Signature": sig,
        },
    )
    check("webhook HMAC accepted", r.status_code == 200, str(r.status_code))

    bad = client.post(
        f"{BASE}/v1/webhooks/billing/stripe",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": ts,
            "X-Webhook-Signature": "0" * 64,
        },
    )
    check("webhook bad signature rejected (401)", bad.status_code == 401, str(bad.status_code))

    # --- §6 media (upload create only; the presigned PUT itself is S3-side) ---
    r = client.post(
        f"{BASE}/v1/uploads",
        json={
            "purpose": "profile_photo",
            "content_type": "image/jpeg",
            "size_bytes": 1234,
            "checksum": hashlib.sha256(b"smoke").hexdigest(),
        },
        headers=ha,
    )
    check("upload slot + presigned URL", r.status_code == 201 and bool(r.json().get("upload_url")), str(r.status_code))

    # --- §4 logout ---
    # Access tokens are stateless 15-min JWTs by design; logout revokes the
    # SESSION, so the post-logout guarantee is that the refresh token dies.
    r = client.post(f"{BASE}/v1/auth/logout", headers=hb)
    check("logout B", r.status_code == 200)
    r = client.post(f"{BASE}/v1/auth/refresh", json={"refresh_token": tokens_b["refresh_token"]})
    check("B refresh token dead after logout (401)", r.status_code == 401, str(r.status_code))

    report()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    sub.add_parser("phase_a")
    b = sub.add_parser("phase_b")
    b.add_argument("--a-chal", required=True)
    b.add_argument("--a-code", required=True)
    b.add_argument("--b-chal", required=True)
    b.add_argument("--b-code", required=True)
    args = parser.parse_args()

    with httpx.Client(timeout=15.0) as client:
        if args.phase == "phase_a":
            phase_a(client)
        else:
            phase_b(client, args)


if __name__ == "__main__":
    main()
