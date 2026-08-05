from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from tunegraph.api.context import Principal
from tunegraph.config import Settings
from tunegraph.domain.enums import PatchState


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    decision_id: str
    reason: str
    metadata: dict[str, Any]


class PolicyService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def authorize_patch_plan(
        self,
        *,
        principal: Principal,
        environment: str,
        patches: list[dict[str, Any]],
        graph_release_id: str,
    ) -> PolicyDecision:
        input_document = {
            "principal": {
                "subject": principal.subject,
                "organization_id": principal.organization_id,
                "roles": sorted(role.value for role in principal.roles),
            },
            "environment": environment,
            "patches": patches,
            "graph_release_id": graph_release_id,
        }
        if self.settings.opa_url:
            return await self._opa_decision(input_document)
        return self._local_decision(input_document)

    def _local_decision(self, document: dict[str, Any]) -> PolicyDecision:
        patches = document["patches"]
        revoked = [patch["id"] for patch in patches if patch["state"] == PatchState.REVOKED]
        if revoked:
            return PolicyDecision(False, "local-default", f"Revoked patches: {revoked}", {})
        if document["environment"] == "production":
            invalid = [
                patch["id"]
                for patch in patches
                if patch["state"] not in {PatchState.PRODUCTION, PatchState.CANARY}
            ]
            if invalid:
                return PolicyDecision(
                    False,
                    "local-default",
                    f"Patches are not production-approved: {invalid}",
                    {},
                )
        return PolicyDecision(True, "local-default", "Allowed by built-in policy", {})

    async def _opa_decision(self, input_document: dict[str, Any]) -> PolicyDecision:
        endpoint = self.settings.opa_url.rstrip("/") + "/v1/data/tunegraph/allow"
        try:
            async with httpx.AsyncClient(timeout=self.settings.opa_timeout_seconds) as client:
                response = await client.post(endpoint, json={"input": input_document})
                response.raise_for_status()
                result = response.json().get("result", {})
        except (httpx.HTTPError, ValueError) as exc:
            return PolicyDecision(
                False,
                "opa-unavailable",
                "Policy service is unavailable or returned an invalid decision",
                {"error_type": type(exc).__name__},
            )
        if isinstance(result, bool):
            return PolicyDecision(result, "opa", "OPA boolean decision", {})
        return PolicyDecision(
            bool(result.get("allow", False)),
            str(result.get("decision_id", "opa")),
            str(result.get("reason", "OPA policy decision")),
            result,
        )
