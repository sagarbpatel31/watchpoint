"""Configuration for the Watchpoint model collector."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class CollectorConfig:
    """All tunables for one model collector instance.

    Sensible defaults work out-of-the-box for local dev.
    Override via constructor args or environment variables.
    """

    # Identity
    #
    # A local label only — used in logs and the on-disk capture. It is never
    # sent to the backend: the device a batch belongs to is resolved server-side
    # from the token, so an agent does not need to know its own UUID.
    device_id: str = field(default_factory=lambda: os.environ.get("WP_DEVICE_ID", "unknown-device"))

    # Backend
    backend_url: str = field(
        default_factory=lambda: os.environ.get("WP_BACKEND_URL", "http://localhost:8000")
    )

    # Credential for the ingest endpoints, sent as the X-Device-Token header.
    # Mint one with POST /api/v1/devices/{device_id}/tokens. Without it the
    # collector still captures and writes to disk, but does not transmit.
    device_token: str = field(default_factory=lambda: os.environ.get("WP_DEVICE_TOKEN", ""))

    # Ring buffer — how many inference frames to keep in memory before oldest are dropped
    ring_buffer_size: int = field(
        default_factory=lambda: int(os.environ.get("WP_RING_BUFFER_SIZE", "512"))
    )

    # Local flush path — where to write msgpack bundles on trigger
    flush_path: str = field(
        default_factory=lambda: os.environ.get("WP_FLUSH_PATH", "/tmp/watchpoint/captures")
    )

    # Which model layers to capture intermediate activations for.
    # Empty list = capture only inputs/outputs of the full model.
    capture_layers: list[str] = field(default_factory=list)

    # Overhead guard: if hook latency exceeds this, emit a warning (µs)
    overhead_budget_us: int = 200

    @classmethod
    def from_env(cls) -> "CollectorConfig":
        """Construct config entirely from environment variables."""
        return cls()
