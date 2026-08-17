"""Watchpoint model-collector — transparent AI inference capture.

Quick start (PyTorch):

    from model_collector import Collector
    from model_collector.adapters.pytorch_adapter import attach_hooks

    collector = Collector(
        backend_url="http://localhost:8000",
        device_token="wp_...",     # or set WP_DEVICE_TOKEN
    )
    attach_hooks(model, collector, layer_names=["backbone.layer4", "head"])
    output = model(input_tensor)   # capture is transparent
    collector.flush(incident_id="some-uuid")   # writes to disk, then uploads

The device a capture belongs to is resolved from the token server-side, so no
device UUID is configured here.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from model_collector.config import CollectorConfig
from model_collector.ring_buffer import RingBuffer
from model_collector.sender import send_inferences, send_model_run
from model_collector.writer import flush_to_disk

log = logging.getLogger(__name__)

__all__ = ["Collector"]


class Collector:
    """Central coordinator: holds the ring buffer, exposes flush interface.

    One Collector instance per model process.  Multiple adapters can write
    to the same Collector (e.g. a PyTorch adapter + an OOD detector).
    """

    def __init__(
        self,
        device_id: str | None = None,
        backend_url: str | None = None,
        capture_layers: list[str] | None = None,
        ring_buffer_size: int | None = None,
        flush_path: str | None = None,
        device_token: str | None = None,
    ) -> None:
        cfg = CollectorConfig()
        # Local label only — the backend resolves the real device from the token.
        self.device_id = device_id or cfg.device_id
        self.backend_url = backend_url or cfg.backend_url
        self.device_token = device_token or cfg.device_token
        self.capture_layers = capture_layers or cfg.capture_layers
        self.flush_path = flush_path or cfg.flush_path
        self._buf = RingBuffer(maxsize=ring_buffer_size or cfg.ring_buffer_size)
        self._model_run_id: str = str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Write path (called by adapters from forward hooks)
    # ------------------------------------------------------------------

    def record(self, frame: dict[str, Any]) -> None:
        """Store one inference frame in the ring buffer.

        Called by adapters; must be fast — runs on the inference thread.
        """
        frame.setdefault("model_run_id", self._model_run_id)
        frame.setdefault("device_id", self.device_id)
        self._buf.append(frame)

    # ------------------------------------------------------------------
    # Flush path (called on incident trigger)
    # ------------------------------------------------------------------

    def flush(
        self,
        incident_id: str | None = None,
        send: bool = True,
        model_name: str = "unknown",
    ) -> str:
        """Snapshot the ring buffer, write to disk, transmit, clear buffer.

        Disk first, network second, deliberately: a backend that is unreachable
        when a robot hits an incident is exactly when the capture matters most,
        so the local msgpack must already be durable before the upload is
        attempted.

        Transmission failures are logged and swallowed. This runs in the
        inference process; losing telemetry is a bad outcome, but taking down
        the robot's perception stack to report it is a worse one.

        Args:
            incident_id: UUID of a known incident to attach the frames to. When
                         omitted the capture uploads unattached — a locally
                         invented id would fail the incident foreign key.
            send:        Upload after writing.  Skipped with a warning when no
                         backend_url or device_token is configured.
            model_name:  Recorded on the model run.

        Returns:
            Path to the written msgpack file.
        """
        # Two different identifiers, deliberately not shared: `capture_id` names
        # the local directory and can be invented, while `incident_id` is a
        # foreign key into the incidents table. Sending an invented one is an FK
        # violation, so a capture with no known incident uploads unattached.
        capture_id = incident_id or str(uuid.uuid4())
        frames = self._buf.snapshot()
        if not frames:
            raise RuntimeError("Ring buffer is empty — nothing to flush")
        path = flush_to_disk(frames, self.flush_path, capture_id)
        self._buf.clear()

        if send:
            self._send(frames, incident_id, model_name)

        return path

    def _send(self, frames: list[dict[str, Any]], incident_id: str | None, model_name: str) -> None:
        """Upload a flushed batch. Never raises — see flush()."""
        if not self.backend_url or not self.device_token:
            log.warning(
                "Capture written to disk but not uploaded: %s not configured. "
                "Set WP_BACKEND_URL and WP_DEVICE_TOKEN to enable transmission.",
                "backend_url" if not self.backend_url else "device_token",
            )
            return

        try:
            # The run must exist before inferences can reference it.
            send_model_run(
                backend_url=self.backend_url,
                model_run_id=self._model_run_id,
                model_name=model_name,
                token=self.device_token,
            )
            send_inferences(
                backend_url=self.backend_url,
                frames=frames,
                incident_id=incident_id,
                token=self.device_token,
            )
        except Exception:
            log.exception(
                "Failed to upload %d frames for incident %s — capture is on disk at %s",
                len(frames),
                incident_id,
                self.flush_path,
            )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def buffer_len(self) -> int:
        return len(self._buf)

    def reset_model_run(self) -> str:
        """Start a new model run (new weights loaded, etc.)."""
        self._model_run_id = str(uuid.uuid4())
        return self._model_run_id
