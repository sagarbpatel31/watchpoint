"""Unit tests for the rules-based analysis engine.

Tests run without a live database — we mock the DB session to return
controlled metric/event fixtures and verify rule trigger logic directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.telemetry import EventLog, LogLevel, MetricPoint

# ---------------------------------------------------------------------------
# Helpers — build fake ORM objects
# ---------------------------------------------------------------------------


def _metric(name: str, value: float) -> MetricPoint:
    m = MagicMock(spec=MetricPoint)
    m.metric_name = name
    m.value = value
    m.timestamp = datetime.now(timezone.utc)
    m.incident_id = uuid.uuid4()
    return m


def _event(message: str, level: LogLevel = LogLevel.info) -> EventLog:
    e = MagicMock(spec=EventLog)
    e.message = message
    e.level = level
    e.timestamp = datetime.now(timezone.utc)
    return e


def _mock_db(metrics: list[MetricPoint], events: list[EventLog]) -> AsyncMock:
    """Return an AsyncSession mock that yields the given metrics and events.

    Call order expected by analyze_incident:
      1. metrics    (Rule 1–7 system rules)
      2. events     (Rule 1–7 system rules)
      3. inferences (RuleAI001._get_inferences)
      4. ood_signals (RuleAI002._get_ood_signals via inferences join)
      5. inferences (RuleAI003._get_inferences)
    """
    db = AsyncMock()

    metrics_result = MagicMock()
    metrics_result.scalars.return_value.all.return_value = metrics

    events_result = MagicMock()
    events_result.scalars.return_value.all.return_value = events

    # AI rules receive empty data — they should not fire in system-rule tests
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(
        side_effect=[metrics_result, events_result, empty_result, empty_result, empty_result]
    )
    return db


# ---------------------------------------------------------------------------
# Rule 1 — Resource contention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule1_resource_contention_fires() -> None:
    metrics = [_metric("cpu_percent", 92.0), _metric("topic_rate_hz", 3.0)]
    db = _mock_db(metrics, [])

    with patch("app.services.analysis.generate_llm_summary", return_value="test summary"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db, incident_title="CPU spike test")

    causes = {c["cause"] for c in result["probable_causes"]}
    assert "Resource contention" in causes


@pytest.mark.asyncio
async def test_rule1_no_fire_when_cpu_low() -> None:
    metrics = [_metric("cpu_percent", 50.0), _metric("topic_rate_hz", 3.0)]
    db = _mock_db(metrics, [])

    with patch("app.services.analysis.generate_llm_summary", return_value="test summary"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db)

    causes = {c["cause"] for c in result["probable_causes"]}
    assert "Resource contention" not in causes


# ---------------------------------------------------------------------------
# Rule 2 — Thermal throttling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule2_thermal_throttling_fires() -> None:
    metrics = [_metric("gpu_temp_c", 80.0), _metric("inference_latency_ms", 150.0)]
    db = _mock_db(metrics, [])

    with patch("app.services.analysis.generate_llm_summary", return_value="test summary"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db, incident_title="Thermal test")

    causes = {c["cause"] for c in result["probable_causes"]}
    assert "Thermal throttling" in causes


# ---------------------------------------------------------------------------
# Rule 3 — Process failure chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule3_process_failure_chain_fires() -> None:
    events = [
        _event("node navigation_node crash detected", LogLevel.error),
        _event("watchdog timeout: navigation_node unresponsive", LogLevel.error),
    ]
    db = _mock_db([], events)

    with patch("app.services.analysis.generate_llm_summary", return_value="test summary"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db)

    causes = {c["cause"] for c in result["probable_causes"]}
    assert "Process failure chain" in causes


# ---------------------------------------------------------------------------
# Rule 4 — Version regression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule4_version_regression_fires() -> None:
    events = [
        _event("deployment v2.1.0 applied", LogLevel.info),
        _event("latency higher than baseline — regression detected", LogLevel.warn),
    ]
    db = _mock_db([], events)

    with patch("app.services.analysis.generate_llm_summary", return_value="test summary"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db)

    causes = {c["cause"] for c in result["probable_causes"]}
    assert "Version regression" in causes


# ---------------------------------------------------------------------------
# Fallback — unknown cause when no rules fire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_when_no_rules_match() -> None:
    db = _mock_db([], [])

    with patch("app.services.analysis.generate_llm_summary", return_value="test summary"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db)

    causes = {c["cause"] for c in result["probable_causes"]}
    assert "Unknown — manual investigation needed" in causes
    assert result["probable_causes"][0]["confidence"] == 0.3


# ---------------------------------------------------------------------------
# LLM fallback — no API key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_fallback_without_api_key() -> None:
    """generate_llm_summary must return rules text when ANTHROPIC_API_KEY is empty."""
    from app.services.analysis import generate_llm_summary

    with patch("app.services.analysis.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        result = await generate_llm_summary(
            incident_title="test",
            top_cause={
                "cause": "Resource contention",
                "description": "CPU too high",
                "confidence": 0.85,
            },
            evidence_signals=["CPU at 92%"],
        )

    assert result == "CPU too high"


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_has_required_fields() -> None:
    db = _mock_db([], [])

    with patch("app.services.analysis.generate_llm_summary", return_value="summary text"):
        from app.services.analysis import analyze_incident

        result = await analyze_incident(uuid.uuid4(), db)

    required = [
        "summary",
        "probable_causes",
        "evidence",
        "suggested_steps",
        "metrics_analyzed",
        "events_analyzed",
    ]
    for field in required:
        assert field in result, f"Missing field: {field}"

    assert isinstance(result["probable_causes"], list)
    assert len(result["probable_causes"]) >= 1
    top = result["probable_causes"][0]
    assert "cause" in top
    assert "confidence" in top
    assert 0.0 <= top["confidence"] <= 1.0
