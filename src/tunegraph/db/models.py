from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tunegraph.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from tunegraph.domain.enums import (
    DeploymentState,
    JobState,
    PatchState,
    ResourceState,
    RiskTier,
)


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("organization_id", "email"),)


class APIKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BaseModelRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "base_models"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[str] = mapped_column(String(255), nullable=False)
    architecture: Mapped[str] = mapped_column(String(255), nullable=False)
    tokenizer_revision: Mapped[str] = mapped_column(String(255), nullable=False)
    license_id: Mapped[str] = mapped_column(String(255), default="unknown", nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=ResourceState.DRAFT, nullable=False)

    __table_args__ = (UniqueConstraint("organization_id", "name", "revision"),)


class DatasetRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purpose: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    classification: Mapped[str] = mapped_column(String(64), default="internal", nullable=False)
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_days: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    quality_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=ResourceState.DRAFT, nullable=False)

    __table_args__ = (UniqueConstraint("organization_id", "name", "version"),)


class Capability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "capabilities"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (UniqueConstraint("organization_id", "key"),)


class TrainingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "training_jobs"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    base_model_id: Mapped[str] = mapped_column(ForeignKey("base_models.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(32), default="lora", nullable=False)
    specification: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=JobState.QUEUED, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContractSuite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contract_suites"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=ResourceState.DRAFT, nullable=False)

    __table_args__ = (UniqueConstraint("organization_id", "name", "version"),)


class PatchRelease(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "patch_releases"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    family: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    capability_id: Mapped[str] = mapped_column(ForeignKey("capabilities.id"), index=True)
    base_model_id: Mapped[str] = mapped_column(ForeignKey("base_models.id"), index=True)
    training_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("training_jobs.id", ondelete="SET NULL"), index=True
    )
    contract_suite_id: Mapped[str | None] = mapped_column(
        ForeignKey("contract_suites.id", ondelete="SET NULL"), index=True
    )
    artifact_uri: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(16), default=RiskTier.MEDIUM, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=PatchState.DRAFT, nullable=False)
    revoked_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("organization_id", "family", "version"),)


class PatchDependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "patch_dependencies"

    patch_id: Mapped[str] = mapped_column(
        ForeignKey("patch_releases.id", ondelete="CASCADE"), index=True
    )
    required_patch_id: Mapped[str] = mapped_column(
        ForeignKey("patch_releases.id", ondelete="CASCADE"), index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("patch_id", "required_patch_id"),)


class PatchConflict(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "patch_conflicts"

    patch_id: Mapped[str] = mapped_column(
        ForeignKey("patch_releases.id", ondelete="CASCADE"), index=True
    )
    conflicting_patch_id: Mapped[str] = mapped_column(
        ForeignKey("patch_releases.id", ondelete="CASCADE"), index=True
    )
    severity: Mapped[str] = mapped_column(String(32), default="blocking", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    __table_args__ = (UniqueConstraint("patch_id", "conflicting_patch_id"),)


class GraphRelease(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "graph_releases"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    base_model_id: Mapped[str] = mapped_column(ForeignKey("base_models.id"), index=True)
    patch_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    router_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    policy_revision: Mapped[str] = mapped_column(String(255), default="local-default", nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32), default=ResourceState.DRAFT, nullable=False)

    __table_args__ = (UniqueConstraint("organization_id", "name", "version"),)


class Deployment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deployments"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    graph_release_id: Mapped[str] = mapped_column(ForeignKey("graph_releases.id"), index=True)
    previous_graph_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("graph_releases.id", ondelete="SET NULL")
    )
    state: Mapped[str] = mapped_column(
        String(32), default=DeploymentState.DRAFT, nullable=False
    )
    traffic_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    health: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (UniqueConstraint("organization_id", "name", "environment"),)


class InferenceTrace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inference_traces"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    deployment_id: Mapped[str | None] = mapped_column(
        ForeignKey("deployments.id", ondelete="SET NULL"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    graph_release_id: Mapped[str | None] = mapped_column(String(36), index=True)
    patch_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    policy_decision: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validation_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    request_digest: Mapped[str | None] = mapped_column(String(64))
    response_digest: Mapped[str | None] = mapped_column(String(64))
    trace_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RemovalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "removal_requests"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    requested_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="requested", nullable=False)
    impact_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    remediation_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"

    organization_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    action: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64))
    before_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    after_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_patches_org_state", PatchRelease.organization_id, PatchRelease.state)
Index("ix_graphs_org_state", GraphRelease.organization_id, GraphRelease.state)
Index("ix_deployments_org_env", Deployment.organization_id, Deployment.environment)
Index("ix_traces_org_created", InferenceTrace.organization_id, InferenceTrace.created_at)
Index("ix_audit_org_created", AuditEvent.organization_id, AuditEvent.created_at)
