"""POST /seed/demo is gated on enable_demo_seed.

The endpoint writes fixed-ID demo rows with no authentication, so on a public
deployment it is both a data-integrity risk (anyone can reset the demo) and,
before it was made idempotent, a way to trigger duplicate-key errors against a
live database. Default is off; docker-compose turns it on for local dev.
"""

from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture
def seed_disabled():
    original = settings.enable_demo_seed
    settings.enable_demo_seed = False
    yield
    settings.enable_demo_seed = original


@pytest.fixture
def seed_enabled():
    original = settings.enable_demo_seed
    settings.enable_demo_seed = True
    yield
    settings.enable_demo_seed = original


def test_seed_returns_404_when_disabled(anon_client, seed_disabled) -> None:
    resp = anon_client.post("/api/v1/seed/demo")
    assert resp.status_code == 404


def test_seed_does_not_advertise_itself_when_disabled(anon_client, seed_disabled) -> None:
    """404 rather than 403 — a 403 would confirm the endpoint exists."""
    resp = anon_client.post("/api/v1/seed/demo")
    assert resp.json()["detail"] == "Not Found"


def test_seed_defaults_to_disabled() -> None:
    """An unconfigured deployment must not be seedable."""
    from app.config import Settings

    assert Settings().enable_demo_seed is False


def test_seed_is_reachable_when_enabled(anon_client, mock_db, seed_enabled) -> None:
    """With the flag on the route runs; it no longer 404s at the gate."""
    mock_db([])
    resp = anon_client.post("/api/v1/seed/demo")
    assert resp.status_code != 404
