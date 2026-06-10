"""Tests for the msgpack writer (no torch required)."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("msgpack")
np = pytest.importorskip("numpy")

from model_collector.writer import flush_to_disk, load_from_disk


def _make_frames(n: int = 5) -> list[dict]:
    return [
        {
            "inference_id": f"id-{i}",
            "layer_name": "__top__",
            "timestamp_ns": i * 1000,
            "output_mean": 0.5,
            "output_std": 0.1,
            "confidence": 0.9,
        }
        for i in range(n)
    ]


def test_flush_creates_file(tmp_path: pytest.TempPathFactory) -> None:
    frames = _make_frames()
    path = flush_to_disk(frames, str(tmp_path), incident_id="inc-001")
    assert os.path.exists(path)
    assert path.endswith(".msgpack")


def test_roundtrip(tmp_path: pytest.TempPathFactory) -> None:
    frames = _make_frames(3)
    path = flush_to_disk(frames, str(tmp_path), incident_id="inc-002")
    loaded = load_from_disk(path)
    assert len(loaded) == 3
    assert loaded[0]["inference_id"] == "id-0"
    assert loaded[2]["timestamp_ns"] == 2000


def test_numpy_roundtrip(tmp_path: pytest.TempPathFactory) -> None:
    arr = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    frames = [{"activations": arr}]
    path = flush_to_disk(frames, str(tmp_path), incident_id="inc-003")
    loaded = load_from_disk(path)
    np.testing.assert_array_almost_equal(loaded[0]["activations"], arr)


def test_flush_raises_on_empty(tmp_path: pytest.TempPathFactory) -> None:
    with pytest.raises(ValueError, match="No frames"):
        flush_to_disk([], str(tmp_path), incident_id="inc-004")
