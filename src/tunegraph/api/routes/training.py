from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, require_permission
from tunegraph.db.models import BaseModelRecord, Capability, DatasetRecord, TrainingJob
from tunegraph.domain.enums import JobState, ResourceState
from tunegraph.schemas import TrainingJobCreate, TrainingJobRead
from tunegraph.services.audit import record_audit

router = APIRouter(prefix="/training-jobs", tags=["training"])


@router.post("", response_model=TrainingJobRead, status_code=202)
async def create_training_job(
    payload: TrainingJobCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("training:*")),
) -> TrainingJob:
    base_model = await session.get(BaseModelRecord, payload.base_model_id)
    dataset = await session.get(DatasetRecord, payload.dataset_id)
    capability = await session.get(Capability, payload.capability_id)
    resources = [base_model, dataset, capability]
    if any(resource is None for resource in resources):
        raise HTTPException(status_code=404, detail="Training input was not found")
    if any(resource.organization_id != principal.organization_id for resource in resources if resource):
        raise HTTPException(status_code=404, detail="Training input was not found")
    if base_model.state != ResourceState.APPROVED or dataset.state != ResourceState.APPROVED:
        raise HTTPException(status_code=409, detail="Base model and dataset must be approved")
    job = TrainingJob(organization_id=principal.organization_id, **payload.model_dump())
    session.add(job)
    await session.flush()
    await record_audit(
        session,
        action="training.queued",
        resource_type="training_job",
        resource_id=job.id,
        principal=principal,
        after_state=payload.model_dump(),
    )
    await session.commit()
    await session.refresh(job)
    return job


@router.get("", response_model=list[TrainingJobRead])
async def list_training_jobs(principal: PrincipalDep, session: SessionDep) -> list[TrainingJob]:
    return list(
        (
            await session.execute(
                select(TrainingJob)
                .where(TrainingJob.organization_id == principal.organization_id)
                .order_by(TrainingJob.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{job_id}", response_model=TrainingJobRead)
async def get_training_job(job_id: str, principal: PrincipalDep, session: SessionDep) -> TrainingJob:
    job = await session.get(TrainingJob, job_id)
    if job is None or job.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job


@router.post("/{job_id}/cancel", response_model=TrainingJobRead)
async def cancel_training_job(
    job_id: str,
    session: SessionDep,
    principal: Principal = Depends(require_permission("training:*")),
) -> TrainingJob:
    job = await session.get(TrainingJob, job_id)
    if job is None or job.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Training job not found")
    if job.state not in {JobState.QUEUED, JobState.RUNNING}:
        raise HTTPException(status_code=409, detail="Job can no longer be cancelled")
    job.state = JobState.CANCELLED
    await record_audit(
        session,
        action="training.cancelled",
        resource_type="training_job",
        resource_id=job.id,
        principal=principal,
        after_state={"state": job.state},
    )
    await session.commit()
    await session.refresh(job)
    return job
