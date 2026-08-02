"""Tests for the public/reference/platform endpoints (catalog §3)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_context():
    resp = client.get("/v1/context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["experience"] == "laarilaara"
    assert body["service_name"]
    assert body["api_version"]


def test_list_countries():
    resp = client.get("/v1/reference/countries")
    assert resp.status_code == 200
    codes = {c["code"] for c in resp.json()}
    assert "IN" in codes
    assert "CA" in codes


def test_list_regions_for_known_country():
    resp = client.get("/v1/reference/regions", params={"countryCode": "IN"})
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert "Punjab" in names


def test_list_regions_for_unknown_country_is_empty():
    resp = client.get("/v1/reference/regions", params={"countryCode": "ZZ"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_regions_requires_country_code():
    resp = client.get("/v1/reference/regions")
    assert resp.status_code == 422


def test_list_languages():
    resp = client.get("/v1/reference/languages")
    assert resp.status_code == 200
    codes = {lang["code"] for lang in resp.json()}
    assert "pa" in codes
    assert "en" in codes


def test_list_communities():
    resp = client.get("/v1/reference/communities")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_religious_practices():
    resp = client.get("/v1/reference/religious-practices")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_education_levels():
    resp = client.get("/v1/reference/education-levels")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_occupation_categories():
    resp = client.get("/v1/reference/occupation-categories")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_interests():
    resp = client.get("/v1/reference/interests")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_plans():
    resp = client.get("/v1/plans")
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.json()}
    assert "free" in ids
    assert any(p["price_cents"] > 0 for p in resp.json())
