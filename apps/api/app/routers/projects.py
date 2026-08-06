import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.incident import Incident
from app.models.workspace import Project
from app.security import require_current_user

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(require_current_user)],
)


@router.get("/{project_id}")
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": str(project.id),
        "name": project.name,
        "slug": project.slug,
        "workspace_id": str(project.workspace_id),
        "created_at": project.created_at.isoformat(),
    }


@router.get("/{project_id}/summary")
async def get_project_summary(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    device_count = await db.execute(
        select(func.count(Device.id)).where(Device.project_id == project_id)
    )
    incident_count = await db.execute(
        select(func.count(Incident.id)).where(Incident.project_id == project_id)
    )
    online_count = await db.execute(
        select(func.count(Device.id)).where(
            Device.project_id == project_id, Device.status == "online"
        )
    )

    return {
        "project_id": str(project_id),
        "total_devices": device_count.scalar() or 0,
        "online_devices": online_count.scalar() or 0,
        "total_incidents": incident_count.scalar() or 0,
    }
