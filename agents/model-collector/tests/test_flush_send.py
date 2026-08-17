"""Collector.flush() writes to disk and then uploads.

Before this, flush() only wrote msgpack — send_model_run and send_inferences had
no callers at all, so nothing the collector captured ever reached the backend.

Two properties matter beyond "it posts":

  * disk first, network second — a backend that is unreachable during an
    incident is exactly when the local capture matters most;
  * upload failure is never fatal — this runs inside the inference process, and
    losing telemetry must not take down a robot's perception stack.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from model_collector import Collector

TOKEN = "wp_abcd1234_secret"
BACKEND = "http://backend:8000"


def _collector(tmp_path, **kwargs) -> Collector:
    opts = {"backend_url": BACKEND, "device_token": TOKEN, "flush_path": str(tmp_path)}
    opts.update(kwargs)
    return Collector(**opts)


def _record_frames(collector: Collector, n: int = 3) -> None:
    for i in range(n):
        collector.record(
            {
                "inference_id": f"00000000-0000-0000-0000-00000000000{i}",
                "layer_name": "head",
                "timestamp_ns": 1_700_000_000_000_000_000 + i,
                "confidence": 0.9,
                "output_mean": 0.1,
                "output_std": 0.05,
                # Captured locally but not accepted by the API.
                "input_shapes": [[1, 3, 224, 224]],
                "output_min": -1.0,
            }
        )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_flush_writes_then_uploads(tmp_path) -> None:
    collector = _collector(tmp_path)
    _record_frames(collector)

    with (
        patch("model_collector.send_model_run") as run,
        patch("model_collector.send_inferences") as inf,
    ):
        path = collector.flush(incident_id="inc-1", model_name="yolov8n")

    assert path.endswith(".msgpack")
    run.assert_called_once()
    inf.assert_called_once()
    # The run must exist before frames can reference it.
    assert run.call_args.kwargs["token"] == TOKEN
    assert inf.call_args.kwargs["token"] == TOKEN
    assert inf.call_args.kwargs["incident_id"] == "inc-1"
    assert len(inf.call_args.kwargs["frames"]) == 3


def test_flush_clears_the_buffer(tmp_path) -> None:
    collector = _collector(tmp_path)
    _record_frames(collector)

    with patch("model_collector.send_model_run"), patch("model_collector.send_inferences"):
        collector.flush()

    assert collector.buffer_len == 0


def test_auto_generated_capture_id_is_not_sent_as_an_incident(tmp_path) -> None:
    """flush() invents an id to name the local directory. That id must not be
    sent as incident_id, which is a foreign key — doing so made the API 500 on
    an FK violation for every capture not tied to a known incident.
    """
    collector = _collector(tmp_path)
    _record_frames(collector)

    with (
        patch("model_collector.send_model_run"),
        patch("model_collector.send_inferences") as inf,
    ):
        path = collector.flush()  # no incident_id given

    assert inf.call_args.kwargs["incident_id"] is None
    # The local capture is still named and written.
    assert path.endswith(".msgpack")


def test_explicit_incident_id_is_forwarded(tmp_path) -> None:
    collector = _collector(tmp_path)
    _record_frames(collector)

    with (
        patch("model_collector.send_model_run"),
        patch("model_collector.send_inferences") as inf,
    ):
        collector.flush(incident_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01")

    assert inf.call_args.kwargs["incident_id"] == "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01"


def test_send_can_be_disabled(tmp_path) -> None:
    collector = _collector(tmp_path)
    _record_frames(collector)

    with patch("model_collector.send_model_run") as run:
        collector.flush(send=False)

    run.assert_not_called()


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_upload_failure_does_not_raise(tmp_path) -> None:
    """A network error must not propagate into the inference thread."""
    collector = _collector(tmp_path)
    _record_frames(collector)

    with (
        patch("model_collector.send_model_run", side_effect=httpx.ConnectError("refused")),
        patch("model_collector.send_inferences"),
    ):
        path = collector.flush(incident_id="inc-2")

    assert path, "the on-disk capture path is still returned"


def test_capture_survives_upload_failure(tmp_path) -> None:
    """Disk write happens before the upload is attempted."""
    collector = _collector(tmp_path)
    _record_frames(collector)

    with (
        patch("model_collector.send_model_run", side_effect=httpx.ConnectError("refused")),
        patch("model_collector.send_inferences"),
    ):
        path = collector.flush(incident_id="inc-3")

    import os

    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_missing_token_skips_upload(tmp_path) -> None:
    """Local-only use keeps working without a credential."""
    collector = _collector(tmp_path, device_token="")
    _record_frames(collector)

    with patch("model_collector.send_model_run") as run:
        path = collector.flush()

    run.assert_not_called()
    assert path


def test_empty_buffer_still_raises(tmp_path) -> None:
    collector = _collector(tmp_path)
    with pytest.raises(RuntimeError, match="empty"):
        collector.flush()


# ---------------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------------


def test_sender_omits_device_id_and_undeclared_fields() -> None:
    """The API rejects unknown fields, so the payload is projected down."""
    from model_collector.sender import send_inferences

    captured: dict = {}

    class _Resp:
        status_code = 201

        def raise_for_status(self) -> None: ...

        def json(self) -> dict:
            return {"created": 1}

    client = MagicMock()
    client.__enter__ = lambda self: self
    client.__exit__ = lambda self, *a: False

    def post(url, json=None, headers=None):
        captured["json"] = json
        captured["headers"] = headers
        return _Resp()

    client.post = post

    with patch("httpx.Client", return_value=client):
        send_inferences(
            BACKEND,
            [
                {
                    "inference_id": "i-1",
                    "model_run_id": "m-1",
                    "device_id": "unknown-device",
                    "timestamp_ns": 1,
                    "confidence": 0.5,
                    "input_shapes": [[1, 3, 224, 224]],
                    "output_min": -1.0,
                }
            ],
            token=TOKEN,
        )

    entry = captured["json"]["inferences"][0]
    assert "device_id" not in entry, "device is resolved from the token"
    assert "input_shapes" not in entry
    assert "output_min" not in entry
    assert entry["confidence"] == 0.5
    assert captured["headers"]["X-Device-Token"] == TOKEN
