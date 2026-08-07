"""Payload shape must match the ingest schemas exactly.

These are regression tests for two bugs that produced no error at all:

  * `send_logs` posted `{"events": [...]}` to /ingest/logs, which declares
    `logs` — a 422 the collector logged as a warning and moved on from.
  * metrics were sent with `labels` where the schema declares `labels_json`.
    The API accepted the batch and discarded the field, so every
    `topic_rate_hz` point was stored with no record of which topic it measured.

The second is the dangerous one: ingest returned 200 and the data was useless.
Asserting on the wire format is the only way to catch that class of mistake
without a live backend.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ros2_collector.main import collect_and_send
from ros2_collector.sender import WatchpointSender

TOKEN = "wp_abcd1234_secret"


class _RecordingSender:
    """Captures what collect_and_send would transmit."""

    def __init__(self) -> None:
        self.metrics: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []

    async def send_metrics(self, metric_points: list[dict[str, Any]]) -> bool:
        self.metrics = metric_points
        return True

    async def send_logs(self, events: list[dict[str, Any]]) -> bool:
        self.logs = events
        return True


def _monitors() -> tuple[MagicMock, MagicMock]:
    topic_monitor = MagicMock()
    topic_monitor.list_topics.return_value = ["/cmd_vel", "/scan"]
    topic_monitor.measure_rates.return_value = {"/cmd_vel": 30.0, "/scan": 10.0}
    node_inspector = MagicMock()
    node_inspector.list_nodes.return_value = ["/nav2", "/controller"]
    return topic_monitor, node_inspector


# ---------------------------------------------------------------------------
# Metric payloads
# ---------------------------------------------------------------------------


async def test_topic_rate_carries_the_topic_label() -> None:
    """The label identifying *which* topic must survive to the wire."""
    topic_monitor, node_inspector = _monitors()
    sender = _RecordingSender()

    await collect_and_send(topic_monitor, node_inspector, sender)

    rates = [m for m in sender.metrics if m["metric_name"] == "topic_rate_hz"]
    assert len(rates) == 2
    for point in rates:
        assert "labels_json" in point, "must be labels_json, not labels"
        assert "labels" not in point
        assert point["labels_json"]["topic"] in {"/cmd_vel", "/scan"}


async def test_metrics_omit_device_id() -> None:
    """device_id comes from the token server-side, not the payload."""
    topic_monitor, node_inspector = _monitors()
    sender = _RecordingSender()

    await collect_and_send(topic_monitor, node_inspector, sender)

    assert sender.metrics
    for point in sender.metrics:
        assert "device_id" not in point


async def test_metric_fields_are_all_declared_by_the_schema() -> None:
    """Ingest rejects unknown fields, so every key must be a real one."""
    allowed = {
        "device_id",
        "incident_id",
        "timestamp",
        "metric_name",
        "value",
        "unit",
        "labels_json",
    }
    topic_monitor, node_inspector = _monitors()
    sender = _RecordingSender()

    await collect_and_send(topic_monitor, node_inspector, sender)

    for point in sender.metrics:
        assert set(point) <= allowed, f"undeclared field(s): {set(point) - allowed}"


# ---------------------------------------------------------------------------
# Log payloads
# ---------------------------------------------------------------------------


async def test_log_event_uses_metadata_json() -> None:
    topic_monitor, node_inspector = _monitors()
    sender = _RecordingSender()

    await collect_and_send(topic_monitor, node_inspector, sender)

    assert len(sender.logs) == 1
    event = sender.logs[0]
    assert "metadata_json" in event, "must be metadata_json, not metadata"
    assert "metadata" not in event
    assert event["metadata_json"]["rates"] == {"/cmd_vel": 30.0, "/scan": 10.0}


async def test_log_fields_are_all_declared_by_the_schema() -> None:
    allowed = {
        "device_id",
        "incident_id",
        "timestamp",
        "level",
        "source",
        "message",
        "metadata_json",
    }
    topic_monitor, node_inspector = _monitors()
    sender = _RecordingSender()

    await collect_and_send(topic_monitor, node_inspector, sender)

    for event in sender.logs:
        assert set(event) <= allowed, f"undeclared field(s): {set(event) - allowed}"


# ---------------------------------------------------------------------------
# Envelope and auth
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "envelope"),
    [
        ("send_metrics", "/api/v1/ingest/metrics", "metrics"),
        ("send_logs", "/api/v1/ingest/logs", "logs"),
    ],
)
async def test_envelope_key_matches_the_endpoint(method: str, path: str, envelope: str) -> None:
    sender = WatchpointSender(api_url="http://backend", token=TOKEN)
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.status_code = 200
    sender._client.post = AsyncMock(return_value=response)

    await getattr(sender, method)([{"any": "payload"}])

    called_path, kwargs = sender._client.post.await_args
    assert called_path[0] == path
    assert envelope in kwargs["json"], f"{method} must post {{'{envelope}': [...]}}"
    await sender.close()


async def test_token_is_sent_as_a_header() -> None:
    sender = WatchpointSender(api_url="http://backend", token=TOKEN)
    assert sender._client.headers["X-Device-Token"] == TOKEN
    await sender.close()


async def test_missing_token_does_not_set_the_header() -> None:
    """Runs without a token so local/simulation use still works; ingest 401s."""
    sender = WatchpointSender(api_url="http://backend")
    assert "X-Device-Token" not in sender._client.headers
    await sender.close()
