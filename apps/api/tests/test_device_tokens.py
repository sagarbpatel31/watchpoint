"""Device token minting, scoping, and revocation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.database import get_db
from app.main import app
from app.security import (
    DEVICE_TOKEN_SCHEME,
    assert_device_matches,
    generate_device_token,
    hash_device_token,
    require_device_token,
)
from tests.conftest import OTHER_DEVICE_ID, STUB_DEVICE_ID, stub_device

# ---------------------------------------------------------------------------
# Token generation and hashing
# ---------------------------------------------------------------------------


def test_generated_token_has_expected_shape() -> None:
    raw, prefix, token_hash = generate_device_token()
    scheme, embedded_prefix, secret = raw.split("_", 2)

    assert scheme == DEVICE_TOKEN_SCHEME
    assert embedded_prefix == prefix
    assert len(secret) >= 32
    assert token_hash == hash_device_token(raw)
    assert len(token_hash) == 64  # sha256 hex


def test_generated_tokens_are_unique() -> None:
    tokens = {generate_device_token()[0] for _ in range(200)}
    assert len(tokens) == 200


def test_hash_is_deterministic_and_not_the_raw_token() -> None:
    raw, _, token_hash = generate_device_token()
    assert hash_device_token(raw) == token_hash
    assert raw not in token_hash


# ---------------------------------------------------------------------------
# Scoping — a token may only write for the device it was issued to
# ---------------------------------------------------------------------------


def test_assert_device_matches_allows_own_device() -> None:
    assert_device_matches(stub_device(), STUB_DEVICE_ID)  # no raise


def test_assert_device_matches_allows_absent_device_id() -> None:
    assert_device_matches(stub_device(), None)  # no raise


def test_assert_device_matches_rejects_other_device() -> None:
    with pytest.raises(HTTPException) as exc:
        assert_device_matches(stub_device(), OTHER_DEVICE_ID)
    assert exc.value.status_code == 403


def test_ingest_rejects_payload_for_another_device(device_client, mock_db) -> None:
    """The concrete attack: a valid token for robot A writing as robot B."""
    mock_db([])
    resp = device_client.post(
        "/api/v1/ingest/metrics",
        json={
            "metrics": [
                {
                    "device_id": str(OTHER_DEVICE_ID),
                    "timestamp": "2026-08-06T00:00:00Z",
                    "metric_name": "cpu_percent",
                    "value": 42.0,
                }
            ]
        },
    )
    assert resp.status_code == 403


def test_ingest_accepts_payload_for_own_device(device_client, mock_db) -> None:
    mock_db([])
    resp = device_client.post(
        "/api/v1/ingest/metrics",
        json={
            "metrics": [
                {
                    "device_id": str(STUB_DEVICE_ID),
                    "timestamp": "2026-08-06T00:00:00Z",
                    "metric_name": "cpu_percent",
                    "value": 42.0,
                }
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ingested": 1}


# ---------------------------------------------------------------------------
# require_device_token
# ---------------------------------------------------------------------------


def _token_row(*, revoked: bool = False) -> MagicMock:
    row = MagicMock()
    row.device_id = STUB_DEVICE_ID
    row.revoked_at = datetime.now(timezone.utc) if revoked else None
    return row


def _db_for(token_row, device_row) -> AsyncMock:
    """Mock session returning the token on first execute, device on second."""
    db = AsyncMock()
    results = []
    for row in (token_row, device_row):
        res = MagicMock()
        res.scalar_one_or_none.return_value = row
        results.append(res)
    db.execute = AsyncMock(side_effect=results)
    return db


async def test_require_device_token_accepts_active_token() -> None:
    device = await require_device_token(
        x_device_token="wp_abcd1234_secret",
        db=_db_for(_token_row(), stub_device()),
    )
    assert device.id == STUB_DEVICE_ID


async def test_require_device_token_rejects_revoked_token() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_device_token(
            x_device_token="wp_abcd1234_secret",
            db=_db_for(_token_row(revoked=True), stub_device()),
        )
    assert exc.value.status_code == 401


async def test_require_device_token_rejects_unknown_token() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_device_token(
            x_device_token="wp_abcd1234_secret",
            db=_db_for(None, None),
        )
    assert exc.value.status_code == 401


async def test_require_device_token_rejects_missing_header() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_device_token(x_device_token=None, db=AsyncMock())
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Token management endpoints
# ---------------------------------------------------------------------------


def test_create_token_returns_plaintext_once(auth_client) -> None:
    now = datetime.now(timezone.utc)
    device = stub_device()

    async def override():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = device
        db.execute = AsyncMock(return_value=result)
        db.add = MagicMock()

        async def refresh(obj):
            # Mimic the server defaults populated on flush.
            obj.id = uuid.uuid4()
            obj.created_at = now
            obj.updated_at = now
            obj.last_used_at = None
            obj.revoked_at = None

        db.refresh = AsyncMock(side_effect=refresh)
        yield db

    app.dependency_overrides[get_db] = override
    resp = auth_client.post(
        f"/api/v1/devices/{STUB_DEVICE_ID}/tokens",
        json={"name": "amr-07 model collector"},
    )
    app.dependency_overrides.pop(get_db)

    assert resp.status_code == 201
    body = resp.json()
    assert body["token_once"].startswith(f"{DEVICE_TOKEN_SCHEME}_")
    assert body["token_prefix"] in body["token_once"]
    assert body["name"] == "amr-07 model collector"
    # The stored hash must never be serialised.
    assert "token_hash" not in body


def test_list_tokens_never_exposes_secret(auth_client, mock_db) -> None:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.device_id = STUB_DEVICE_ID
    row.name = "amr-07"
    row.token_prefix = "abcd1234"
    row.token_hash = "should-never-appear"
    row.last_used_at = None
    row.revoked_at = None
    row.created_at = datetime.now(timezone.utc)

    mock_db([row])
    resp = auth_client.get(f"/api/v1/devices/{STUB_DEVICE_ID}/tokens")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload[0]["token_prefix"] == "abcd1234"
    assert "should-never-appear" not in resp.text
    assert "token_hash" not in payload[0]
    assert "token_once" not in payload[0]
