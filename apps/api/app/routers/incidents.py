import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ai_layer import Inference
from app.models.device import Deployment, Device
from app.models.incident import Incident, IncidentStatus
from app.models.telemetry import EventLog, MetricPoint
from app.schemas.ai_layer import InferenceListResponse, InferenceResponse
from app.schemas.incident import (
    IncidentCreate,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentResponse,
)
from app.security import require_current_user
from app.services.analysis import analyze_incident
from app.services.replay_bundle import generate_replay_bundle

router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_current_user)],
)


@router.post("/", response_model=IncidentResponse)
async def create_incident(body: IncidentCreate, db: AsyncSession = Depends(get_db)):
    incident = Incident(
        project_id=body.project_id,
        device_id=body.device_id,
        deployment_id=body.deployment_id,
        title=body.title,
        severity=body.severity,
        trigger_type=body.trigger_type,
        started_at=body.started_at or datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


@router.get("/", response_model=IncidentListResponse)
async def list_incidents(
    project_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    status: IncidentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Incident)
    count_query = select(func.count(Incident.id))

    if project_id:
        query = query.where(Incident.project_id == project_id)
        count_query = count_query.where(Incident.project_id == project_id)
    if device_id:
        query = query.where(Incident.device_id == device_id)
        count_query = count_query.where(Incident.device_id == device_id)
    if status:
        query = query.where(Incident.status == status)
        count_query = count_query.where(Incident.status == status)

    query = query.order_by(Incident.started_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    incidents = result.scalars().all()
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return IncidentListResponse(incidents=incidents, total=total)


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Get device name
    device_result = await db.execute(
        select(Device.device_name).where(Device.id == incident.device_id)
    )
    device_name = device_result.scalar_one_or_none()

    # Get deployment version
    deployment_version = None
    if incident.deployment_id:
        dep_result = await db.execute(
            select(Deployment.version).where(Deployment.id == incident.deployment_id)
        )
        deployment_version = dep_result.scalar_one_or_none()

    # Count events and metrics
    event_count_result = await db.execute(
        select(func.count(EventLog.id)).where(EventLog.incident_id == incident_id)
    )
    metric_count_result = await db.execute(
        select(func.count(MetricPoint.id)).where(MetricPoint.incident_id == incident_id)
    )

    return IncidentDetailResponse(
        **{c.name: getattr(incident, c.name) for c in incident.__table__.columns},
        device_name=device_name,
        deployment_version=deployment_version,
        event_count=event_count_result.scalar() or 0,
        metric_count=metric_count_result.scalar() or 0,
    )


@router.get("/{incident_id}/events")
async def get_incident_events(
    incident_id: uuid.UUID, limit: int = 500, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventLog)
        .where(EventLog.incident_id == incident_id)
        .order_by(EventLog.timestamp)
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "timestamp": e.timestamp.isoformat(),
            "level": e.level.value,
            "source": e.source,
            "message": e.message,
            "metadata_json": e.metadata_json,
        }
        for e in events
    ]


@router.get("/{incident_id}/metrics")
async def get_incident_metrics(
    incident_id: uuid.UUID, limit: int = 5000, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MetricPoint)
        .where(MetricPoint.incident_id == incident_id)
        .order_by(MetricPoint.timestamp)
        .limit(limit)
    )
    metrics = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "timestamp": m.timestamp.isoformat(),
            "metric_name": m.metric_name,
            "value": m.value,
            "unit": m.unit,
            "labels_json": m.labels_json,
        }
        for m in metrics
    ]


@router.get("/{incident_id}/inferences", response_model=InferenceListResponse)
async def list_incident_inferences(
    incident_id: uuid.UUID,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    """List all inference frames linked to an incident, ordered by timestamp."""
    result = await db.execute(
        select(Inference)
        .where(Inference.incident_id == incident_id)
        .order_by(Inference.timestamp_ns)
        .limit(limit)
    )
    inferences = result.scalars().all()
    rows = [InferenceResponse.model_validate(i) for i in inferences]
    return InferenceListResponse(inferences=rows, total=len(rows))


@router.post("/{incident_id}/analyze")
async def analyze_incident_endpoint(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    analysis = await analyze_incident(incident_id, db, incident_title=incident.title)

    incident.analysis_json = analysis
    incident.root_cause_summary = analysis.get("summary", "")
    incident.status = IncidentStatus.investigating
    await db.commit()

    return analysis


@router.post("/{incident_id}/replay-bundle")
async def create_replay_bundle(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    bundle_path = await generate_replay_bundle(incident_id, db)

    return {"bundle_path": bundle_path, "incident_id": str(incident_id)}
