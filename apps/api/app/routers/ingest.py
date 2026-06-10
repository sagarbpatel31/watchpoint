from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.device_tokens import require_device_token
from app.models.telemetry import EventLog, MetricPoint
from app.schemas.telemetry import EventBatchIngest, LogBatchIngest, MetricBatchIngest

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/logs")
async def ingest_logs(
    body: LogBatchIngest,
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    device_id = body.logs[0].device_id
    await require_device_token(device_id, x_device_token, db)
    entries = []
    for log in body.logs:
        if log.device_id != device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All log entries in a batch must belong to the same device",
            )
        entry = EventLog(
            device_id=log.device_id,
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
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    device_id = body.metrics[0].device_id
    await require_device_token(device_id, x_device_token, db)
    entries = []
    for metric in body.metrics:
        if metric.device_id != device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All metric entries in a batch must belong to the same device",
            )
        entry = MetricPoint(
            device_id=metric.device_id,
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
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    device_id = body.events[0].device_id
    await require_device_token(device_id, x_device_token, db)
    entries = []
    for event in body.events:
        if event.device_id != device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All event entries in a batch must belong to the same device",
            )
        entry = EventLog(
            device_id=event.device_id,
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
