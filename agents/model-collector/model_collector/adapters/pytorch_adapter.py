"""PyTorch adapter — capture inference frames via register_forward_hook.

Design:
- Uses torch.nn.Module.register_forward_hook (non-intrusive).
- Captures: layer name, input/output shapes, output statistics, wall latency.
- All tensor data is detached + moved to CPU before capture (no grad tracking).
- Heavy work (Grad-CAM, S3 upload) deferred to flush — this hook is <100µs.

Usage:
    from model_collector import Collector
    from model_collector.adapters.pytorch_adapter import attach_hooks

    collector = Collector(device_id="robot-01")
    attach_hooks(model, collector, layer_names=["backbone.layer4", "head"])
    output = model(input_tensor)
"""

from __future__ import annotations

import hashlib
import time
import uuid
import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Avoid hard import at module level — torch may not be installed.
    import torch.nn as nn


def attach_hooks(
    model: "nn.Module",
    collector: Any,
    layer_names: list[str] | None = None,
) -> list[Any]:
    """Register forward hooks on the model and return hook handles.

    Args:
        model:       The PyTorch model to instrument.
        collector:   A Collector instance — frames are written via collector.record().
        layer_names: Named sub-modules to capture intermediate activations for.
                     Use ``model.named_modules()`` to discover available names.
                     Pass None or [] to capture only the top-level forward pass.

    Returns:
        List of hook handles.  Call handle.remove() to detach.

    Example:
        handles = attach_hooks(model, collector, layer_names=["layer1", "fc"])
        # ... run inference ...
        for h in handles: h.remove()
    """
    try:
        import torch  # noqa: F401
        import torch.nn as nn  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "PyTorch is required for pytorch_adapter. "
            "Install with: pip install 'watchpoint-model-collector[pytorch]'"
        ) from e

    handles: list[Any] = []
    layer_names_set = set(layer_names or [])

    # --- top-level hook (always attached) ---
    handles.append(_register_hook(model, "__top__", collector))

    # --- intermediate-layer hooks ---
    for name, module in model.named_modules():
        if name and name in layer_names_set:
            handles.append(_register_hook(module, name, collector))
        elif name and not layer_names_set:
            pass  # no intermediate layers requested

    if layer_names_set:
        found = {name for name, _ in model.named_modules() if name in layer_names_set}
        missing = layer_names_set - found
        if missing:
            warnings.warn(
                f"Layers not found in model: {missing}. "
                "Use list(model.named_modules()) to see available names.",
                UserWarning,
                stacklevel=2,
            )

    return handles


def _register_hook(module: Any, layer_name: str, collector: Any) -> Any:
    """Register one forward hook on module."""

    def hook(
        mod: Any,
        inputs: tuple[Any, ...],
        output: Any,
    ) -> None:
        t0 = time.perf_counter()
        frame = _capture_frame(layer_name, inputs, output)
        collector.record(frame)
        elapsed_us = (time.perf_counter() - t0) * 1e6
        if elapsed_us > 200:  # overhead budget
            warnings.warn(
                f"model-collector hook on '{layer_name}' took {elapsed_us:.0f}µs "
                "(budget: 200µs). Consider reducing capture_layers.",
                RuntimeWarning,
                stacklevel=2,
            )

    return module.register_forward_hook(hook)


def _capture_frame(
    layer_name: str,
    inputs: tuple[Any, ...],
    output: Any,
) -> dict[str, Any]:
    """Build a lightweight frame dict from hook arguments.

    Only small metadata is captured here.  Raw tensors are NOT stored
    (too large for the ring buffer at inference rate).
    """
    import torch

    # Wall clock, not time.monotonic_ns(): these timestamps are joined against
    # system telemetry and ROS 2 topic health on one incident timeline, and a
    # monotonic clock has an arbitrary epoch that cannot be correlated with
    # anything else.
    ts_ns = time.time_ns()
    inference_id = str(uuid.uuid4())

    frame: dict[str, Any] = {
        "inference_id": inference_id,
        "layer_name": layer_name,
        "timestamp_ns": ts_ns,
    }

    # --- input metadata ---
    input_shapes: list[list[int]] = []
    for inp in inputs:
        if isinstance(inp, torch.Tensor):
            input_shapes.append(list(inp.shape))
    frame["input_shapes"] = input_shapes

    # --- output metadata ---
    if isinstance(output, torch.Tensor):
        out_cpu = output.detach().cpu()
        frame["output_shape"] = list(out_cpu.shape)
        frame["output_mean"] = float(out_cpu.float().mean())
        frame["output_std"] = float(out_cpu.float().std())
        frame["output_min"] = float(out_cpu.float().min())
        frame["output_max"] = float(out_cpu.float().max())

        # Confidence: top-1 softmax probability (if 1-D or 2-D classification output)
        if out_cpu.dim() in (1, 2):
            try:
                probs = torch.softmax(out_cpu.float(), dim=-1)
                frame["confidence"] = float(probs.max())
            except Exception:
                frame["confidence"] = None
        else:
            frame["confidence"] = None

        # Input hash (of first input tensor) — for dedup and replay
        if inputs and isinstance(inputs[0], torch.Tensor):
            inp0_bytes = inputs[0].detach().cpu().numpy().tobytes()
            frame["input_hash"] = hashlib.sha256(inp0_bytes).hexdigest()[:16]

    elif isinstance(output, (tuple, list)):
        # Multi-output heads (e.g. YOLO returns (boxes, scores, classes))
        shapes = []
        for o in output:
            if isinstance(o, torch.Tensor):
                shapes.append(list(o.detach().shape))
        frame["output_shape"] = shapes
        frame["output_mean"] = None
        frame["output_std"] = None
        frame["confidence"] = None

    return frame
