from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, require_permission
from tunegraph.db.models import ContractSuite
from tunegraph.domain.enums import ResourceState
from tunegraph.schemas import (
    ContractEvaluateRequest,
    ContractEvaluationResult,
    ContractGate,
    ContractSuiteCreate,
    ContractSuiteRead,
)
from tunegraph.services.audit import record_audit
from tunegraph.services.contracts import ContractEngine

router = APIRouter(prefix="/contract-suites", tags=["contracts"])
engine = ContractEngine()


@router.post("", response_model=ContractSuiteRead, status_code=201)
async def create_contract_suite(
    payload: ContractSuiteCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("contracts:*")),
) -> ContractSuite:
    suite = ContractSuite(
        organization_id=principal.organization_id,
        name=payload.name,
        version=payload.version,
        definition={"gates": [gate.model_dump() for gate in payload.gates]},
    )
    session.add(suite)
    await session.flush()
    await record_audit(
        session,
        action="contract_suite.created",
        resource_type="contract_suite",
        resource_id=suite.id,
        principal=principal,
        after_state=suite.definition,
    )
    await session.commit()
    await session.refresh(suite)
    return suite


@router.get("", response_model=list[ContractSuiteRead])
async def list_contract_suites(
    principal: PrincipalDep, session: SessionDep
) -> list[ContractSuite]:
    return list(
        (
            await session.execute(
                select(ContractSuite)
                .where(ContractSuite.organization_id == principal.organization_id)
                .order_by(ContractSuite.created_at.desc())
            )
        ).scalars()
    )


@router.post("/{suite_id}/approve", response_model=ContractSuiteRead)
async def approve_contract_suite(
    suite_id: str,
    session: SessionDep,
    principal: Principal = Depends(require_permission("contracts:*")),
) -> ContractSuite:
    suite = await session.get(ContractSuite, suite_id)
    if suite is None or suite.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Contract suite not found")
    suite.state = ResourceState.APPROVED
    await record_audit(
        session,
        action="contract_suite.approved",
        resource_type="contract_suite",
        resource_id=suite.id,
        principal=principal,
        after_state={"state": suite.state},
    )
    await session.commit()
    await session.refresh(suite)
    return suite


@router.post("/{suite_id}/evaluate", response_model=ContractEvaluationResult)
async def evaluate_contract_suite(
    suite_id: str,
    payload: ContractEvaluateRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> ContractEvaluationResult:
    suite = await session.get(ContractSuite, suite_id)
    if suite is None or suite.organization_id != principal.organization_id:
        raise HTTPException(status_code=404, detail="Contract suite not found")
    gates = [ContractGate.model_validate(item) for item in suite.definition.get("gates", [])]
    return engine.evaluate(gates, payload)
