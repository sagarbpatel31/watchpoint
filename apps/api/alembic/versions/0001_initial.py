"""Initial schema — all existing tables

Revision ID: 0001
Revises:
Create Date: 2026-05-01

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- enum types ---
    devicestatus = sa.Enum("online", "offline", "unknown", name="devicestatus")
    severity = sa.Enum("critical", "high", "medium", "low", name="severity")
    incidentstatus = sa.Enum("open", "investigating", "resolved", name="incidentstatus")
    artifacttype = sa.Enum(
        "log_bundle", "metrics_bundle", "replay_bundle", "ros2_snapshot",
        name="artifacttype",
    )
    loglevel = sa.Enum("debug", "info", "warn", "error", "fatal", name="loglevel")

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # workspaces
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])

    # projects
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])

    # devices
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=False),
        sa.Column("hardware_model", sa.String(255), nullable=True),
        sa.Column("os_version", sa.String(255), nullable=True),
        sa.Column("agent_version", sa.String(100), nullable=True),
        sa.Column("status", devicestatus, nullable=False, server_default="unknown"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # deployments
    op.create_table(
        "deployments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("version", sa.String(255), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # incidents
    op.create_table(
        "incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("severity", severity, nullable=False, server_default="medium"),
        sa.Column("status", incidentstatus, nullable=False, server_default="open"),
        sa.Column("trigger_type", sa.String(100), nullable=True),
        sa.Column("root_cause_summary", sa.Text, nullable=True),
        sa.Column("analysis_json", JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # incident_artifacts
    op.create_table(
        "incident_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("artifact_type", artifacttype, nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # event_logs
    op.create_table(
        "event_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", loglevel, nullable=False, server_default="info"),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata_json", JSONB, nullable=True),
    )
    op.create_index("ix_event_logs_device_id", "event_logs", ["device_id"])
    op.create_index("ix_event_logs_incident_id", "event_logs", ["incident_id"])
    op.create_index("ix_event_logs_timestamp", "event_logs", ["timestamp"])

    # metric_points
    op.create_table(
        "metric_points",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("labels_json", JSONB, nullable=True),
    )
    op.create_index("ix_metric_points_device_id", "metric_points", ["device_id"])
    op.create_index("ix_metric_points_incident_id", "metric_points", ["incident_id"])
    op.create_index("ix_metric_points_timestamp", "metric_points", ["timestamp"])
    op.create_index("ix_metric_points_metric_name", "metric_points", ["metric_name"])

    # annotations
    op.create_table(
        "annotations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("annotation_type", sa.String(50), nullable=False, server_default="note"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("annotations")
    op.drop_table("metric_points")
    op.drop_table("event_logs")
    op.drop_table("incident_artifacts")
    op.drop_table("incidents")
    op.drop_table("deployments")
    op.drop_table("devices")
    op.drop_table("projects")
    op.drop_table("workspaces")
    op.drop_table("users")
    sa.Enum(name="loglevel").drop(op.get_bind())
    sa.Enum(name="artifacttype").drop(op.get_bind())
    sa.Enum(name="incidentstatus").drop(op.get_bind())
    sa.Enum(name="severity").drop(op.get_bind())
    sa.Enum(name="devicestatus").drop(op.get_bind())
