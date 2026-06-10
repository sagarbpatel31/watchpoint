"""AI layer models — model runs, inferences, policy decisions, OOD signals.

These tables capture what the model saw, predicted, and decided during an
incident window. They are the core of Watchpoint's AI failure forensics.

Migration: alembic/versions/0002_ai_layer.py
Device auth migration: alembic/versions/0003_device_api_tokens.py
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Framework(str, enum.Enum):
    pytorch = "pytorch"
    onnx = "onnx"
    tensorrt = "tensorrt"


class ModelRun(UUIDMixin, TimestampMixin, Base):
    """One continuous model execution session on a device.

    A model run starts when the collector attaches hooks to a model and ends
    when the process exits or hooks are removed.  Many inferences belong to
    one model run.
    """

    __tablename__ = "model_runs"

    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), index=True)
    framework: Mapped[Framework] = mapped_column(Enum(Framework), default=Framework.pytorch)
    model_name: Mapped[str] = mapped_column(String(255))
    weights_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column()
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    device: Mapped["Device"] = relationship()  # type: ignore[name-defined]  # noqa: F821
    inferences: Mapped[list["Inference"]] = relationship(back_populates="model_run")


class Inference(UUIDMixin, Base):
    """One forward pass through the model.

    Captured by the model-collector hook adapter.  Small metadata only —
    heavy data (raw tensors, attention maps) lives in object storage
    referenced by input_ref / attention_ref.
    """

    __tablename__ = "inferences"

    model_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_runs.id"), index=True)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), index=True)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("incidents.id"), nullable=True, index=True
    )
    timestamp_ns: Mapped[int] = mapped_column(BigInteger, index=True)

    # Input metadata
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_ref: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # S3 key

    # Output summary
    outputs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Performance
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_mem_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Introspection (computed lazily on flush)
    attention_ref: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Layer-level capture (from pytorch_adapter)
    layer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    output_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    model_run: Mapped[ModelRun] = relationship(back_populates="inferences")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="inference")
    ood_signals: Mapped[list["OODSignal"]] = relationship(back_populates="inference")


class Decision(UUIDMixin, Base):
    """A policy decision made in response to an inference.

    Captures what action the policy chose, what alternatives it considered,
    and its confidence.  Used by rule AI-005 (decision-perception mismatch).
    """

    __tablename__ = "decisions"

    inference_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inferences.id"), index=True)
    policy_name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(500))
    alternatives: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Format: [{"action": "reroute_right", "score": 0.41}, ...]
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp_ns: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column()

    inference: Mapped[Inference] = relationship(back_populates="decisions")


class OODSignal(UUIDMixin, Base):
    """Out-of-distribution detection signal for one inference.

    Computed by the model-collector or backend from embedding distance,
    softmax entropy, or pixel statistics.  Used by rule AI-002.
    """

    __tablename__ = "ood_signals"

    inference_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inferences.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(100))
    # "embedding_distance" | "softmax_entropy" | "pixel_stats"
    score: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    is_ood: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column()

    inference: Mapped[Inference] = relationship(back_populates="ood_signals")
