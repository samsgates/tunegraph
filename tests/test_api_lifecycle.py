from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")
pytest.importorskip("structlog")

_db_path = Path(tempfile.mkdtemp()) / "integration.db"
os.environ["TUNEGRAPH_ENVIRONMENT"] = "test"
os.environ["TUNEGRAPH_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"
os.environ["TUNEGRAPH_SECRET_KEY"] = "integration-test-secret-with-at-least-thirty-two-characters"
os.environ["TUNEGRAPH_TRUSTED_HOSTS"] = '["testserver"]'
os.environ["TUNEGRAPH_JSON_LOGS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from tunegraph.db.session import SessionLocal  # noqa: E402
from tunegraph.main import app  # noqa: E402
from tunegraph.services.bootstrap import bootstrap_admin  # noqa: E402


async def _bootstrap() -> None:
    async with SessionLocal() as session:
        await bootstrap_admin(
            session,
            email="admin@example.com",
            password="correct-horse-battery-staple",
            organization_name="Test Organization",
            organization_slug="test-org",
        )


def _auth_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={
            "organization_slug": "test-org",
            "email": "admin@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_complete_patch_graph_and_deployment_lifecycle() -> None:
    with TestClient(app) as client:
        asyncio.run(_bootstrap())
        headers = _auth_headers(client)

        model = client.post(
            "/api/v1/base-models",
            headers=headers,
            json={
                "name": "test-model",
                "provider": "test",
                "source_uri": "oci://models/test",
                "revision": "revision-1",
                "architecture": "decoder-only-transformer",
                "tokenizer_revision": "tokenizer-1",
                "license_id": "test-license",
                "manifest_sha256": "a" * 64,
                "metadata_json": {},
            },
        )
        assert model.status_code == 201, model.text
        model_id = model.json()["id"]
        assert client.post(f"/api/v1/base-models/{model_id}/approve", headers=headers).status_code == 200

        dataset = client.post(
            "/api/v1/datasets",
            headers=headers,
            json={
                "name": "refund-data",
                "version": 1,
                "owner": "test-team",
                "source_uri": "file:///datasets/refund.jsonl",
                "content_sha256": "b" * 64,
                "record_count": 100,
                "metadata_json": {},
            },
        )
        assert dataset.status_code == 201, dataset.text
        dataset_id = dataset.json()["id"]
        validation = client.post(
            f"/api/v1/datasets/{dataset_id}/validate",
            headers=headers,
            json={"minimum_quality_score": 0.8},
        )
        assert validation.status_code == 200
        assert validation.json()["quality_report"]["passed"] is True
        assert client.post(f"/api/v1/datasets/{dataset_id}/approve", headers=headers).status_code == 200

        capability = client.post(
            "/api/v1/capabilities",
            headers=headers,
            json={"key": "support.refunds", "name": "Refunds", "description": "Refund behavior"},
        )
        assert capability.status_code == 201
        capability_id = capability.json()["id"]

        suite = client.post(
            "/api/v1/contract-suites",
            headers=headers,
            json={
                "name": "refund-contracts",
                "version": 1,
                "gates": [
                    {
                        "id": "accuracy",
                        "evaluator": "metric_threshold",
                        "metric": "accuracy",
                        "operator": ">=",
                        "threshold": 0.9,
                        "blocking": True,
                    }
                ],
            },
        )
        assert suite.status_code == 201, suite.text
        suite_id = suite.json()["id"]
        assert client.post(f"/api/v1/contract-suites/{suite_id}/approve", headers=headers).status_code == 200

        patch = client.post(
            "/api/v1/patches",
            headers=headers,
            json={
                "family": "refund-policy",
                "version": 1,
                "capability_id": capability_id,
                "base_model_id": model_id,
                "contract_suite_id": suite_id,
                "artifact_uri": "oci://patches/refund-policy:v1",
                "artifact_sha256": "c" * 64,
                "rank": 8,
                "risk_tier": "medium",
                "manifest": {"owner": "test-team"},
            },
        )
        assert patch.status_code == 201, patch.text
        patch_id = patch.json()["id"]

        for state in ["training", "evaluation_pending"]:
            response = client.post(
                f"/api/v1/patches/{patch_id}/state",
                headers=headers,
                json={"target_state": state},
            )
            assert response.status_code == 200, response.text

        evaluation = client.post(
            f"/api/v1/patches/{patch_id}/evaluate",
            headers=headers,
            json={"metrics": {"accuracy": 0.95}},
        )
        assert evaluation.status_code == 200, evaluation.text
        assert evaluation.json()["passed"] is True

        for state in ["review_pending", "approved", "staged", "canary", "production"]:
            response = client.post(
                f"/api/v1/patches/{patch_id}/state",
                headers=headers,
                json={"target_state": state},
            )
            assert response.status_code == 200, response.text

        graph = client.post(
            "/api/v1/graphs",
            headers=headers,
            json={
                "name": "support-production",
                "version": 1,
                "base_model_id": model_id,
                "patch_ids": [patch_id],
                "router_config": {"mode": "explicit"},
                "policy_revision": "test-policy-v1",
            },
        )
        assert graph.status_code == 201, graph.text
        graph_id = graph.json()["id"]
        assert client.post(f"/api/v1/graphs/{graph_id}/publish", headers=headers).status_code == 200

        deployment = client.post(
            "/api/v1/deployments",
            headers=headers,
            json={
                "name": "support-agent",
                "environment": "production",
                "graph_release_id": graph_id,
                "traffic_percentage": 0,
            },
        )
        assert deployment.status_code == 201, deployment.text
        deployment_id = deployment.json()["id"]
        canary = client.post(
            f"/api/v1/deployments/{deployment_id}/canary",
            headers=headers,
            json={"traffic_percentage": 5},
        )
        assert canary.status_code == 200
        assert canary.json()["traffic_percentage"] == 5
        promoted = client.post(
            f"/api/v1/deployments/{deployment_id}/promote",
            headers=headers,
            json={"traffic_percentage": 100},
        )
        assert promoted.status_code == 200
        assert promoted.json()["state"] == "healthy"

        provenance = client.get(f"/api/v1/patches/{patch_id}/provenance", headers=headers)
        assert provenance.status_code == 200
        assert provenance.json()["artifact_sha256"] == "c" * 64

        audits = client.get("/api/v1/audit-events", headers=headers)
        assert audits.status_code == 200
        assert len(audits.json()) >= 10
