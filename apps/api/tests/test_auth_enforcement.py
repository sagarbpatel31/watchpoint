"""Every non-public route must reject unauthenticated callers.

This is the regression guard for the state this API shipped in previously: JWT
login existed and issued valid tokens, but `GET /auth/me` was the only route
that consumed one. Everything else — incidents, devices, projects, ingest,
replay bundles, seed — served anonymous requests.

`test_no_unlisted_routes` is the part that matters long term: adding a route
without classifying it here fails the suite, so a new router cannot be merged
unprotected by omission.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.routing import APIRoute

from app.main import app

_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01")

# (method, path) that must answer 401 without credentials.
USER_PROTECTED: list[tuple[str, str]] = [
    ("GET", "/api/v1/incidents/"),
    ("POST", "/api/v1/incidents/"),
    ("GET", f"/api/v1/incidents/{_ID}"),
    ("GET", f"/api/v1/incidents/{_ID}/events"),
    ("GET", f"/api/v1/incidents/{_ID}/metrics"),
    ("GET", f"/api/v1/incidents/{_ID}/inferences"),
    ("POST", f"/api/v1/incidents/{_ID}/analyze"),
    ("POST", f"/api/v1/incidents/{_ID}/replay-bundle"),
    ("GET", "/api/v1/devices/"),
    ("POST", "/api/v1/devices/register"),
    ("GET", f"/api/v1/devices/{_ID}"),
    ("POST", f"/api/v1/devices/heartbeat/{_ID}"),
    ("POST", "/api/v1/devices/deployments"),
    ("POST", f"/api/v1/devices/{_ID}/tokens"),
    ("GET", f"/api/v1/devices/{_ID}/tokens"),
    ("POST", f"/api/v1/devices/tokens/{_ID}/revoke"),
    ("GET", f"/api/v1/projects/{_ID}"),
    ("GET", f"/api/v1/projects/{_ID}/summary"),
    ("GET", f"/api/v1/inferences/{_ID}"),
    ("GET", f"/api/v1/inferences/{_ID}/attention"),
    ("GET", f"/api/v1/bundles/{_ID}"),
]

DEVICE_PROTECTED: list[tuple[str, str]] = [
    ("POST", "/api/v1/ingest/logs"),
    ("POST", "/api/v1/ingest/metrics"),
    ("POST", "/api/v1/ingest/events"),
    ("POST", "/api/v1/ingest/model-runs"),
    ("POST", "/api/v1/ingest/inferences"),
    ("POST", "/api/v1/ingest/decisions"),
]

# Deliberately reachable without credentials.
PUBLIC: set[tuple[str, str]] = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/auth/me"),  # enforces auth itself, returns 401 too
    ("POST", "/api/v1/seed/demo"),  # gated by enable_demo_seed, not by identity
}


@pytest.mark.parametrize(("method", "path"), USER_PROTECTED)
def test_user_routes_reject_anonymous(anon_client, method: str, path: str) -> None:
    resp = anon_client.request(method, path, json={})
    assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


@pytest.mark.parametrize(("method", "path"), DEVICE_PROTECTED)
def test_ingest_routes_reject_missing_device_token(anon_client, method: str, path: str) -> None:
    resp = anon_client.request(method, path, json={})
    assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


def test_ingest_routes_reject_unknown_device_token(anon_client, mock_db) -> None:
    """A well-formed but unrecognised token is rejected, not merely absent ones."""
    mock_db([])  # no DeviceToken row matches the hash
    resp = anon_client.post(
        "/api/v1/ingest/metrics",
        json={"metrics": []},
        headers={"X-Device-Token": "wp_deadbeef_not-a-real-token"},
    )
    assert resp.status_code == 401


def test_no_unlisted_routes() -> None:
    """Every API route is classified as public, user-protected, or device-protected.

    Fails when a route is added without a deliberate decision about its auth.
    """
    classified = {(m, p) for m, p in USER_PROTECTED + DEVICE_PROTECTED} | PUBLIC
    classified_paths = {p for _, p in classified}

    unlisted: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            # Compare on the templated path with params substituted by _ID.
            concrete = route.path
            for param in route.param_convertors:
                concrete = concrete.replace(f"{{{param}}}", str(_ID))
            if (method, concrete) not in classified and concrete not in classified_paths:
                unlisted.append(f"{method} {route.path}")

    assert not unlisted, (
        "Routes not classified in test_auth_enforcement.py — decide whether each "
        f"needs auth and add it to the right list: {sorted(unlisted)}"
    )
