from pathlib import Path

from tunegraph.config import Settings
from tunegraph.db.models import GraphRelease, PatchRelease
from tunegraph.security.signing import generate_keypair, sign_bytes
from tunegraph.services.hashing import canonical_json_bytes, sha256_json
from tunegraph.services.integrity import (
    graph_integrity_errors,
    graph_manifest,
    patch_integrity_errors,
)


def signing_settings(tmp_path: Path) -> tuple[Settings, Path]:
    private = tmp_path / "private.pem"
    public = tmp_path / "public.pem"
    generate_keypair(private, public)
    return (
        Settings(
            secret_key="x" * 64,
            signing_private_key_path=private,
            signing_public_key_path=public,
        ),
        private,
    )


def test_graph_integrity_detects_tampering(tmp_path: Path) -> None:
    settings, private = signing_settings(tmp_path)
    manifest = graph_manifest(
        name="support",
        version=1,
        base_model_id="model-1",
        patch_ids=["patch-1"],
        router_config={"mode": "explicit"},
        policy_revision="policy-1",
    )
    graph = GraphRelease(
        organization_id="org-1",
        name="support",
        version=1,
        base_model_id="model-1",
        patch_ids=["patch-1"],
        router_config={"mode": "explicit"},
        policy_revision="policy-1",
        manifest_sha256=sha256_json(manifest),
        signature=sign_bytes(private, canonical_json_bytes(manifest)),
    )
    assert graph_integrity_errors(graph, settings) == []
    graph.patch_ids = ["patch-1", "patch-2"]
    assert graph_integrity_errors(graph, settings)


def test_patch_integrity_detects_record_drift(tmp_path: Path) -> None:
    settings, private = signing_settings(tmp_path)
    manifest = {
        "family": "refund-policy",
        "version": 1,
        "base_model_id": "model-1",
        "capability_id": "capability-1",
        "training_job_id": None,
        "contract_suite_id": "contracts-1",
        "artifact_uri": "oci://registry/refund-policy:v1",
        "artifact_sha256": "a" * 64,
        "rank": 8,
        "risk_tier": "medium",
    }
    patch = PatchRelease(
        organization_id="org-1",
        family="refund-policy",
        version=1,
        base_model_id="model-1",
        capability_id="capability-1",
        training_job_id=None,
        contract_suite_id="contracts-1",
        artifact_uri="oci://registry/refund-policy:v1",
        artifact_sha256="a" * 64,
        signature=sign_bytes(private, canonical_json_bytes(manifest)),
        rank=8,
        risk_tier="medium",
        manifest=manifest,
    )
    assert patch_integrity_errors(patch, settings) == []
    patch.artifact_sha256 = "b" * 64
    errors = patch_integrity_errors(patch, settings)
    assert any("artifact_sha256" in error for error in errors)
