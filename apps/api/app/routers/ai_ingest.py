"""AI layer ingest and query endpoints.

Routers:
  router             — POST /ingest/model-runs, /ingest/inferences, /ingest/decisions
                       Device-token auth (X-Device-Token); written to by the
                       model-collector agent.
  inferences_router  — GET /inferences/{id}, GET /inferences/{id}/attention
                       JWT auth; read by the dashboard.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ai_layer import Decision, Inference, ModelRun
from app.models.device import Device
from app.models.incident import Incident
from app.schemas.ai_layer import (
    AttentionResponse,
    DecisionBatchCreate,
    InferenceBatchCreate,
    InferenceResponse,
    IngestResponse,
    ModelRunCreate,
    ModelRunResponse,
)
from app.security import assert_device_matches, require_current_user, require_device_token

router = APIRouter(prefix="/ingest", tags=["ai-ingest"])
inferences_router = APIRouter(
    prefix="/inferences",
    tags=["ai-inferences"],
    dependencies=[Depends(require_current_user)],
)


# ---------------------------------------------------------------------------
# Model runs
# ---------------------------------------------------------------------------


@router.post(
    "/model-runs",
    status_code=status.HTTP_201_CREATED,
    response_model=ModelRunResponse,
    summary="Register a model run",
    description=(
        "Called by the model-collector agent when a model starts running on a device. "
        "Returns the persisted model run with its assigned ID."
    ),
)
async def create_model_run(
    payload: ModelRunCreate,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> ModelRunResponse:
    assert_device_matches(device, payload.device_id)
    run = ModelRun(
        id=payload.id or uuid.uuid4(),
        device_id=payload.device_id or device.id,
        framework=payload.framework,  # type: ignore[arg-type]
        model_name=payload.model_name,
        weights_hash=payload.weights_hash,
        started_at=payload.started_at or datetime.now(timezone.utc),
        metadata_json=payload.metadata,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return ModelRunResponse.model_validate(run)


# ---------------------------------------------------------------------------
# Inferences
# ---------------------------------------------------------------------------


@router.post(
    "/inferences",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestResponse,
    summary="Batch ingest inference frames",
    description=(
        "Accept a batch of inference frames captured by the model-collector hook adapter. "
        "Each frame records one forward pass through the model."
    ),
)
async def ingest_inferences(
    payload: InferenceBatchCreate,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> IngestResponse:
    # incident_id is a foreign key. An agent sending a stale or unknown one used
    # to surface as a 500 from the FK violation; answer 404 instead so the
    # client can tell a bad reference from a server fault.
    referenced_incidents = {i.incident_id for i in payload.inferences if i.incident_id}
    if referenced_incidents:
        known = await db.execute(select(Incident.id).where(Incident.id.in_(referenced_incidents)))
        missing = referenced_incidents - {row.id for row in known}
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown incident_id {sorted(str(m) for m in missing)[0]}",
            )

    rows: list[Inference] = []
    for item in payload.inferences:
        assert_device_matches(device, item.device_id)
        rows.append(
            Inference(
                id=item.inference_id or uuid.uuid4(),
                model_run_id=item.model_run_id,
                device_id=item.device_id or device.id,
                incident_id=item.incident_id,
                timestamp_ns=item.timestamp_ns,
                input_hash=item.input_hash,
                input_ref=item.input_ref,
                outputs=item.outputs,
                confidence=item.confidence,
                latency_ms=item.latency_ms,
                gpu_mem_mb=item.gpu_mem_mb,
                layer_name=item.layer_name,
                output_mean=item.output_mean,
                output_std=item.output_std,
            )
        )
    db.add_all(rows)
    await db.commit()
    return IngestResponse(created=len(rows))


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


@router.post(
    "/decisions",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestResponse,
    summary="Batch ingest policy decisions",
    description=(
        "Accept a batch of policy decision records. "
        "Each decision references an inference and records what action was chosen."
    ),
)
async def ingest_decisions(
    payload: DecisionBatchCreate,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(require_device_token),
) -> IngestResponse:
    # A decision carries no device_id of its own, so scope it through the
    # inference it references: every referenced inference must belong to the
    # device this token was issued for.
    referenced_ids = {item.inference_id for item in payload.decisions}
    owner_result = await db.execute(
        select(Inference.id, Inference.device_id).where(Inference.id.in_(referenced_ids))
    )
    owners = {row.id: row.device_id for row in owner_result}

    for inference_id in referenced_ids:
        owner_device_id = owners.get(inference_id)
        if owner_device_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown inference_id {inference_id}",
            )
        assert_device_matches(device, owner_device_id)

    now = datetime.now(timezone.utc)
    rows: list[Decision] = []
    for item in payload.decisions:
        rows.append(
            Decision(
                inference_id=item.inference_id,
                policy_name=item.policy_name,
                action=item.action,
                alternatives={"items": item.alternatives} if item.alternatives else None,
                confidence=item.confidence,
                timestamp_ns=item.timestamp_ns,
                created_at=now,
            )
        )
    db.add_all(rows)
    await db.commit()
    return IngestResponse(created=len(rows))


# ---------------------------------------------------------------------------
# Single-inference query (inferences_router — prefix /inferences)
# ---------------------------------------------------------------------------


@inferences_router.get(
    "/{inference_id}",
    response_model=InferenceResponse,
    summary="Get a single inference frame",
)
async def get_inference(
    inference_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InferenceResponse:
    result = await db.execute(select(Inference).where(Inference.id == inference_id))
    inf = result.scalar_one_or_none()
    if not inf:
        raise HTTPException(status_code=404, detail="Inference not found")
    return InferenceResponse.model_validate(inf)


@inferences_router.get(
    "/{inference_id}/attention",
    response_model=AttentionResponse,
    summary="Get attention / saliency metadata for an inference",
    description=(
        "Returns the attention map reference (S3 key) if Grad-CAM has been computed. "
        "Status is 'available' when attention_ref is set, 'unavailable' otherwise. "
        "Grad-CAM computation is implemented in Week 3."
    ),
)
async def get_inference_attention(
    inference_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AttentionResponse:
    result = await db.execute(select(Inference).where(Inference.id == inference_id))
    inf = result.scalar_one_or_none()
    if not inf:
        raise HTTPException(status_code=404, detail="Inference not found")

    # Extract heatmap from outputs JSON if present (seeded by demo data or model-collector)
    heatmap: list[list[float]] | None = None
    if inf.outputs and isinstance(inf.outputs, dict):
        raw = inf.outputs.get("attention_heatmap")
        if raw and isinstance(raw, list):
            heatmap = raw

    # Status: available if we have a heatmap grid OR an attention_ref (S3 key)
    status = "available" if (heatmap is not None or inf.attention_ref) else "unavailable"

    return AttentionResponse(
        inference_id=inf.id,
        attention_ref=inf.attention_ref,
        layer_name=inf.layer_name,
        status=status,
        heatmap=heatmap,
    )
