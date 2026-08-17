import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DeviceToken(UUIDMixin, TimestampMixin, Base):
    """Scoped API credential for an embedded agent.

    Agents (edge-agent, ros2-collector, model-collector) authenticate with one
    of these rather than a JWT: they are long-lived, headless, and cannot run a
    login flow or refresh an expiring token.

    Only the SHA-256 hash is stored. `token_prefix` is kept so a token can be
    identified in a list without exposing the secret.
    """

    __tablename__ = "device_tokens"

    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    token_prefix: Mapped[str] = mapped_column(String(16), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    device: Mapped["Device"] = relationship(back_populates="tokens")  # noqa: F821

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
