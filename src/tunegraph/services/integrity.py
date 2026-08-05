from __future__ import annotations

from typing import Any

from tunegraph.config import Settings
from tunegraph.db.models import GraphRelease, PatchRelease
from tunegraph.security.signing import verify_bytes
from tunegraph.services.hashing import canonical_json_bytes, sha256_json


def graph_manifest(
    *,
    name: str,
    version: int,
    base_model_id: str,
    patch_ids: list[str],
    router_config: dict[str, Any],
    policy_revision: str,
) -> dict[str, object]:
    return {
        "name": name,
        "version": version,
        "base_model_id": base_model_id,
        "patch_ids": sorted(patch_ids),
        "router_config": router_config,
        "policy_revision": policy_revision,
    }


def graph_manifest_from_record(graph: GraphRelease) -> dict[str, object]:
    return graph_manifest(
        name=graph.name,
        version=graph.version,
        base_model_id=graph.base_model_id,
        patch_ids=graph.patch_ids,
        router_config=graph.router_config,
        policy_revision=graph.policy_revision,
    )


def graph_integrity_errors(graph: GraphRelease, settings: Settings) -> list[str]:
    manifest = graph_manifest_from_record(graph)
    errors: list[str] = []
    if graph.manifest_sha256 != sha256_json(manifest):
        errors.append("Graph manifest hash does not match the stored graph fields")
    if graph.signature:
        if not settings.signing_public_key_path:
            errors.append("Graph is signed but no verification key is configured")
        elif not verify_bytes(
            settings.signing_public_key_path,
            canonical_json_bytes(manifest),
            graph.signature,
        ):
            errors.append("Graph signature verification failed")
    elif settings.is_production:
        errors.append("Production graph releases must be signed")
    return errors


def patch_integrity_errors(patch: PatchRelease, settings: Settings) -> list[str]:
    manifest = patch.manifest
    expected_fields = {
        "family": patch.family,
        "version": patch.version,
        "base_model_id": patch.base_model_id,
        "capability_id": patch.capability_id,
        "training_job_id": patch.training_job_id,
        "contract_suite_id": patch.contract_suite_id,
        "artifact_uri": patch.artifact_uri,
        "artifact_sha256": patch.artifact_sha256,
        "rank": patch.rank,
        "risk_tier": patch.risk_tier,
    }
    errors = [
        f"Patch manifest field {field} does not match the stored patch"
        for field, value in expected_fields.items()
        if manifest.get(field) != value
    ]
    if patch.signature:
        if not settings.signing_public_key_path:
            errors.append("Patch is signed but no verification key is configured")
        elif not verify_bytes(
            settings.signing_public_key_path,
            canonical_json_bytes(manifest),
            patch.signature,
        ):
            errors.append("Patch signature verification failed")
    elif settings.is_production:
        errors.append("Production patch releases must be signed")
    return errors
