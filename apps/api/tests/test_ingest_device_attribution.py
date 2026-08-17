"""Ingest attributes telemetry to the device that owns the token.

Agents cannot reliably know their own device UUID — the Go agent sent its
hostname and the model collector sent the literal string "unknown-device", both
of which the API rejected as malformed UUIDs. `device_id` is therefore optional
and derived from the credential, while a payload that *does* name a device is
still checked against it.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import OTHER_DEVICE_ID, STUB_DEVICE_ID

TS = "2026-08-06T00:00:00Z"


def _metric(**overrides) -> dict:
    payload = {"timestamp": TS, "metric_name": "cpu_percent", "value": 42.0, "unit": "%"}
    payload.update(overrides)
    return {"metrics": [payload]}


def _log(**overrides) -> dict:
    payload = {"timestamp": TS, "level": "info", "source": "agent", "message": "hello"}
    payload.update(overrides)
    return {"logs": [payload]}


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/ingest/metrics", _metric()),
        ("/api/v1/ingest/logs", _log()),
        ("/api/v1/ingest/events", {"events": [{"timestamp": TS, "source": "a", "message": "m"}]}),
    ],
)
def test_device_id_may_be_omitted(device_client, mock_db, path: str, body: dict) -> None:
    mock_db([])
    resp = device_client.post(path, json=body)
    assert resp.status_code == 200, resp.text


def test_omitted_device_id_is_filled_from_the_token(device_client, mock_db) -> None:
    """The row must be attributed to the token's device, not left null."""
    captured: list = []
    mock_db([], on_add_all=captured.extend)

    resp = device_client.post("/api/v1/ingest/metrics", json=_metric())

    assert resp.status_code == 200
    assert captured, "no rows were persisted"
    assert captured[0].device_id == STUB_DEVICE_ID


def test_explicit_matching_device_id_is_accepted(device_client, mock_db) -> None:
    mock_db([])
    resp = device_client.post("/api/v1/ingest/metrics", json=_metric(device_id=str(STUB_DEVICE_ID)))
    assert resp.status_code == 200


def test_explicit_foreign_device_id_is_still_rejected(device_client, mock_db) -> None:
    """Making device_id optional must not weaken cross-device protection."""
    mock_db([])
    resp = device_client.post(
        "/api/v1/ingest/metrics", json=_metric(device_id=str(OTHER_DEVICE_ID))
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Unknown fields
# ---------------------------------------------------------------------------


def test_unknown_metric_field_is_rejected(device_client, mock_db) -> None:
    """`labels` instead of `labels_json` used to be accepted and discarded.

    That silently stripped the label identifying which topic a rate belonged to.
    """
    mock_db([])
    resp = device_client.post(
        "/api/v1/ingest/metrics",
        json=_metric(labels={"topic": "/cmd_vel"}),
    )
    assert resp.status_code == 422
    assert "labels" in resp.text


def test_unknown_log_field_is_rejected(device_client, mock_db) -> None:
    mock_db([])
    resp = device_client.post("/api/v1/ingest/logs", json=_log(metadata={"a": 1}))
    assert resp.status_code == 422


def test_correct_field_names_are_accepted(device_client, mock_db) -> None:
    captured: list = []
    mock_db([], on_add_all=captured.extend)

    resp = device_client.post(
        "/api/v1/ingest/metrics",
        json=_metric(labels_json={"topic": "/cmd_vel"}),
    )

    assert resp.status_code == 200
    assert captured[0].labels_json == {"topic": "/cmd_vel"}


# ---------------------------------------------------------------------------
# AI layer
# ---------------------------------------------------------------------------


def test_model_run_device_id_may_be_omitted(device_client, mock_db) -> None:
    captured: list = []
    mock_db([], on_add=captured.append)

    resp = device_client.post(
        "/api/v1/ingest/model-runs",
        json={"model_name": "yolov8n", "framework": "pytorch"},
    )

    assert resp.status_code == 201, resp.text
    assert captured[0].device_id == STUB_DEVICE_ID


def test_inference_device_id_may_be_omitted(device_client, mock_db) -> None:
    captured: list = []
    mock_db([], on_add_all=captured.extend)

    resp = device_client.post(
        "/api/v1/ingest/inferences",
        json={
            "inferences": [
                {
                    "model_run_id": str(uuid.uuid4()),
                    "timestamp_ns": 1_700_000_000_000_000_000,
                    "confidence": 0.91,
                    "layer_name": "head",
                }
            ]
        },
    )

    assert resp.status_code == 201, resp.text
    assert captured[0].device_id == STUB_DEVICE_ID


def test_unknown_incident_id_is_404_not_500(device_client, mock_db) -> None:
    """A stale incident reference used to hit the FK and surface as a 500."""
    mock_db([])  # no incident rows match
    resp = device_client.post(
        "/api/v1/ingest/inferences",
        json={
            "inferences": [
                {
                    "model_run_id": str(uuid.uuid4()),
                    "incident_id": str(uuid.uuid4()),
                    "timestamp_ns": 1,
                }
            ]
        },
    )
    assert resp.status_code == 404
    assert "incident_id" in resp.text


def test_inference_rejects_undeclared_capture_fields(device_client, mock_db) -> None:
    """The collector captures more locally than the API stores.

    input_shapes/output_min/output_max live in the on-disk msgpack; the sender
    projects them out. Accepting them here would silently drop them instead.
    """
    mock_db([])
    resp = device_client.post(
        "/api/v1/ingest/inferences",
        json={
            "inferences": [
                {
                    "model_run_id": str(uuid.uuid4()),
                    "timestamp_ns": 1,
                    "input_shapes": [[1, 3, 224, 224]],
                }
            ]
        },
    )
    assert resp.status_code == 422
