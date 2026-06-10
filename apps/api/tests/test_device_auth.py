"""Tests for device-scoped API token auth."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.database import get_db
from app.device_tokens import hash_device_token
from app.main import app
from app.models.device import Device, DeviceStatus


def _make_device(token: str = "test-token") -> Device:
    return Device(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        device_name="robot-01",
        api_token_hash=hash_device_token(token),
        status=DeviceStatus.online,
        registered_at=datetime.now(timezone.utc),
    )


def _db_override(device: Device | None):
    async def override():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = device
        db.execute = AsyncMock(return_value=result)
        db.add = MagicMock()
        db.add_all = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    return override


def test_register_device_returns_token(monkeypatch) -> None:
    captured = {}

    async def override():
        db = AsyncMock()

        def add(obj):
            captured["device"] = obj

        db.add = add
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    monkeypatch.setattr("app.routers.devices.generate_device_token", lambda: "device-token-123")
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    resp = client.post(
        "/api/v1/devices/register",
        json={
            "project_id": str(uuid.uuid4()),
            "device_name": "robot-01",
            "hardware_model": "Jetson",
            "os_version": "Ubuntu",
            "agent_version": "1.0.0",
        },
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["device_token"] == "device-token-123"
    assert captured["device"].api_token_hash == hash_device_token("device-token-123")


def test_metrics_ingest_requires_device_token() -> None:
    app.dependency_overrides[get_db] = _db_override(_make_device())
    client = TestClient(app)
    resp = client.post(
        "/api/v1/ingest/metrics",
        json={
            "metrics": [
                {
                    "device_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metric_name": "cpu_percent",
                    "value": 88.0,
                }
            ]
        },
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 401


def test_metrics_ingest_accepts_valid_token() -> None:
    token = "device-token-xyz"
    device = _make_device(token=token)
    app.dependency_overrides[get_db] = _db_override(device)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/ingest/metrics",
        headers={"X-Device-Token": token},
        json={
            "metrics": [
                {
                    "device_id": str(device.id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metric_name": "cpu_percent",
                    "value": 88.0,
                }
            ]
        },
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1


def test_model_run_ingest_requires_device_token() -> None:
    app.dependency_overrides[get_db] = _db_override(_make_device())
    client = TestClient(app)
    resp = client.post(
        "/api/v1/ingest/model-runs",
        json={
            "device_id": str(uuid.uuid4()),
            "model_name": "resnet18",
            "framework": "pytorch",
        },
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
