import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    unknown = "unknown"


class Device(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    device_name: Mapped[str] = mapped_column(String(255))
    api_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hardware_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[DeviceStatus] = mapped_column(Enum(DeviceStatus), default=DeviceStatus.unknown)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    registered_at: Mapped[datetime] = mapped_column()

    project: Mapped["Project"] = relationship(back_populates="devices")  # noqa: F821
    deployments: Mapped[list["Deployment"]] = relationship(back_populates="device")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="device")  # noqa: F821
    event_logs: Mapped[list["EventLog"]] = relationship(back_populates="device")  # noqa: F821
    metric_points: Mapped[list["MetricPoint"]] = relationship(back_populates="device")  # noqa: F821


class Deployment(UUIDMixin, Base):
    __tablename__ = "deployments"

    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    version: Mapped[str] = mapped_column(String(255))
    deployed_at: Mapped[datetime] = mapped_column()
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column()

    device: Mapped[Device] = relationship(back_populates="deployments")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="deployment")  # noqa: F821
