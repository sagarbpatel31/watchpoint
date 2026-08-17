"""Telemetry ingest — authenticated with a device token (X-Device-Token).

Agents are headless and long-lived, so they authenticate with a scoped device
token rather than a JWT. Every batch is checked against the credential: a token
may only write telemetry for the device it was issued to.

`device_id` is optional in the payload. When omitted it is taken from the token,
so an agent needs only a backend URL and a credential — it never has to know its
own UUID. When supplied it must match the token, or the batch is rejected.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.telemetry import EventLog, MetricPoint
from app.schemas.telemetry import EventBatchIngest, LogBatchIngest, MetricBatchIngest
from app.security import assert_device_matches, require_device_token

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/logs")
async def ingest_logs(
    body: LogBatchIngest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device_token),
):
    entries = []
    for log in body.logs:
        assert_device_matches(device, log.device_id)
        entry = EventLog(
            device_id=log.device_id or device.id,
            incident_id=log.incident_id,
            timestamp=log.timestamp,
            level=log.level,
            source=log.source,
            message=log.message,
            metadata_json=log.metadata_json,
        )
        entries.append(entry)
    db.add_all(entries)
    await db.commit()
    return {"ingested": len(entries)}


@router.post("/metrics")
async def ingest_metrics(
    body: MetricBatchIngest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device_token),
):
    entries = []
    for metric in body.metrics:
        assert_device_matches(device, metric.device_id)
        entry = MetricPoint(
            device_id=metric.device_id or device.id,
            incident_id=metric.incident_id,
            timestamp=metric.timestamp,
            metric_name=metric.metric_name,
            value=metric.value,
            unit=metric.unit,
            labels_json=metric.labels_json,
        )
        entries.append(entry)
    db.add_all(entries)
    await db.commit()
    return {"ingested": len(entries)}


@router.post("/events")
async def ingest_events(
    body: EventBatchIngest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device_token),
):
    entries = []
    for event in body.events:
        assert_device_matches(device, event.device_id)
        entry = EventLog(
            device_id=event.device_id or device.id,
            incident_id=event.incident_id,
            timestamp=event.timestamp,
            level=event.level,
            source=event.source,
            message=event.message,
            metadata_json=event.metadata_json,
        )
        entries.append(entry)
    db.add_all(entries)
    await db.commit()
    return {"ingested": len(entries)}
