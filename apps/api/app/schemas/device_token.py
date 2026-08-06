import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DeviceTokenCreate(BaseModel):
    name: str


class DeviceTokenResponse(BaseModel):
    """A token as listed. Deliberately has no field for the secret or its hash.

    Adding one here is the only way it could leak, so the omission is the
    control — not filtering at the call site.
    """

    id: uuid.UUID
    device_id: uuid.UUID
    name: str
    token_prefix: str
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceTokenCreatedResponse(DeviceTokenResponse):
    """Returned once, at creation. `token_once` is never retrievable again."""

    token_once: str
