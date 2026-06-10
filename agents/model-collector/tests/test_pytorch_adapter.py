"""Tests for the PyTorch forward-hook adapter.

Requires torch to be installed (dev extra).
Skip gracefully if torch is not available.
"""

from __future__ import annotations

import pytest

try:
    import torch
    import torch.nn as nn

    HAS_TORCH = True
except ImportError:
    torch = None
    nn = None
    HAS_TORCH = False

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")


# ---------------------------------------------------------------------------
# Minimal test model
# ---------------------------------------------------------------------------

if HAS_TORCH:

    class TinyNet(nn.Module):
        """Two-layer linear network for testing hooks."""

        def __init__(self) -> None:
            super().__init__()
            self.fc1 = nn.Linear(8, 16)
            self.relu = nn.ReLU()
            self.fc2 = nn.Linear(16, 4)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.fc2(self.relu(self.fc1(x)))
else:

    class TinyNet:  # type: ignore[no-redef]
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_collector() -> "Collector":
    from model_collector import Collector

    return Collector(device_id="test-device", ring_buffer_size=64)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_hook_fires_on_forward() -> None:
    """Hook must record at least one frame per forward pass."""
    from model_collector.adapters.pytorch_adapter import attach_hooks

    model = TinyNet()
    collector = _make_collector()
    handles = attach_hooks(model, collector)

    x = torch.randn(1, 8)
    _ = model(x)

    assert collector.buffer_len >= 1
    for h in handles:
        h.remove()


def test_frame_has_required_fields() -> None:
    """Each frame must have the fields the backend expects."""
    from model_collector.adapters.pytorch_adapter import attach_hooks

    model = TinyNet()
    collector = _make_collector()
    handles = attach_hooks(model, collector)

    x = torch.randn(1, 8)
    _ = model(x)

    frames = collector._buf.snapshot()
    assert frames, "No frames recorded"

    # Top-level hook frame
    top_frame = next(f for f in frames if f["layer_name"] == "__top__")
    required = [
        "inference_id",
        "layer_name",
        "timestamp_ns",
        "input_shapes",
        "output_shape",
        "output_mean",
        "output_std",
        "model_run_id",
        "device_id",
    ]
    for field in required:
        assert field in top_frame, f"Missing field: {field}"

    for h in handles:
        h.remove()


def test_intermediate_layer_hooks() -> None:
    """Named layers in layer_names must each produce a frame."""
    from model_collector.adapters.pytorch_adapter import attach_hooks

    model = TinyNet()
    collector = _make_collector()
    handles = attach_hooks(model, collector, layer_names=["fc1", "fc2"])

    x = torch.randn(2, 8)
    _ = model(x)

    frames = collector._buf.snapshot()
    layer_names_seen = {f["layer_name"] for f in frames}
    assert "fc1" in layer_names_seen
    assert "fc2" in layer_names_seen

    for h in handles:
        h.remove()


def test_confidence_captured_for_classification_output() -> None:
    """Confidence (top-1 softmax) must be a float in [0, 1] for 2-D outputs."""
    from model_collector.adapters.pytorch_adapter import attach_hooks

    model = TinyNet()
    collector = _make_collector()
    handles = attach_hooks(model, collector)

    x = torch.randn(1, 8)
    _ = model(x)

    top_frame = next((f for f in collector._buf.snapshot() if f["layer_name"] == "__top__"), None)
    assert top_frame is not None
    conf = top_frame.get("confidence")
    assert conf is not None
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"

    for h in handles:
        h.remove()


def test_multiple_forward_passes_accumulate() -> None:
    """Each forward pass should add frames to the ring buffer."""
    from model_collector.adapters.pytorch_adapter import attach_hooks

    model = TinyNet()
    collector = _make_collector()
    handles = attach_hooks(model, collector)

    for _ in range(5):
        x = torch.randn(1, 8)
        _ = model(x)

    # 5 forward passes × 1 top-level hook = at least 5 frames
    assert collector.buffer_len >= 5

    for h in handles:
        h.remove()


def test_flush_clears_buffer(tmp_path: pytest.TempPathFactory) -> None:
    """flush() must write a file and clear the buffer."""
    from model_collector.adapters.pytorch_adapter import attach_hooks

    model = TinyNet()
    collector = _make_collector()
    collector.flush_path = str(tmp_path)
    handles = attach_hooks(model, collector)

    x = torch.randn(1, 8)
    _ = model(x)

    assert collector.buffer_len > 0
    path = collector.flush(incident_id="test-incident-001")
    assert collector.buffer_len == 0

    import os

    assert os.path.exists(path)
    assert path.endswith(".msgpack")

    for h in handles:
        h.remove()
