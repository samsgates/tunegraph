from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, require_permission
from tunegraph.db.models import BaseModelRecord
from tunegraph.domain.enums import ResourceState
from tunegraph.schemas import BaseModelCreate, BaseModelRead
from tunegraph.services.audit import record_audit

router = APIRouter(prefix="/base-models", tags=["base-models"])


@router.post("", response_model=BaseModelRead, status_code=201)
async def create_base_model(
    payload: BaseModelCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("models:*")),
) -> BaseModelRecord:
    record = BaseModelRecord(
        organization_id=principal.organization_id,
        **payload.model_dump(),
    )
    session.add(record)
    await session.flush()
    await record_audit(
        session,
        action="base_model.registered",
        resource_type="base_model",
        resource_id=record.id,
        principal=principal,
        after_state=payload.model_dump(),
    )
    await session.commit()
    await session.refresh(record)
    return record


@router.get("", response_model=list[BaseModelRead])
async def list_base_models(principal: PrincipalDep, session: SessionDep) -> list[BaseModelRecord]:
    return list(
        (
            await session.execute(
                select(BaseModelRecord)
                .where(BaseModelRecord.organization_id == principal.organization_id)
                .order_by(BaseModelRecord.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{model_id}", response_model=BaseModelRead)
async def get_base_model(model_id: str, principal: PrincipalDep, session: SessionDep) -> BaseModelRecord:
    record = await session.get(BaseModelRecord, model_id)
    if record is None or record.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Base model not found")
    return record


@router.post("/{model_id}/approve", response_model=BaseModelRead)
async def approve_base_model(
    model_id: str,
    session: SessionDep,
    principal: Principal = Depends(require_permission("models:*")),
) -> BaseModelRecord:
    record = await session.get(BaseModelRecord, model_id)
    if record is None or record.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Base model not found")
    before = {"state": record.state}
    record.state = ResourceState.APPROVED
    await record_audit(
        session,
        action="base_model.approved",
        resource_type="base_model",
        resource_id=record.id,
        principal=principal,
        before_state=before,
        after_state={"state": record.state},
    )
    await session.commit()
    await session.refresh(record)
    return record
