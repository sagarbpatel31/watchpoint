"""HTTP sender — flush captured frames to the Watchpoint backend.

Called after flush_to_disk succeeds.  Sends:
  POST /api/v1/ingest/model-runs    (once per model run)
  POST /api/v1/ingest/inferences    (batch, one entry per captured frame)

Both endpoints require a device token in the X-Device-Token header. The device a
batch belongs to is resolved server-side from that token, so no device_id is
sent — an agent never has to know its own UUID.

All network errors are logged and re-raised — caller decides on retry policy.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Fields the ingest API declares for an inference frame. Captured frames carry
# more than this (input_shapes, output_min/max, ...) which is kept in the local
# msgpack capture; the API rejects unknown fields, so the payload is projected
# down to exactly what it accepts rather than relying on it to ignore extras.
_INFERENCE_FIELDS = (
    "inference_id",
    "model_run_id",
    "incident_id",
    "timestamp_ns",
    "input_hash",
    "input_ref",
    "outputs",
    "confidence",
    "latency_ms",
    "gpu_mem_mb",
    "layer_name",
    "output_mean",
    "output_std",
)


def _auth_headers(token: str | None) -> dict[str, str]:
    return {"X-Device-Token": token} if token else {}


def send_model_run(
    backend_url: str,
    model_run_id: str,
    model_name: str,
    framework: str = "pytorch",
    metadata: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Register a model run with the backend.

    Returns the response JSON dict.
    """
    payload = {
        "id": model_run_id,
        "model_name": model_name,
        "framework": framework,
        "metadata": metadata or {},
    }
    url = f"{backend_url.rstrip('/')}/api/v1/ingest/model-runs"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, json=payload, headers=_auth_headers(token))
        resp.raise_for_status()
        return resp.json()


def send_inferences(
    backend_url: str,
    frames: list[dict[str, Any]],
    incident_id: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Batch-send captured inference frames to the backend.

    Args:
        backend_url: Base URL of the Watchpoint API.
        frames:      List of frame dicts from the ring buffer snapshot.
        incident_id: Optional incident UUID to attach to each inference.
        token:       Device token for the X-Device-Token header.

    Returns:
        Response JSON dict.
    """
    if not frames:
        raise ValueError("No frames to send")

    inferences = []
    for frame in frames:
        entry = {k: frame[k] for k in _INFERENCE_FIELDS if k in frame}
        if incident_id:
            entry["incident_id"] = incident_id
        inferences.append(entry)

    url = f"{backend_url.rstrip('/')}/api/v1/ingest/inferences"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json={"inferences": inferences}, headers=_auth_headers(token))
        resp.raise_for_status()
        log.info("Sent %d inference frames to backend", len(inferences))
        return resp.json()
