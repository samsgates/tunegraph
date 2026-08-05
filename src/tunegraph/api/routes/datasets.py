from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, require_permission
from tunegraph.db.models import DatasetRecord
from tunegraph.domain.enums import ResourceState
from tunegraph.schemas import DatasetCreate, DatasetRead, DatasetValidationRequest
from tunegraph.services.audit import record_audit
from tunegraph.services.dataset_validation import DatasetValidator

router = APIRouter(prefix="/datasets", tags=["datasets"])
validator = DatasetValidator()


@router.post("", response_model=DatasetRead, status_code=201)
async def create_dataset(
    payload: DatasetCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("datasets:*")),
) -> DatasetRecord:
    dataset = DatasetRecord(organization_id=principal.organization_id, **payload.model_dump())
    session.add(dataset)
    await session.flush()
    await record_audit(
        session,
        action="dataset.registered",
        resource_type="dataset",
        resource_id=dataset.id,
        principal=principal,
        after_state=payload.model_dump(),
    )
    await session.commit()
    await session.refresh(dataset)
    return dataset


@router.get("", response_model=list[DatasetRead])
async def list_datasets(principal: PrincipalDep, session: SessionDep) -> list[DatasetRecord]:
    return list(
        (
            await session.execute(
                select(DatasetRecord)
                .where(DatasetRecord.organization_id == principal.organization_id)
                .order_by(DatasetRecord.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(dataset_id: str, principal: PrincipalDep, session: SessionDep) -> DatasetRecord:
    dataset = await session.get(DatasetRecord, dataset_id)
    if dataset is None or dataset.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/{dataset_id}/validate", response_model=DatasetRead)
async def validate_dataset(
    dataset_id: str,
    payload: DatasetValidationRequest,
    session: SessionDep,
    principal: Principal = Depends(require_permission("datasets:*")),
) -> DatasetRecord:
    dataset = await session.get(DatasetRecord, dataset_id)
    if dataset is None or dataset.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    report = validator.validate(
        record_count=dataset.record_count,
        content_sha256=dataset.content_sha256,
        metadata=dataset.metadata_json,
        checks=payload.checks,
        minimum_quality_score=payload.minimum_quality_score,
    )
    dataset.quality_report = report
    dataset.state = ResourceState.VALIDATED if report["passed"] else ResourceState.FAILED
    await record_audit(
        session,
        action="dataset.validated",
        resource_type="dataset",
        resource_id=dataset.id,
        principal=principal,
        after_state={"state": dataset.state, "quality_report": report},
    )
    await session.commit()
    await session.refresh(dataset)
    return dataset


@router.post("/{dataset_id}/approve", response_model=DatasetRead)
async def approve_dataset(
    dataset_id: str,
    session: SessionDep,
    principal: Principal = Depends(require_permission("datasets:*")),
) -> DatasetRecord:
    dataset = await session.get(DatasetRecord, dataset_id)
    if dataset is None or dataset.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.state != ResourceState.VALIDATED:
        raise HTTPException(status_code=409, detail="Dataset must pass validation before approval")
    dataset.state = ResourceState.APPROVED
    await record_audit(
        session,
        action="dataset.approved",
        resource_type="dataset",
        resource_id=dataset.id,
        principal=principal,
        after_state={"state": dataset.state},
    )
    await session.commit()
    await session.refresh(dataset)
    return dataset
