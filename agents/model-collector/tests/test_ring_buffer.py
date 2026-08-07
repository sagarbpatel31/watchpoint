"""Tests for the ring buffer."""

from __future__ import annotations

import threading

import pytest

from model_collector.ring_buffer import RingBuffer


def _frame(n: int) -> dict:
    return {"n": n, "data": "x" * 100}


def test_basic_append_and_snapshot() -> None:
    buf = RingBuffer(maxsize=4)
    for i in range(3):
        buf.append(_frame(i))
    snap = buf.snapshot()
    assert len(snap) == 3
    assert snap[0]["n"] == 0
    assert snap[2]["n"] == 2


def test_ring_drops_oldest_when_full() -> None:
    buf = RingBuffer(maxsize=3)
    for i in range(5):
        buf.append(_frame(i))
    snap = buf.snapshot()
    assert len(snap) == 3
    # Only frames 2, 3, 4 should remain
    assert [f["n"] for f in snap] == [2, 3, 4]


def test_clear() -> None:
    buf = RingBuffer(maxsize=10)
    buf.append(_frame(0))
    buf.clear()
    assert len(buf) == 0
    assert buf.snapshot() == []


def test_is_full() -> None:
    buf = RingBuffer(maxsize=2)
    assert not buf.is_full()
    buf.append(_frame(0))
    buf.append(_frame(1))
    assert buf.is_full()


def test_invalid_maxsize() -> None:
    with pytest.raises(ValueError):
        RingBuffer(maxsize=0)


def test_thread_safety() -> None:
    """Concurrent appends must not corrupt the buffer."""
    buf = RingBuffer(maxsize=1000)
    errors: list[Exception] = []

    def worker(start: int) -> None:
        try:
            for i in range(200):
                buf.append(_frame(start + i))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i * 200,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"
    # Buffer is capped at 1000; total appends = 1000
    assert len(buf) == 1000
