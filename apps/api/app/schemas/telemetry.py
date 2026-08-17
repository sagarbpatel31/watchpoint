import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.telemetry import LogLevel

# Ingest payloads reject unknown fields.
#
# A collector that sent `labels` where the schema declares `labels_json` used to
# get a 200 back with the field silently discarded — the failure only showed up
# much later as telemetry that had lost the label identifying which topic it
# came from. Rejecting extras turns that class of mistake into a 422 at
# integration time.
_STRICT = {"extra": "forbid"}


class LogEntry(BaseModel):
    # Optional: filled in from the authenticated device token when absent, so an
    # agent does not need to know its own UUID. When present it is checked
    # against the token and rejected with 403 on mismatch.
    device_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    timestamp: datetime
    level: LogLevel = LogLevel.info
    source: str
    message: str
    metadata_json: Optional[dict] = None

    model_config = _STRICT


class LogBatchIngest(BaseModel):
    logs: list[LogEntry]

    model_config = _STRICT


class MetricEntry(BaseModel):
    device_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    timestamp: datetime
    metric_name: str
    value: float
    unit: Optional[str] = None
    labels_json: Optional[dict] = None

    model_config = _STRICT


class MetricBatchIngest(BaseModel):
    metrics: list[MetricEntry]

    model_config = _STRICT


class EventEntry(BaseModel):
    device_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    timestamp: datetime
    source: str
    message: str
    level: LogLevel = LogLevel.info
    metadata_json: Optional[dict] = None

    model_config = _STRICT


class EventBatchIngest(BaseModel):
    events: list[EventEntry]

    model_config = _STRICT


class LogResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    metadata_json: Optional[dict]

    model_config = {"from_attributes": True}


class MetricResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    timestamp: datetime
    metric_name: str
    value: float
    unit: Optional[str]
    labels_json: Optional[dict]

    model_config = {"from_attributes": True}
