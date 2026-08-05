from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, require_permission
from tunegraph.db.models import Capability
from tunegraph.schemas import CapabilityCreate, CapabilityRead
from tunegraph.services.audit import record_audit

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.post("", response_model=CapabilityRead, status_code=201)
async def create_capability(
    payload: CapabilityCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("patches:create")),
) -> Capability:
    capability = Capability(organization_id=principal.organization_id, **payload.model_dump())
    session.add(capability)
    await session.flush()
    await record_audit(
        session,
        action="capability.created",
        resource_type="capability",
        resource_id=capability.id,
        principal=principal,
        after_state=payload.model_dump(),
    )
    await session.commit()
    await session.refresh(capability)
    return capability


@router.get("", response_model=list[CapabilityRead])
async def list_capabilities(principal: PrincipalDep, session: SessionDep) -> list[Capability]:
    return list(
        (
            await session.execute(
                select(Capability)
                .where(Capability.organization_id == principal.organization_id)
                .order_by(Capability.key)
            )
        ).scalars()
    )


@router.get("/{capability_id}", response_model=CapabilityRead)
async def get_capability(
    capability_id: str, principal: PrincipalDep, session: SessionDep
) -> Capability:
    capability = await session.get(Capability, capability_id)
    if capability is None or capability.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Capability not found")
    return capability
