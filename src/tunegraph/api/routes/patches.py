from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, SettingsDep, require_permission
from tunegraph.db.models import (
    BaseModelRecord,
    Capability,
    ContractSuite,
    PatchConflict,
    PatchDependency,
    PatchRelease,
    TrainingJob,
)
from tunegraph.domain.enums import PatchState, ResourceState
from tunegraph.domain.permissions import has_permission
from tunegraph.domain.state_machine import ensure_patch_transition
from tunegraph.schemas import (
    ContractEvaluateRequest,
    ContractEvaluationResult,
    ContractGate,
    PatchConflictCreate,
    PatchCreate,
    PatchDependencyCreate,
    PatchRead,
    PatchStateChange,
)
from tunegraph.security.signing import verify_bytes
from tunegraph.services.audit import record_audit
from tunegraph.services.contracts import ContractEngine
from tunegraph.services.hashing import canonical_json_bytes

router = APIRouter(prefix="/patches", tags=["patches"])
contract_engine = ContractEngine()


@router.post("", response_model=PatchRead, status_code=201)
async def create_patch(
    payload: PatchCreate,
    session: SessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("patches:create")),
) -> PatchRelease:
    base_model = await session.get(BaseModelRecord, payload.base_model_id)
    capability = await session.get(Capability, payload.capability_id)
    if base_model is None or capability is None:
        raise HTTPException(status_code=404, detail="Base model or capability not found")
    if (
        base_model.organization_id != principal.organization_id
        or capability.organization_id != principal.organization_id
    ):
        raise HTTPException(status_code=404, detail="Base model or capability not found")
    if base_model.state != ResourceState.APPROVED:
        raise HTTPException(status_code=409, detail="Base model must be approved")
    if payload.training_job_id:
        job = await session.get(TrainingJob, payload.training_job_id)
        if job is None or job.organization_id != principal.organization_id:
            raise HTTPException(status_code=404, detail="Training job not found")
    if payload.contract_suite_id:
        suite = await session.get(ContractSuite, payload.contract_suite_id)
        if suite is None or suite.organization_id != principal.organization_id:
            raise HTTPException(status_code=404, detail="Contract suite not found")
        if suite.state != ResourceState.APPROVED:
            raise HTTPException(status_code=409, detail="Contract suite must be approved")

    manifest = {
        **payload.manifest,
        "family": payload.family,
        "version": payload.version,
        "base_model_id": payload.base_model_id,
        "capability_id": payload.capability_id,
        "training_job_id": payload.training_job_id,
        "contract_suite_id": payload.contract_suite_id,
        "artifact_uri": payload.artifact_uri,
        "artifact_sha256": payload.artifact_sha256,
        "rank": payload.rank,
        "risk_tier": payload.risk_tier,
    }
    if settings.signing_public_key_path and payload.signature:
        if not verify_bytes(
            settings.signing_public_key_path,
            canonical_json_bytes(manifest),
            payload.signature,
        ):
            raise HTTPException(status_code=422, detail="Patch manifest signature is invalid")
    elif settings.is_production and not payload.signature:
        raise HTTPException(status_code=422, detail="Production requires signed patch manifests")

    patch = PatchRelease(
        organization_id=principal.organization_id,
        **payload.model_dump(exclude={"manifest"}),
        manifest=manifest,
    )
    session.add(patch)
    await session.flush()
    await record_audit(
        session,
        action="patch.created",
        resource_type="patch",
        resource_id=patch.id,
        principal=principal,
        after_state=manifest,
    )
    await session.commit()
    await session.refresh(patch)
    return patch


@router.get("", response_model=list[PatchRead])
async def list_patches(principal: PrincipalDep, session: SessionDep) -> list[PatchRelease]:
    return list(
        (
            await session.execute(
                select(PatchRelease)
                .where(PatchRelease.organization_id == principal.organization_id)
                .order_by(PatchRelease.created_at.desc())
            )
        ).scalars()
    )


@router.get("/{patch_id}", response_model=PatchRead)
async def get_patch(patch_id: str, principal: PrincipalDep, session: SessionDep) -> PatchRelease:
    patch = await session.get(PatchRelease, patch_id)
    if patch is None or patch.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post("/{patch_id}/state", response_model=PatchRead)
async def change_patch_state(
    patch_id: str,
    payload: PatchStateChange,
    session: SessionDep,
    principal: PrincipalDep,
) -> PatchRelease:
    required_permission = (
        "patches:approve"
        if payload.target_state == PatchState.APPROVED
        else "patches:*"
    )
    if not has_permission(set(principal.roles), required_permission):
        raise HTTPException(status_code=403, detail=f"Missing permission: {required_permission}")
    patch = await session.get(PatchRelease, patch_id)
    if patch is None or patch.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Patch not found")
    current = PatchState(patch.state)
    try:
        ensure_patch_transition(current, payload.target_state)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    before = {"state": patch.state}
    patch.state = payload.target_state
    if payload.target_state == PatchState.REVOKED:
        patch.revoked_reason = payload.reason or "Revoked by operator"
    await record_audit(
        session,
        action=f"patch.state.{payload.target_state}",
        resource_type="patch",
        resource_id=patch.id,
        principal=principal,
        before_state=before,
        after_state={"state": patch.state, "reason": payload.reason},
    )
    await session.commit()
    await session.refresh(patch)
    return patch


@router.post("/{patch_id}/dependencies", status_code=201)
async def add_dependency(
    patch_id: str,
    payload: PatchDependencyCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("patches:*")),
) -> dict[str, str | bool]:
    patch = await session.get(PatchRelease, patch_id)
    required = await session.get(PatchRelease, payload.required_patch_id)
    if (
        patch is None
        or required is None
        or patch.organization_id != principal.organization_id
        or required.organization_id != principal.organization_id
    ):
        raise HTTPException(status_code=404, detail="Patch not found")
    if PatchState(patch.state) not in {
        PatchState.DRAFT,
        PatchState.EVALUATION_PENDING,
        PatchState.CANDIDATE,
    }:
        raise HTTPException(
            status_code=409,
            detail="Patch topology is immutable after review begins",
        )
    dependency = PatchDependency(
        patch_id=patch.id,
        required_patch_id=required.id,
        required=payload.required,
    )
    session.add(dependency)
    await session.commit()
    return {"patch_id": patch.id, "required_patch_id": required.id, "required": payload.required}


@router.post("/{patch_id}/conflicts", status_code=201)
async def add_conflict(
    patch_id: str,
    payload: PatchConflictCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("patches:*")),
) -> dict[str, str]:
    patch = await session.get(PatchRelease, patch_id)
    conflicting = await session.get(PatchRelease, payload.conflicting_patch_id)
    if (
        patch is None
        or conflicting is None
        or patch.organization_id != principal.organization_id
        or conflicting.organization_id != principal.organization_id
    ):
        raise HTTPException(status_code=404, detail="Patch not found")
    if PatchState(patch.state) not in {
        PatchState.DRAFT,
        PatchState.EVALUATION_PENDING,
        PatchState.CANDIDATE,
    }:
        raise HTTPException(
            status_code=409,
            detail="Patch topology is immutable after review begins",
        )
    conflict = PatchConflict(
        patch_id=patch.id,
        conflicting_patch_id=conflicting.id,
        severity=payload.severity,
        reason=payload.reason,
    )
    session.add(conflict)
    await session.commit()
    return {
        "patch_id": patch.id,
        "conflicting_patch_id": conflicting.id,
        "severity": payload.severity,
    }


@router.post("/{patch_id}/evaluate", response_model=ContractEvaluationResult)
async def evaluate_patch(
    patch_id: str,
    payload: ContractEvaluateRequest,
    session: SessionDep,
    principal: Principal = Depends(require_permission("patches:evaluate")),
) -> ContractEvaluationResult:
    patch = await session.get(PatchRelease, patch_id)
    if patch is None or patch.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Patch not found")
    if PatchState(patch.state) != PatchState.EVALUATION_PENDING:
        raise HTTPException(
            status_code=409,
            detail="Patch must be in evaluation_pending state before evaluation",
        )
    if patch.contract_suite_id is None:
        raise HTTPException(status_code=409, detail="Patch has no contract suite")
    suite = await session.get(ContractSuite, patch.contract_suite_id)
    if suite is None or suite.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Contract suite not found")
    if suite.state != ResourceState.APPROVED:
        raise HTTPException(status_code=409, detail="Contract suite must be approved")
    gates = [ContractGate.model_validate(item) for item in suite.definition.get("gates", [])]
    result = contract_engine.evaluate(gates, payload)
    patch.evaluation_summary = result.model_dump(mode="json")
    patch.state = PatchState.CANDIDATE if result.passed else PatchState.FAILED
    await record_audit(
        session,
        action="patch.evaluated",
        resource_type="patch",
        resource_id=patch.id,
        principal=principal,
        after_state={"state": patch.state, "evaluation": patch.evaluation_summary},
    )
    await session.commit()
    return result


@router.get("/{patch_id}/provenance")
async def patch_provenance(
    patch_id: str, principal: PrincipalDep, session: SessionDep
) -> dict[str, object]:
    patch = await session.get(PatchRelease, patch_id)
    if patch is None or patch.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Patch not found")
    job = await session.get(TrainingJob, patch.training_job_id) if patch.training_job_id else None
    return {
        "patch_id": patch.id,
        "family": patch.family,
        "version": patch.version,
        "base_model_id": patch.base_model_id,
        "capability_id": patch.capability_id,
        "training_job_id": patch.training_job_id,
        "dataset_id": job.dataset_id if job else None,
        "artifact_uri": patch.artifact_uri,
        "artifact_sha256": patch.artifact_sha256,
        "manifest": patch.manifest,
        "limitations": ["Lineage records inclusion and transformation history, not exact causal influence."],
    }


@router.get("/{patch_id}/diff/{other_patch_id}")
async def diff_patches(
    patch_id: str, other_patch_id: str, principal: PrincipalDep, session: SessionDep
) -> dict[str, object]:
    left = await session.get(PatchRelease, patch_id)
    right = await session.get(PatchRelease, other_patch_id)
    if (
        left is None
        or right is None
        or left.organization_id != principal.organization_id
        or right.organization_id != principal.organization_id
    ):
        raise HTTPException(status_code=404, detail="Patch not found")
    fields = [
        "version", "base_model_id", "capability_id", "training_job_id",
        "contract_suite_id", "artifact_sha256", "rank", "risk_tier", "state"
    ]
    changes = {
        field: {"from": getattr(left, field), "to": getattr(right, field)}
        for field in fields
        if getattr(left, field) != getattr(right, field)
    }
    return {
        "from_patch_id": left.id,
        "to_patch_id": right.id,
        "changes": changes,
        "evaluation_from": left.evaluation_summary,
        "evaluation_to": right.evaluation_summary,
    }
