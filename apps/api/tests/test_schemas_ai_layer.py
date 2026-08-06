"""Tests for AI layer Pydantic schemas — validation logic only, no DB."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.ai_layer import (
    DecisionBatchCreate,
    InferenceBatchCreate,
    InferenceItem,
    ModelRunCreate,
)


def test_model_run_create_minimal() -> None:
    device_id = uuid.uuid4()
    m = ModelRunCreate(device_id=device_id, model_name="yolov8n")
    assert m.device_id == device_id
    assert m.model_name == "yolov8n"
    assert m.framework == "pytorch"
    assert m.id is None


def test_model_run_create_with_explicit_id() -> None:
    run_id = uuid.uuid4()
    device_id = uuid.uuid4()
    m = ModelRunCreate(id=run_id, device_id=device_id, model_name="resnet18")
    assert m.id == run_id


def test_inference_batch_requires_at_least_one() -> None:
    with pytest.raises(ValidationError):
        InferenceBatchCreate(inferences=[])


def test_inference_batch_valid() -> None:
    model_run_id = uuid.uuid4()
    device_id = uuid.uuid4()
    item = InferenceItem(
        model_run_id=model_run_id,
        device_id=device_id,
        timestamp_ns=1_000_000_000,
        confidence=0.87,
        layer_name="__top__",
    )
    batch = InferenceBatchCreate(inferences=[item])
    assert len(batch.inferences) == 1
    assert batch.inferences[0].confidence == 0.87


def test_decision_batch_requires_at_least_one() -> None:
    with pytest.raises(ValidationError):
        DecisionBatchCreate(decisions=[])


def test_decision_batch_valid() -> None:
    from app.schemas.ai_layer import DecisionCreate

    d = DecisionCreate(
        inference_id=uuid.uuid4(),
        policy_name="nav_policy_v2",
        action="continue_at_speed",
        confidence=0.39,
        alternatives=[{"action": "reroute_right", "score": 0.41}],
    )
    batch = DecisionBatchCreate(decisions=[d])
    assert batch.decisions[0].action == "continue_at_speed"
