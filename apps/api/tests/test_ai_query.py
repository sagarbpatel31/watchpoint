"""Tests for AI layer query endpoints (GET side).

Uses FastAPI dependency override to inject a mock AsyncSession, avoiding
a live database connection. All tests are synchronous (TestClient).

These routes sit behind `require_current_user`, so they run through the
`auth_client` fixture rather than a bare TestClient.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import get_db
from app.main import app
from tests.conftest import make_db_override

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INCIDENT_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01")
INFERENCE_ID = uuid.uuid4()


def _make_inference(
    *,
    id: uuid.UUID = INFERENCE_ID,
    incident_id: uuid.UUID = INCIDENT_ID,
    model_run_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    timestamp_ns: int = 1_000_000_000,
    confidence: float | None = 0.87,
    latency_ms: float | None = 12.5,
    layer_name: str | None = "fc",
    output_mean: float | None = 0.1,
    output_std: float | None = 0.05,
    attention_ref: str | None = None,
) -> MagicMock:
    """Build a mock Inference ORM object."""
    inf = MagicMock()
    inf.id = id
    inf.model_run_id = model_run_id or uuid.uuid4()
    inf.device_id = device_id or uuid.uuid4()
    inf.incident_id = incident_id
    inf.timestamp_ns = timestamp_ns
    inf.confidence = confidence
    inf.latency_ms = latency_ms
    inf.layer_name = layer_name
    inf.output_mean = output_mean
    inf.output_std = output_std
    inf.attention_ref = attention_ref
    return inf


def _db_returning(rows: list) -> callable:
    """Return a get_db override that yields a mock returning `rows` once."""
    return make_db_override(rows)


# ---------------------------------------------------------------------------
# GET /incidents/{id}/inferences
# ---------------------------------------------------------------------------


def test_list_incident_inferences_empty(auth_client):
    app.dependency_overrides[get_db] = _db_returning([])
    resp = auth_client.get(f"/api/v1/incidents/{INCIDENT_ID}/inferences")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["inferences"] == []
    assert body["total"] == 0


def test_list_incident_inferences_returns_rows(auth_client):
    inf1 = _make_inference(timestamp_ns=1_000)
    inf2 = _make_inference(id=uuid.uuid4(), timestamp_ns=2_000)
    app.dependency_overrides[get_db] = _db_returning([inf1, inf2])
    resp = auth_client.get(f"/api/v1/incidents/{INCIDENT_ID}/inferences")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["inferences"]) == 2
    assert body["inferences"][0]["confidence"] == pytest.approx(0.87)
    assert body["inferences"][0]["layer_name"] == "fc"


# ---------------------------------------------------------------------------
# GET /inferences/{id}
# ---------------------------------------------------------------------------


def test_get_inference_not_found(auth_client):
    app.dependency_overrides[get_db] = _db_returning([])
    resp = auth_client.get(f"/api/v1/inferences/{uuid.uuid4()}")
    app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Inference not found"


def test_get_inference_success(auth_client):
    inf = _make_inference()
    app.dependency_overrides[get_db] = _db_returning([inf])
    resp = auth_client.get(f"/api/v1/inferences/{INFERENCE_ID}")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(INFERENCE_ID)
    assert body["latency_ms"] == pytest.approx(12.5)
    assert body["output_mean"] == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# GET /inferences/{id}/attention
# ---------------------------------------------------------------------------


def test_get_attention_not_found(auth_client):
    app.dependency_overrides[get_db] = _db_returning([])
    resp = auth_client.get(f"/api/v1/inferences/{uuid.uuid4()}/attention")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_get_attention_unavailable(auth_client):
    """No Grad-CAM computed yet → status unavailable."""
    inf = _make_inference(attention_ref=None)
    app.dependency_overrides[get_db] = _db_returning([inf])
    resp = auth_client.get(f"/api/v1/inferences/{INFERENCE_ID}/attention")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unavailable"
    assert body["attention_ref"] is None


def test_get_attention_available(auth_client):
    """attention_ref set → status available."""
    s3_key = "watchpoint/inferences/abc123/gradcam.npy"
    inf = _make_inference(attention_ref=s3_key)
    app.dependency_overrides[get_db] = _db_returning([inf])
    resp = auth_client.get(f"/api/v1/inferences/{INFERENCE_ID}/attention")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "available"
    assert body["attention_ref"] == s3_key
    assert body["layer_name"] == "fc"
