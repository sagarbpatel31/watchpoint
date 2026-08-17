import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Deployment, Device, DeviceStatus
from app.models.device_token import DeviceToken
from app.schemas.device import (
    DeploymentCreate,
    DeploymentResponse,
    DeviceRegister,
    DeviceResponse,
)
from app.schemas.device_token import (
    DeviceTokenCreate,
    DeviceTokenCreatedResponse,
    DeviceTokenResponse,
)
from app.security import generate_device_token, require_current_user

router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    dependencies=[Depends(require_current_user)],
)


@router.post("/register", response_model=DeviceResponse)
async def register_device(body: DeviceRegister, db: AsyncSession = Depends(get_db)):
    device = Device(
        project_id=body.project_id,
        device_name=body.device_name,
        hardware_model=body.hardware_model,
        os_version=body.os_version,
        agent_version=body.agent_version,
        status=DeviceStatus.online,
        last_seen_at=datetime.now(timezone.utc),
        registered_at=datetime.now(timezone.utc),
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(project_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Device)
    if project_id:
        query = query.where(Device.project_id == project_id)
    query = query.order_by(Device.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/heartbeat/{device_id}")
async def device_heartbeat(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.last_seen_at = datetime.now(timezone.utc)
    device.status = DeviceStatus.online
    await db.commit()
    return {"status": "ok"}


@router.post("/deployments", response_model=DeploymentResponse)
async def create_deployment(body: DeploymentCreate, db: AsyncSession = Depends(get_db)):
    deployment = Deployment(
        device_id=body.device_id,
        version=body.version,
        metadata_json=body.metadata_json,
        deployed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    return deployment


# ---------------------------------------------------------------------------
# Device tokens — credentials for embedded agents
# ---------------------------------------------------------------------------


@router.post(
    "/tokens/{token_id}/revoke",
    response_model=DeviceTokenResponse,
    summary="Revoke a device token",
    description=(
        "Soft-revokes the token by stamping revoked_at, preserving the audit "
        "trail of when it existed and when it was last used."
    ),
)
async def revoke_device_token(token_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeviceToken).where(DeviceToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    if token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(token)
    return token


@router.post(
    "/{device_id}/tokens",
    response_model=DeviceTokenCreatedResponse,
    status_code=201,
    summary="Mint a device token",
    description=(
        "Creates a credential for an embedded agent. The plaintext token is "
        "returned in `token_once` and is never retrievable again — only its "
        "SHA-256 hash is stored."
    ),
)
async def create_device_token(
    device_id: uuid.UUID,
    body: DeviceTokenCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Device not found")

    raw_token, prefix, token_hash = generate_device_token()
    token = DeviceToken(
        device_id=device_id,
        name=body.name,
        token_prefix=prefix,
        token_hash=token_hash,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    return DeviceTokenCreatedResponse(
        **DeviceTokenResponse.model_validate(token).model_dump(),
        token_once=raw_token,
    )


@router.get(
    "/{device_id}/tokens",
    response_model=list[DeviceTokenResponse],
    summary="List a device's tokens",
    description="Returns metadata only — the secret is not recoverable.",
)
async def list_device_tokens(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceToken)
        .where(DeviceToken.device_id == device_id)
        .order_by(DeviceToken.created_at.desc())
    )
    return result.scalars().all()
