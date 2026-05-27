"""Add AI layer tables: model_runs, inferences, decisions, ood_signals

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-01

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    framework_enum = sa.Enum("pytorch", "onnx", "tensorrt", name="framework")

    # model_runs
    op.create_table(
        "model_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("framework", framework_enum, nullable=False, server_default="pytorch"),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("weights_hash", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_model_runs_device_id", "model_runs", ["device_id"])

    # inferences
    op.create_table(
        "inferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_run_id", UUID(as_uuid=True), sa.ForeignKey("model_runs.id"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("timestamp_ns", sa.BigInteger, nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("input_ref", sa.String(1000), nullable=True),
        sa.Column("outputs", JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("gpu_mem_mb", sa.Integer, nullable=True),
        sa.Column("attention_ref", sa.String(1000), nullable=True),
        sa.Column("layer_name", sa.String(255), nullable=True),
        sa.Column("output_mean", sa.Float, nullable=True),
        sa.Column("output_std", sa.Float, nullable=True),
    )
    op.create_index("ix_inferences_model_run_id", "inferences", ["model_run_id"])
    op.create_index("ix_inferences_device_id", "inferences", ["device_id"])
    op.create_index("ix_inferences_incident_id", "inferences", ["incident_id"])
    op.create_index("ix_inferences_timestamp_ns", "inferences", ["timestamp_ns"])

    # decisions
    op.create_table(
        "decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("inference_id", UUID(as_uuid=True), sa.ForeignKey("inferences.id"), nullable=False),
        sa.Column("policy_name", sa.String(255), nullable=False),
        sa.Column("action", sa.String(500), nullable=False),
        sa.Column("alternatives", JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("timestamp_ns", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_decisions_inference_id", "decisions", ["inference_id"])

    # ood_signals
    op.create_table(
        "ood_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("inference_id", UUID(as_uuid=True), sa.ForeignKey("inferences.id"), nullable=False),
        sa.Column("signal_type", sa.String(100), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("is_ood", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ood_signals_inference_id", "ood_signals", ["inference_id"])


def downgrade() -> None:
    op.drop_table("ood_signals")
    op.drop_table("decisions")
    op.drop_table("inferences")
    op.drop_table("model_runs")
    sa.Enum(name="framework").drop(op.get_bind())
