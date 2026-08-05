from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, SettingsDep, require_permission
from tunegraph.db.models import Deployment, GraphRelease
from tunegraph.domain.enums import DeploymentState, ResourceState
from tunegraph.schemas import DeploymentAction, DeploymentCreate, DeploymentGraphUpdate, DeploymentRead
from tunegraph.services.audit import record_audit
from tunegraph.services.integrity import graph_integrity_errors

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentRead, status_code=201)
async def create_deployment(
    payload: DeploymentCreate,
    session: SessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("deployments:*")),
) -> Deployment:
    graph = await session.get(GraphRelease, payload.graph_release_id)
    if graph is None or graph.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Graph release not found")
    if graph.state != ResourceState.APPROVED:
        raise HTTPException(status_code=409, detail="Graph release must be published")
    integrity_errors = graph_integrity_errors(graph, settings)
    if integrity_errors:
        raise HTTPException(status_code=409, detail={"integrity_errors": integrity_errors})
    deployment = Deployment(organization_id=principal.organization_id, **payload.model_dump())
    session.add(deployment)
    await session.flush()
    await record_audit(
        session,
        action="deployment.created",
        resource_type="deployment",
        resource_id=deployment.id,
        principal=principal,
        after_state=payload.model_dump(),
    )
    await session.commit()
    await session.refresh(deployment)
    return deployment


@router.get("", response_model=list[DeploymentRead])
async def list_deployments(principal: PrincipalDep, session: SessionDep) -> list[Deployment]:
    return list(
        (
            await session.execute(
                select(Deployment)
                .where(Deployment.organization_id == principal.organization_id)
                .order_by(Deployment.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{deployment_id}", response_model=DeploymentRead)
async def get_deployment(
    deployment_id: str, principal: PrincipalDep, session: SessionDep
) -> Deployment:
    deployment = await session.get(Deployment, deployment_id)
    if deployment is None or deployment.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post("/{deployment_id}/canary", response_model=DeploymentRead)
async def canary_deployment(
    deployment_id: str,
    payload: DeploymentAction,
    session: SessionDep,
    principal: Principal = Depends(require_permission("deployments:*")),
) -> Deployment:
    deployment = await session.get(Deployment, deployment_id)
    if deployment is None or deployment.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Deployment not found")
    deployment.state = DeploymentState.HEALTHY
    deployment.traffic_percentage = payload.traffic_percentage or 5
    deployment.health = {"status": "canary", "reason": payload.reason}
    await record_audit(
        session,
        action="deployment.canary",
        resource_type="deployment",
        resource_id=deployment.id,
        principal=principal,
        after_state={"traffic_percentage": deployment.traffic_percentage},
    )
    await session.commit()
    await session.refresh(deployment)
    return deployment


@router.post("/{deployment_id}/promote", response_model=DeploymentRead)
async def promote_deployment(
    deployment_id: str,
    payload: DeploymentAction,
    session: SessionDep,
    principal: Principal = Depends(require_permission("deployments:*")),
) -> Deployment:
    deployment = await session.get(Deployment, deployment_id)
    if deployment is None or deployment.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Deployment not found")
    deployment.state = DeploymentState.HEALTHY
    deployment.traffic_percentage = payload.traffic_percentage or 100
    deployment.health = {"status": "healthy", "reason": payload.reason}
    await record_audit(
        session,
        action="deployment.promoted",
        resource_type="deployment",
        resource_id=deployment.id,
        principal=principal,
        after_state={"traffic_percentage": deployment.traffic_percentage},
    )
    await session.commit()
    await session.refresh(deployment)
    return deployment


@router.post("/{deployment_id}/rollback", response_model=DeploymentRead)
async def rollback_deployment(
    deployment_id: str,
    payload: DeploymentAction,
    session: SessionDep,
    principal: Principal = Depends(require_permission("deployments:*")),
) -> Deployment:
    deployment = await session.get(Deployment, deployment_id)
    if deployment is None or deployment.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not deployment.previous_graph_release_id:
        raise HTTPException(status_code=409, detail="No previous graph release is recorded")
    current = deployment.graph_release_id
    deployment.graph_release_id = deployment.previous_graph_release_id
    deployment.previous_graph_release_id = current
    deployment.state = DeploymentState.ROLLED_BACK
    deployment.health = {"status": "rolled_back", "reason": payload.reason}
    await record_audit(
        session,
        action="deployment.rolled_back",
        resource_type="deployment",
        resource_id=deployment.id,
        principal=principal,
        after_state={"graph_release_id": deployment.graph_release_id},
    )
    await session.commit()
    await session.refresh(deployment)
    return deployment


@router.post("/{deployment_id}/graph", response_model=DeploymentRead)
async def update_deployment_graph(
    deployment_id: str,
    payload: DeploymentGraphUpdate,
    session: SessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("deployments:*")),
) -> Deployment:
    deployment = await session.get(Deployment, deployment_id)
    graph = await session.get(GraphRelease, payload.graph_release_id)
    if deployment is None or deployment.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if graph is None or graph.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Graph release not found")
    if graph.state != ResourceState.APPROVED:
        raise HTTPException(status_code=409, detail="Graph release must be published")
    integrity_errors = graph_integrity_errors(graph, settings)
    if integrity_errors:
        raise HTTPException(status_code=409, detail={"integrity_errors": integrity_errors})
    previous = deployment.graph_release_id
    deployment.previous_graph_release_id = previous
    deployment.graph_release_id = graph.id
    deployment.state = DeploymentState.HEALTHY
    deployment.traffic_percentage = payload.traffic_percentage
    deployment.health = {"status": "graph_updated", "reason": payload.reason}
    await record_audit(
        session,
        action="deployment.graph_updated",
        resource_type="deployment",
        resource_id=deployment.id,
        principal=principal,
        before_state={"graph_release_id": previous},
        after_state={"graph_release_id": graph.id, "traffic_percentage": payload.traffic_percentage},
    )
    await session.commit()
    await session.refresh(deployment)
    return deployment
