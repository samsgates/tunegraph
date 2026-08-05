from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, require_permission
from tunegraph.db.models import RemovalRequest
from tunegraph.schemas import RemovalRequestCreate, RemovalRequestRead
from tunegraph.services.audit import record_audit
from tunegraph.services.removal import RemovalService

router = APIRouter(prefix="/removal-requests", tags=["removals"])
service = RemovalService()


@router.post("", response_model=RemovalRequestRead, status_code=201)
async def create_removal_request(
    payload: RemovalRequestCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("removals:*")),
) -> RemovalRequest:
    request = RemovalRequest(
        organization_id=principal.organization_id,
        requested_by_user_id=principal.subject if principal.auth_type == "user" else None,
        **payload.model_dump(),
    )
    session.add(request)
    await session.flush()
    request.impact_report = await service.impact_report(
        session,
        organization_id=principal.organization_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )
    request.state = "impact_analyzed"
    await record_audit(
        session,
        action="removal.requested",
        resource_type="removal_request",
        resource_id=request.id,
        principal=principal,
        after_state={"target_type": payload.target_type, "target_id": payload.target_id},
    )
    await session.commit()
    await session.refresh(request)
    return request


@router.get("", response_model=list[RemovalRequestRead])
async def list_removal_requests(
    principal: PrincipalDep, session: SessionDep
) -> list[RemovalRequest]:
    return list(
        (
            await session.execute(
                select(RemovalRequest)
                .where(RemovalRequest.organization_id == principal.organization_id)
                .order_by(RemovalRequest.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{request_id}", response_model=RemovalRequestRead)
async def get_removal_request(
    request_id: str, principal: PrincipalDep, session: SessionDep
) -> RemovalRequest:
    request = await session.get(RemovalRequest, request_id)
    if request is None or request.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Removal request not found")
    return request


@router.post("/{request_id}/approve", response_model=RemovalRequestRead)
async def approve_removal_request(
    request_id: str,
    session: SessionDep,
    principal: Principal = Depends(require_permission("removals:approve")),
) -> RemovalRequest:
    request = await session.get(RemovalRequest, request_id)
    if request is None or request.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Removal request not found")
    if request.state != "impact_analyzed":
        raise HTTPException(status_code=409, detail="Removal request cannot be approved")
    request.state = "approved"
    await record_audit(
        session,
        action="removal.approved",
        resource_type="removal_request",
        resource_id=request.id,
        principal=principal,
        after_state={"state": request.state},
    )
    await session.commit()
    await session.refresh(request)
    return request


@router.post("/{request_id}/execute", response_model=RemovalRequestRead)
async def execute_removal_request(
    request_id: str,
    session: SessionDep,
    principal: Principal = Depends(require_permission("removals:*")),
) -> RemovalRequest:
    request = await session.get(RemovalRequest, request_id)
    if request is None or request.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Removal request not found")
    if request.state != "approved":
        raise HTTPException(status_code=409, detail="Removal request is not executable")
    request.state = "remediation_required"
    request.remediation_report = {
        "status": "manual_action_required",
        "recommended_strategy": request.impact_report.get("recommended_strategy"),
        "steps": [
            "Contain affected graph releases",
            "Retrain affected patch families without the target data",
            "Run retain-set and forget-set evaluations",
            "Publish and deploy a replacement graph release",
        ],
        "guarantee": "No claim of complete erasure is made until evidence is attached.",
    }
    await record_audit(
        session,
        action="removal.execution_started",
        resource_type="removal_request",
        resource_id=request.id,
        principal=principal,
        after_state=request.remediation_report,
    )
    await session.commit()
    await session.refresh(request)
    return request
