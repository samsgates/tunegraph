from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, SettingsDep, require_permission
from tunegraph.db.models import BaseModelRecord, GraphRelease
from tunegraph.domain.enums import ResourceState
from tunegraph.domain.permissions import has_permission
from tunegraph.schemas import GraphCreate, GraphRead, GraphValidationResult
from tunegraph.security.signing import sign_bytes
from tunegraph.services.audit import record_audit
from tunegraph.services.graph import GraphResolver
from tunegraph.services.hashing import canonical_json_bytes, sha256_json
from tunegraph.services.integrity import graph_integrity_errors, graph_manifest

router = APIRouter(prefix="/graphs", tags=["graphs"])
resolver = GraphResolver()


@router.post("", response_model=GraphRead, status_code=201)
async def create_graph(
    payload: GraphCreate,
    session: SessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("graphs:*")),
) -> GraphRelease:
    base_model = await session.get(BaseModelRecord, payload.base_model_id)
    if base_model is None or base_model.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Base model not found")
    validation = await resolver.validate(
        session,
        organization_id=principal.organization_id,
        base_model_id=payload.base_model_id,
        patch_ids=payload.patch_ids,
        settings=settings,
    )
    if not validation.valid:
        raise HTTPException(status_code=409, detail={"errors": validation.errors, "warnings": validation.warnings})
    manifest = graph_manifest(
        name=payload.name,
        version=payload.version,
        base_model_id=payload.base_model_id,
        patch_ids=validation.resolved_patch_ids,
        router_config=payload.router_config,
        policy_revision=payload.policy_revision,
    )
    signature = None
    if settings.signing_private_key_path:
        signature = sign_bytes(settings.signing_private_key_path, canonical_json_bytes(manifest))
    graph = GraphRelease(
        organization_id=principal.organization_id,
        name=payload.name,
        version=payload.version,
        base_model_id=payload.base_model_id,
        patch_ids=validation.resolved_patch_ids,
        router_config=payload.router_config,
        policy_revision=payload.policy_revision,
        manifest_sha256=sha256_json(manifest),
        signature=signature,
    )
    session.add(graph)
    await session.flush()
    await record_audit(
        session,
        action="graph.created",
        resource_type="graph_release",
        resource_id=graph.id,
        principal=principal,
        after_state=manifest,
    )
    await session.commit()
    await session.refresh(graph)
    return graph


@router.get("", response_model=list[GraphRead])
async def list_graphs(principal: PrincipalDep, session: SessionDep) -> list[GraphRelease]:
    return list(
        (
            await session.execute(
                select(GraphRelease)
                .where(GraphRelease.organization_id == principal.organization_id)
                .order_by(GraphRelease.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{graph_id}", response_model=GraphRead)
async def get_graph(graph_id: str, principal: PrincipalDep, session: SessionDep) -> GraphRelease:
    graph = await session.get(GraphRelease, graph_id)
    if graph is None or graph.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Graph release not found")
    return graph


@router.post("/{graph_id}/validate", response_model=GraphValidationResult)
async def validate_graph(
    graph_id: str, principal: PrincipalDep, session: SessionDep, settings: SettingsDep
) -> GraphValidationResult:
    graph = await session.get(GraphRelease, graph_id)
    if graph is None or graph.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Graph release not found")
    return await resolver.validate(
        session,
        organization_id=principal.organization_id,
        base_model_id=graph.base_model_id,
        patch_ids=graph.patch_ids,
        settings=settings,
    )


@router.post("/{graph_id}/publish", response_model=GraphRead)
async def publish_graph(
    graph_id: str,
    session: SessionDep,
    settings: SettingsDep,
    principal: PrincipalDep,
) -> GraphRelease:
    if not has_permission(set(principal.roles), "graphs:approve"):
        raise HTTPException(status_code=403, detail="Missing permission: graphs:approve")
    graph = await session.get(GraphRelease, graph_id)
    if graph is None or graph.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Graph release not found")
    validation = await resolver.validate(
        session,
        organization_id=principal.organization_id,
        base_model_id=graph.base_model_id,
        patch_ids=graph.patch_ids,
        settings=settings,
    )
    if not validation.valid:
        raise HTTPException(status_code=409, detail=validation.model_dump())
    if validation.resolved_patch_ids != sorted(graph.patch_ids):
        raise HTTPException(
            status_code=409,
            detail="Patch dependencies changed. Create a new graph release.",
        )
    integrity_errors = graph_integrity_errors(graph, settings)
    if integrity_errors:
        raise HTTPException(status_code=409, detail={"integrity_errors": integrity_errors})
    graph.state = ResourceState.APPROVED
    await record_audit(
        session,
        action="graph.published",
        resource_type="graph_release",
        resource_id=graph.id,
        principal=principal,
        after_state={"state": graph.state, "patch_ids": graph.patch_ids},
    )
    await session.commit()
    await session.refresh(graph)
    return graph
