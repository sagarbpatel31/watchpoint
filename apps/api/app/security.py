import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.device import Device
from app.models.device_token import DeviceToken
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Device tokens look like: wp_<prefix>_<secret>
DEVICE_TOKEN_SCHEME = "wp"
_DEVICE_TOKEN_PREFIX_LEN = 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user from JWT token. Returns None if no token (for optional auth)."""
    if token is None:
        return None

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        return None

    return user


async def require_current_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Require authenticated user — raises 401 if not authenticated."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ---------------------------------------------------------------------------
# Device tokens (embedded agents)
# ---------------------------------------------------------------------------
#
# Deliberately SHA-256 rather than bcrypt, which is the opposite of the choice
# made for passwords above. Passwords are low-entropy and need a slow hash to
# survive offline cracking. A device token is 32 bytes from `secrets`, so it is
# not guessable and a slow hash buys nothing — while bcrypt's ~100ms would land
# on the ingest hot path, which agents hit continuously with batched telemetry.


def hash_device_token(raw_token: str) -> str:
    """SHA-256 hex digest of a raw device token — the stored lookup key."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_device_token() -> tuple[str, str, str]:
    """Mint a new device token.

    Returns `(raw_token, prefix, token_hash)`. The raw token is shown to the
    operator exactly once and never persisted.
    """
    secret = secrets.token_urlsafe(32)
    prefix = secrets.token_hex(_DEVICE_TOKEN_PREFIX_LEN // 2)
    raw_token = f"{DEVICE_TOKEN_SCHEME}_{prefix}_{secret}"
    return raw_token, prefix, hash_device_token(raw_token)


async def require_device_token(
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
) -> Device:
    """Authenticate an embedded agent and return the device it may write as.

    Returning the Device (rather than a bool) lets ingest routes verify that the
    payload's device_id matches the credential. Without that check any valid
    token could attribute telemetry to any device, which would corrupt the
    per-device baselines AI-001 and AI-003 compute against.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing device token",
        headers={"WWW-Authenticate": "DeviceToken"},
    )

    if not x_device_token:
        raise unauthorized

    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token_hash == hash_device_token(x_device_token))
    )
    token = result.scalar_one_or_none()

    if token is None or token.revoked_at is not None:
        raise unauthorized

    device_result = await db.execute(select(Device).where(Device.id == token.device_id))
    device = device_result.scalar_one_or_none()
    if device is None:
        raise unauthorized

    token.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return device


def assert_device_matches(device: Device, payload_device_id: uuid.UUID | None) -> None:
    """Reject telemetry a token is not scoped to write.

    A missing device_id in the payload is allowed — the route fills it in from
    the authenticated device.
    """
    if payload_device_id is not None and payload_device_id != device.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device token is not authorised for the device_id in this payload",
        )
