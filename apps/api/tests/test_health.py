"""Tests for the health endpoint and app startup."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _make_client() -> TestClient:
    # Import here to avoid top-level side effects during collection.
    from app.main import app

    return TestClient(app, raise_server_exceptions=True)


def test_health_returns_ok() -> None:
    client = _make_client()
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "watchpoint-api"
    assert "version" in body


def test_health_method_not_allowed() -> None:
    client = _make_client()
    resp = client.post("/api/v1/health")
    assert resp.status_code == 405
