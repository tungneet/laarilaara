"""Tests for the health slice."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_returns_ok():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert "X-Request-Id" in resp.headers


def test_ready_returns_ready_when_checks_skipped():
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert any(c["name"] == "dynamodb" for c in body["checks"])
    assert body["checks"][0]["status"] == "skipped"


def test_request_id_is_echoed_when_valid():
    resp = client.get("/health/live", headers={"X-Request-Id": "abc-123"})
    assert resp.headers["X-Request-Id"] == "abc-123"


def test_unsafe_request_id_is_replaced():
    resp = client.get("/health/live", headers={"X-Request-Id": "bad id with spaces!"})
    assert resp.headers["X-Request-Id"] != "bad id with spaces!"


def test_unknown_route_returns_problem_json():
    resp = client.get("/health/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert body["status"] == 404
    assert body["code"] == "NOT_FOUND"
    assert "requestId" in body
