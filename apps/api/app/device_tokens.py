from __future__ import annotations

import hashlib
import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device

DEVICE_TOKEN_BYTES = 32


def generate_device_token() -> str:
    """Generate a high-entropy bearer token for a device."""
    return secrets.token_urlsafe(DEVICE_TOKEN_BYTES)


def hash_device_token(token: str) -> str:
    """Hash a device token before storing it in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_device_token(token: str, token_hash: str) -> bool:
    """Check whether the provided token matches the stored hash."""
    return secrets.compare_digest(hash_device_token(token), token_hash)


async def get_device_or_404(device_id: uuid.UUID, db: AsyncSession) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


async def require_device_token(
    device_id: uuid.UUID,
    device_token: str | None,
    db: AsyncSession,
) -> Device:
    """Require a valid device token for the given device."""
    if not device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token required",
        )

    device = await get_device_or_404(device_id, db)
    if not device.api_token_hash or not verify_device_token(device_token, device.api_token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device token",
        )
    return device
