from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tunegraph.api.context import Principal
from tunegraph.api.errors import TuneGraphError
from tunegraph.config import Settings
from tunegraph.db.models import Deployment, GraphRelease, InferenceTrace, PatchRelease
from tunegraph.domain.enums import DeploymentState, ResourceState
from tunegraph.schemas import ChatCompletionRequest
from tunegraph.services.graph import GraphResolver
from tunegraph.services.hashing import redact_digest
from tunegraph.services.integrity import graph_integrity_errors
from tunegraph.services.policy import PolicyService


@dataclass(frozen=True, slots=True)
class PatchPlan:
    request_id: str
    deployment_id: str | None
    graph_release_id: str
    base_model_id: str
    patch_ids: list[str]
    patch_models: list[str]
    policy_decision: dict[str, Any]
    environment: str


class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.graph_resolver = GraphResolver()
        self.policy = PolicyService(settings)

    async def resolve_plan(
        self,
        session: AsyncSession,
        principal: Principal,
        request: ChatCompletionRequest,
    ) -> PatchPlan:
        request_id = "req_" + uuid.uuid4().hex
        deployment: Deployment | None = None
        graph: GraphRelease | None = None
        environment = self.settings.environment

        if request.tunegraph.deployment:
            deployment = await self._resolve_deployment(
                session, principal.organization_id, request.tunegraph.deployment
            )
            if deployment is None:
                raise TuneGraphError("DEPLOYMENT_NOT_FOUND", "Deployment was not found", status_code=404)
            if deployment.state not in {DeploymentState.HEALTHY, DeploymentState.DEGRADED}:
                raise TuneGraphError(
                    "DEPLOYMENT_NOT_READY",
                    f"Deployment is in state {deployment.state}",
                    status_code=409,
                )
            graph = await session.get(GraphRelease, deployment.graph_release_id)
            environment = deployment.environment
        elif request.tunegraph.graph_release_id:
            graph = await session.get(GraphRelease, request.tunegraph.graph_release_id)
        else:
            deployment = await self._resolve_deployment(
                session, principal.organization_id, request.model, allow_ambiguous=False
            )
            if deployment:
                graph = await session.get(GraphRelease, deployment.graph_release_id)
                environment = deployment.environment

        if graph is None or graph.organization_id != principal.organization_id:
            raise TuneGraphError(
                "GRAPH_NOT_FOUND",
                "A valid graph release or deployment is required",
                status_code=404,
            )

        if graph.state != ResourceState.APPROVED:
            raise TuneGraphError(
                "GRAPH_NOT_PUBLISHED",
                "Inference requires a published graph release",
                status_code=409,
            )

        integrity_errors = graph_integrity_errors(graph, self.settings)
        if integrity_errors:
            raise TuneGraphError(
                "GRAPH_INTEGRITY_FAILED",
                "Graph release integrity verification failed",
                status_code=409,
                details={"errors": integrity_errors},
            )

        requested_patch_ids = request.tunegraph.patch_ids or graph.patch_ids
        if not set(requested_patch_ids).issubset(set(graph.patch_ids)):
            raise TuneGraphError(
                "PATCH_NOT_IN_GRAPH",
                "Explicit patches must belong to the selected graph release",
                status_code=403,
            )
        validation = await self.graph_resolver.validate(
            session,
            organization_id=principal.organization_id,
            base_model_id=graph.base_model_id,
            patch_ids=requested_patch_ids,
            settings=self.settings,
        )
        if not validation.valid:
            raise TuneGraphError(
                "PATCH_PLAN_INVALID",
                "The requested patch plan is invalid",
                status_code=409,
                details={"errors": validation.errors, "warnings": validation.warnings},
            )
        if not set(validation.resolved_patch_ids).issubset(set(graph.patch_ids)):
            raise TuneGraphError(
                "GRAPH_DEPENDENCY_DRIFT",
                "Patch dependencies changed after the graph release was signed",
                status_code=409,
            )

        patches = (
            await session.execute(
                select(PatchRelease).where(PatchRelease.id.in_(validation.resolved_patch_ids))
            )
        ).scalars().all()
        patches_by_id = {patch.id: patch for patch in patches}
        ordered_patches = [patches_by_id[patch_id] for patch_id in validation.resolved_patch_ids]
        policy = await self.policy.authorize_patch_plan(
            principal=principal,
            environment=environment,
            patches=[{"id": p.id, "state": p.state, "risk_tier": p.risk_tier} for p in ordered_patches],
            graph_release_id=graph.id,
        )
        if not policy.allowed:
            raise TuneGraphError(
                "POLICY_DENIED",
                policy.reason,
                status_code=403,
                details=policy.metadata,
            )

        return PatchPlan(
            request_id=request_id,
            deployment_id=deployment.id if deployment else None,
            graph_release_id=graph.id,
            base_model_id=graph.base_model_id,
            patch_ids=validation.resolved_patch_ids,
            patch_models=[f"{p.family}:v{p.version}" for p in ordered_patches],
            policy_decision={
                "allowed": policy.allowed,
                "decision_id": policy.decision_id,
                "reason": policy.reason,
            },
            environment=environment,
        )

    async def _resolve_deployment(
        self,
        session: AsyncSession,
        organization_id: str,
        identifier: str,
        *,
        allow_ambiguous: bool = False,
    ) -> Deployment | None:
        deployment = await session.get(Deployment, identifier)
        if deployment is not None:
            return deployment if deployment.organization_id == organization_id else None
        matches = list(
            (
                await session.execute(
                    select(Deployment).where(
                        Deployment.organization_id == organization_id,
                        Deployment.name == identifier,
                    )
                )
            ).scalars()
        )
        if len(matches) > 1 and not allow_ambiguous:
            raise TuneGraphError(
                "DEPLOYMENT_AMBIGUOUS",
                "Deployment name exists in multiple environments. Use the deployment ID.",
                status_code=409,
            )
        return matches[0] if matches else None

    async def invoke(
        self,
        session: AsyncSession,
        principal: Principal,
        request: ChatCompletionRequest,
    ) -> tuple[dict[str, Any], PatchPlan]:
        plan = await self.resolve_plan(session, principal, request)
        started = time.perf_counter()
        payload = request.model_dump(exclude={"tunegraph", "extra_body"}, exclude_none=True)
        payload.update(request.extra_body)
        payload["model"] = request.model
        # vLLM selects one LoRA by model name. TuneGraph records the full plan and can use
        # pre-approved merged compositions for multiple patches. For a single patch, route it directly.
        if len(plan.patch_models) == 1:
            payload["model"] = plan.patch_models[0]
        payload["stream"] = False

        headers: dict[str, str] = {"X-TuneGraph-Request-ID": plan.request_id}
        if self.settings.inference_backend_api_key:
            headers["Authorization"] = (
                "Bearer " + self.settings.inference_backend_api_key.get_secret_value()
            )

        status_code = 502
        error_code: str | None = None
        response_json: dict[str, Any]
        try:
            async with httpx.AsyncClient(timeout=self.settings.inference_timeout_seconds) as client:
                response = await client.post(
                    self.settings.inference_backend_url.rstrip("/") + "/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
            status_code = response.status_code
            if response.status_code >= 400:
                error_code = "INFERENCE_BACKEND_ERROR"
                raise TuneGraphError(
                    error_code,
                    "Inference backend rejected the request",
                    status_code=502,
                    details={"backend_status": response.status_code},
                )
            response_json = response.json()
        except httpx.HTTPError as exc:
            error_code = "INFERENCE_BACKEND_UNAVAILABLE"
            raise TuneGraphError(error_code, "Inference backend is unavailable", status_code=503) from exc
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            trace = InferenceTrace(
                organization_id=principal.organization_id,
                deployment_id=plan.deployment_id,
                request_id=plan.request_id,
                graph_release_id=plan.graph_release_id,
                patch_ids=plan.patch_ids,
                policy_decision=plan.policy_decision,
                latency_ms=latency_ms,
                token_usage={},
                validation_result={},
                status_code=status_code,
                error_code=error_code,
                request_digest=redact_digest(request.model_dump()),
                response_digest=None,
                trace_metadata={"environment": plan.environment},
            )
            session.add(trace)
            await session.commit()

        usage = response_json.get("usage", {})
        trace.token_usage = usage
        trace.response_digest = redact_digest(response_json)
        await session.commit()
        response_json.setdefault("tunegraph", {})
        response_json["tunegraph"].update(
            {
                "request_id": plan.request_id,
                "graph_release_id": plan.graph_release_id,
                "patch_ids": plan.patch_ids,
                "policy_decision": plan.policy_decision,
            }
        )
        return response_json, plan
