"""HTTP sender — flush captured frames to the Watchpoint backend.

Called after flush_to_disk succeeds.  Sends:
  POST /api/v1/ingest/model-runs    (once per model run)
  POST /api/v1/ingest/inferences    (batch, one entry per captured frame)

All network errors are logged and re-raised — caller decides on retry policy.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


def send_model_run(
    backend_url: str,
    device_id: str,
    model_run_id: str,
    model_name: str,
    framework: str = "pytorch",
    metadata: dict[str, Any] | None = None,
    device_token: str | None = None,
) -> dict[str, Any]:
    """Register a model run with the backend.

    Returns the response JSON dict.
    """
    payload = {
        "id": model_run_id,
        "device_id": device_id,
        "model_name": model_name,
        "framework": framework,
        "metadata": metadata or {},
    }
    url = f"{backend_url.rstrip('/')}/api/v1/ingest/model-runs"
    with httpx.Client(timeout=10.0) as client:
        headers = {"X-Device-Token": device_token} if device_token else None
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def send_inferences(
    backend_url: str,
    frames: list[dict[str, Any]],
    incident_id: str | None = None,
    device_token: str | None = None,
) -> dict[str, Any]:
    """Batch-send captured inference frames to the backend.

    Args:
        backend_url: Base URL of the Watchpoint API.
        frames:      List of frame dicts from the ring buffer snapshot.
        incident_id: Optional incident UUID to attach to each inference.

    Returns:
        Response JSON dict.
    """
    if not frames:
        raise ValueError("No frames to send")

    inferences = []
    for frame in frames:
        entry: dict[str, Any] = {
            "inference_id": frame.get("inference_id"),
            "model_run_id": frame.get("model_run_id"),
            "device_id": frame.get("device_id"),
            "layer_name": frame.get("layer_name"),
            "timestamp_ns": frame.get("timestamp_ns"),
            "input_shapes": frame.get("input_shapes"),
            "output_shape": frame.get("output_shape"),
            "output_mean": frame.get("output_mean"),
            "output_std": frame.get("output_std"),
            "confidence": frame.get("confidence"),
            "input_hash": frame.get("input_hash"),
        }
        if incident_id:
            entry["incident_id"] = incident_id
        inferences.append(entry)

    url = f"{backend_url.rstrip('/')}/api/v1/ingest/inferences"
    with httpx.Client(timeout=30.0) as client:
        headers = {"X-Device-Token": device_token} if device_token else None
        resp = client.post(url, json={"inferences": inferences}, headers=headers)
        resp.raise_for_status()
        log.info("Sent %d inference frames to backend", len(inferences))
        return resp.json()
