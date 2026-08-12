"""Unit tests for AI-layer failure rules (AI-001, AI-002, AI-003).

All tests are fully offline — no live DB required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ai_layer import Inference, OODSignal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inference(confidence: float | None = None, latency_ms: float | None = None) -> Inference:
    inf = MagicMock(spec=Inference)
    inf.id = uuid.uuid4()
    inf.confidence = confidence
    inf.latency_ms = latency_ms
    inf.timestamp_ns = 0
    inf.incident_id = uuid.uuid4()
    return inf


def _ood(
    is_ood: bool,
    score: float = 1.0,
    threshold: float = 0.5,
    signal_type: str = "softmax_entropy",
) -> OODSignal:
    sig = MagicMock(spec=OODSignal)
    sig.is_ood = is_ood
    sig.score = score
    sig.threshold = threshold
    sig.signal_type = signal_type
    return sig


def _db_inferences(inferences: list[Inference]) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = inferences
    db.execute = AsyncMock(return_value=result)
    return db


def _db_ood(ood_signals: list[OODSignal]) -> AsyncMock:
    """DB mock for RuleAI002 — returns OOD signals from the join query."""
    db = AsyncMock()
    ood_result = MagicMock()
    ood_result.scalars.return_value.all.return_value = ood_signals
    db.execute = AsyncMock(return_value=ood_result)
    return db


# ---------------------------------------------------------------------------
# AI-001 — Perception confidence collapse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai001_fires_on_large_drop() -> None:
    """30%+ confidence drop in second half must fire AI-001."""
    from app.rca.ai_rules.rule_ai001 import RuleAI001

    # First half median ~0.93, second half median ~0.42 → ~55% drop
    infs = [_inference(confidence=0.93) for _ in range(6)] + [
        _inference(confidence=0.42) for _ in range(6)
    ]
    db = _db_inferences(infs)
    result = await RuleAI001().evaluate(uuid.uuid4(), db)

    assert result is not None
    assert result["rule_id"] == "AI-001"
    assert result["confidence"] > 0
    evidence = result["evidence"][0]
    assert evidence["drop_pct"] > 30


@pytest.mark.asyncio
async def test_ai001_no_fire_stable_confidence() -> None:
    """Stable confidence must not fire AI-001."""
    from app.rca.ai_rules.rule_ai001 import RuleAI001

    infs = [_inference(confidence=0.87 - i * 0.001) for i in range(12)]
    db = _db_inferences(infs)
    result = await RuleAI001().evaluate(uuid.uuid4(), db)

    assert result is None


@pytest.mark.asyncio
async def test_ai001_no_fire_insufficient_frames() -> None:
    """Fewer than 6 inferences with confidence must not fire."""
    from app.rca.ai_rules.rule_ai001 import RuleAI001

    infs = [_inference(confidence=0.90), _inference(confidence=0.40)]  # only 2
    db = _db_inferences(infs)
    result = await RuleAI001().evaluate(uuid.uuid4(), db)

    assert result is None


@pytest.mark.asyncio
async def test_ai001_ignores_none_confidence() -> None:
    """Inferences with confidence=None must be excluded from calculation."""
    from app.rca.ai_rules.rule_ai001 import RuleAI001

    # None values excluded; remaining 6 frames have negligible drop
    infs = (
        [_inference(confidence=None) for _ in range(10)]
        + [_inference(confidence=0.88) for _ in range(3)]
        + [_inference(confidence=0.85) for _ in range(3)]
    )
    db = _db_inferences(infs)
    result = await RuleAI001().evaluate(uuid.uuid4(), db)

    assert result is None  # drop < 30%


# ---------------------------------------------------------------------------
# AI-002 — OOD input detected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai002_fires_on_ood_signal() -> None:
    """Any is_ood=True signal must fire AI-002."""
    from app.rca.ai_rules.rule_ai002 import RuleAI002

    signals = [_ood(is_ood=True, score=0.81, threshold=0.60, signal_type="softmax_entropy")]
    db = _db_ood(signals)
    result = await RuleAI002().evaluate(uuid.uuid4(), db)

    assert result is not None
    assert result["rule_id"] == "AI-002"
    assert result["confidence"] == 0.65  # base confidence for 1 signal


@pytest.mark.asyncio
async def test_ai002_confidence_scales_with_signal_count() -> None:
    """More OOD signals → higher confidence (capped at 0.90)."""
    from app.rca.ai_rules.rule_ai002 import RuleAI002

    signals = [_ood(is_ood=True) for _ in range(6)]
    db = _db_ood(signals)
    result = await RuleAI002().evaluate(uuid.uuid4(), db)

    assert result is not None
    assert result["confidence"] == 0.90  # cap reached at 6 signals


@pytest.mark.asyncio
async def test_ai002_no_fire_all_false() -> None:
    """Signals with is_ood=False must not fire AI-002."""
    from app.rca.ai_rules.rule_ai002 import RuleAI002

    signals = [_ood(is_ood=False) for _ in range(5)]
    db = _db_ood(signals)
    result = await RuleAI002().evaluate(uuid.uuid4(), db)

    assert result is None


@pytest.mark.asyncio
async def test_ai002_no_fire_empty_signals() -> None:
    from app.rca.ai_rules.rule_ai002 import RuleAI002

    db = _db_ood([])
    result = await RuleAI002().evaluate(uuid.uuid4(), db)

    assert result is None


# ---------------------------------------------------------------------------
# AI-003 — Inference latency spike
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai003_fires_on_2x_latency_spike() -> None:
    """p99 latency ≥2× in second half must fire AI-003."""
    from app.rca.ai_rules.rule_ai003 import RuleAI003

    # First 6: 15ms, second 6: 150ms → 10× spike
    infs = [_inference(latency_ms=15.0) for _ in range(6)] + [
        _inference(latency_ms=150.0) for _ in range(6)
    ]
    db = _db_inferences(infs)
    result = await RuleAI003().evaluate(uuid.uuid4(), db)

    assert result is not None
    assert result["rule_id"] == "AI-003"
    evidence = result["evidence"][0]
    assert evidence["ratio"] >= 2.0


@pytest.mark.asyncio
async def test_ai003_no_fire_below_threshold() -> None:
    """Latency increase under 2× must not fire AI-003."""
    from app.rca.ai_rules.rule_ai003 import RuleAI003

    infs = [_inference(latency_ms=20.0) for _ in range(6)] + [
        _inference(latency_ms=35.0) for _ in range(6)  # 1.75× — under threshold
    ]
    db = _db_inferences(infs)
    result = await RuleAI003().evaluate(uuid.uuid4(), db)

    assert result is None


@pytest.mark.asyncio
async def test_ai003_no_fire_insufficient_frames() -> None:
    from app.rca.ai_rules.rule_ai003 import RuleAI003

    infs = [_inference(latency_ms=200.0) for _ in range(4)]  # only 4
    db = _db_inferences(infs)
    result = await RuleAI003().evaluate(uuid.uuid4(), db)

    assert result is None


@pytest.mark.asyncio
async def test_ai003_ignores_none_latency() -> None:
    """Inferences with latency_ms=None must be excluded."""
    from app.rca.ai_rules.rule_ai003 import RuleAI003

    # None frames excluded; remaining 6 have no significant spike
    infs = (
        [_inference(latency_ms=None) for _ in range(10)]
        + [_inference(latency_ms=20.0) for _ in range(3)]
        + [_inference(latency_ms=30.0) for _ in range(3)]
    )
    db = _db_inferences(infs)
    result = await RuleAI003().evaluate(uuid.uuid4(), db)

    assert result is None  # 30/20 = 1.5× — under threshold
