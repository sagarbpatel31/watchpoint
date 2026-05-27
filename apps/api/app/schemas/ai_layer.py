"""Pydantic schemas for AI layer ingest and query endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ModelRun
# ---------------------------------------------------------------------------


class ModelRunCreate(BaseModel):
    """Payload for POST /ingest/model-runs."""

    id: Optional[uuid.UUID] = Field(default=None, description="Client-generated UUID (optional)")
    device_id: uuid.UUID
    framework: str = "pytorch"
    model_name: str
    weights_hash: Optional[str] = None
    started_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class ModelRunResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    framework: str
    model_name: str
    weights_hash: Optional[str]
    started_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


class InferenceItem(BaseModel):
    """One inference frame — part of a batch POST."""

    inference_id: Optional[uuid.UUID] = Field(
        default=None, description="Client-generated UUID. Auto-generated if absent."
    )
    model_run_id: uuid.UUID
    device_id: uuid.UUID
    incident_id: Optional[uuid.UUID] = None
    timestamp_ns: int
    input_hash: Optional[str] = None
    input_ref: Optional[str] = None
    outputs: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    gpu_mem_mb: Optional[int] = None
    layer_name: Optional[str] = None
    output_mean: Optional[float] = None
    output_std: Optional[float] = None


class InferenceBatchCreate(BaseModel):
    """Payload for POST /ingest/inferences."""

    inferences: list[InferenceItem] = Field(..., min_length=1)


class InferenceResponse(BaseModel):
    id: uuid.UUID
    model_run_id: uuid.UUID
    device_id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    timestamp_ns: int
    confidence: Optional[float]
    latency_ms: Optional[float]
    layer_name: Optional[str]
    output_mean: Optional[float]
    output_std: Optional[float]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class DecisionCreate(BaseModel):
    """One policy decision — part of a batch POST."""

    inference_id: uuid.UUID
    policy_name: str
    action: str
    alternatives: Optional[list[dict[str, Any]]] = None
    confidence: Optional[float] = None
    timestamp_ns: Optional[int] = None


class DecisionBatchCreate(BaseModel):
    """Payload for POST /ingest/decisions."""

    decisions: list[DecisionCreate] = Field(..., min_length=1)


class DecisionResponse(BaseModel):
    id: uuid.UUID
    inference_id: uuid.UUID
    policy_name: str
    action: str
    confidence: Optional[float]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# OODSignal
# ---------------------------------------------------------------------------


class OODSignalCreate(BaseModel):
    inference_id: uuid.UUID
    signal_type: str
    score: float
    threshold: float
    is_ood: bool = False


class OODSignalResponse(BaseModel):
    id: uuid.UUID
    inference_id: uuid.UUID
    signal_type: str
    score: float
    threshold: float
    is_ood: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Query responses
# ---------------------------------------------------------------------------


class InferenceListResponse(BaseModel):
    inferences: list[InferenceResponse]
    total: int


class AttentionResponse(BaseModel):
    inference_id: uuid.UUID
    attention_ref: Optional[str]
    layer_name: Optional[str]
    # "available" — heatmap data present; "unavailable" — not computed yet
    status: str
    # 8×8 normalized attention grid (0.0–1.0). None when status="unavailable".
    heatmap: Optional[list[list[float]]] = None


# ---------------------------------------------------------------------------
# Generic ingest response
# ---------------------------------------------------------------------------


class IngestResponse(BaseModel):
    created: int
    message: str = "ok"
