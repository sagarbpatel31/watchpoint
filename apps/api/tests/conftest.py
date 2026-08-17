"""Shared test fixtures.

The suite mocks the DB session via FastAPI dependency overrides rather than
running a live Postgres, so tests stay fast and hermetic. Auth dependencies are
overridden the same way — each test states which identity it runs as.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.security import require_current_user, require_device_token

STUB_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
STUB_DEVICE_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_DEVICE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def make_db_override(
    rows: list | None = None,
    on_add=None,
    on_add_all=None,
):
    """Build a get_db override yielding a mock session that returns `rows`.

    `on_add` / `on_add_all` receive the ORM objects the route persisted, so a
    test can assert on what was actually written rather than only on the status
    code — which is how the device attribution is checked.
    """
    rows = rows if rows is not None else []

    async def override():
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = rows
        result.scalar_one_or_none.return_value = rows[0] if rows else None
        result.scalar.return_value = len(rows)
        result.__iter__ = lambda self: iter(rows)
        db.execute = AsyncMock(return_value=result)
        # add/add_all are synchronous on a real AsyncSession; leaving them as
        # AsyncMock returns un-awaited coroutines and emits RuntimeWarnings.
        db.add = MagicMock(side_effect=on_add)
        db.add_all = MagicMock(side_effect=on_add_all)

        async def refresh(obj, *_args, **_kwargs):
            # Postgres fills these from server defaults on flush; without a real
            # session they stay None and response validation fails on fields the
            # route never sets itself.
            now = datetime.now(timezone.utc)
            for attr in ("created_at", "updated_at"):
                if getattr(obj, attr, None) is None:
                    setattr(obj, attr, now)

        db.refresh = AsyncMock(side_effect=refresh)
        yield db

    return override


def stub_user() -> MagicMock:
    user = MagicMock()
    user.id = STUB_USER_ID
    user.email = "demo@watchpoint.ai"
    user.name = "Demo User"
    user.is_active = True
    return user


def stub_device(device_id: uuid.UUID = STUB_DEVICE_ID) -> MagicMock:
    device = MagicMock()
    device.id = device_id
    device.device_name = "amr-07"
    return device


@pytest.fixture
def mock_db():
    """Callable that installs a get_db override returning the given rows.

    Pass `on_add` / `on_add_all` to capture what the route persisted.
    """

    def _install(rows: list | None = None, on_add=None, on_add_all=None) -> None:
        app.dependency_overrides[get_db] = make_db_override(rows, on_add, on_add_all)

    yield _install
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client() -> Iterator[TestClient]:
    """Client authenticated as a dashboard user (JWT identity)."""
    app.dependency_overrides[require_current_user] = stub_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def device_client() -> Iterator[TestClient]:
    """Client authenticated as an embedded agent holding a device token."""
    app.dependency_overrides[require_device_token] = lambda: stub_device()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client() -> Iterator[TestClient]:
    """Client with no credentials — used to assert routes are protected."""
    app.dependency_overrides.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
