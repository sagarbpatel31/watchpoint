import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.device import DeviceStatus


class DeviceRegister(BaseModel):
    project_id: uuid.UUID
    device_name: str
    hardware_model: Optional[str] = None
    os_version: Optional[str] = None
    agent_version: Optional[str] = None


class DeviceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    device_name: str
    hardware_model: Optional[str]
    os_version: Optional[str]
    agent_version: Optional[str]
    status: DeviceStatus
    last_seen_at: Optional[datetime]
    registered_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceRegistrationResponse(DeviceResponse):
    device_token: str


class DeploymentCreate(BaseModel):
    device_id: uuid.UUID
    version: str
    metadata_json: Optional[dict] = None


class DeploymentResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    version: str
    deployed_at: datetime
    metadata_json: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}
