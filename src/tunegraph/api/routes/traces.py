from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from tunegraph.api.deps import PrincipalDep, SessionDep
from tunegraph.db.models import InferenceTrace
from tunegraph.schemas import TraceRead

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceRead])
async def list_traces(principal: PrincipalDep, session: SessionDep) -> list[InferenceTrace]:
    return list(
        (
            await session.execute(
                select(InferenceTrace)
                .where(InferenceTrace.organization_id == principal.organization_id)
                .order_by(InferenceTrace.created_at.desc())
                .limit(200)
            )
        ).scalars()
    )


@router.get("/{trace_id}", response_model=TraceRead)
async def get_trace(trace_id: str, principal: PrincipalDep, session: SessionDep) -> InferenceTrace:
    trace = await session.get(InferenceTrace, trace_id)
    if trace is None or trace.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/{trace_id}/explanation")
async def explain_trace(trace_id: str, principal: PrincipalDep, session: SessionDep) -> dict[str, object]:
    trace = await session.get(InferenceTrace, trace_id)
    if trace is None or trace.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {
        "trace_id": trace.id,
        "request_id": trace.request_id,
        "graph_release_id": trace.graph_release_id,
        "patch_ids": trace.patch_ids,
        "policy_decision": trace.policy_decision,
        "explanation": "Patch participation is exact. Training-record influence is not inferred by this endpoint.",
    }
