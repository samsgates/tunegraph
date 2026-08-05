from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from tunegraph.domain.enums import DeploymentState, JobState, PatchState, ResourceState, RiskTier, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    items: list[Any]
    next_cursor: str | None = None


class LoginRequest(BaseModel):
    organization_slug: str = Field(default="default", min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    full_name: str = Field(default="", max_length=255)
    roles: list[Role] = Field(default_factory=lambda: [Role.ML_ENGINEER])


class UserRead(ORMModel):
    id: str
    organization_id: str
    email: EmailStr
    full_name: str
    roles: list[str]
    is_active: bool
    created_at: datetime


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    roles: list[Role]
    expires_at: datetime | None = None


class APIKeyCreated(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    expires_at: datetime | None


class BaseModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=255)
    source_uri: str = Field(min_length=1, max_length=2048)
    revision: str = Field(min_length=1, max_length=255)
    architecture: str = Field(min_length=1, max_length=255)
    tokenizer_revision: str = Field(min_length=1, max_length=255)
    license_id: str = Field(default="unknown", max_length=255)
    manifest_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class BaseModelRead(ORMModel):
    id: str
    organization_id: str
    name: str
    provider: str
    source_uri: str
    revision: str
    architecture: str
    tokenizer_revision: str
    license_id: str
    manifest_sha256: str
    metadata_json: dict[str, Any]
    state: str
    created_at: datetime
    updated_at: datetime


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(ge=1)
    owner: str = Field(min_length=1, max_length=255)
    source_uri: str = Field(min_length=1, max_length=2048)
    content_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    record_count: int = Field(default=0, ge=0)
    purpose: list[str] = Field(default_factory=lambda: ["supervised-fine-tuning"])
    classification: str = Field(default="internal", max_length=64)
    contains_personal_data: bool = False
    retention_days: int | None = Field(default=None, ge=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DatasetRead(ORMModel):
    id: str
    organization_id: str
    name: str
    version: int
    owner: str
    source_uri: str
    content_sha256: str
    record_count: int
    purpose: list[str]
    classification: str
    contains_personal_data: bool
    retention_days: int | None
    metadata_json: dict[str, Any]
    quality_report: dict[str, Any]
    state: str
    created_at: datetime
    updated_at: datetime


class DatasetValidationRequest(BaseModel):
    checks: list[str] = Field(
        default_factory=lambda: ["schema", "duplicates", "secrets", "quality"]
    )
    minimum_quality_score: float = Field(default=0.8, ge=0, le=1)


class CapabilityCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,254}$")
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CapabilityRead(ORMModel):
    id: str
    organization_id: str
    key: str
    name: str
    description: str
    metadata_json: dict[str, Any]
    created_at: datetime


class TrainingJobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_model_id: str
    dataset_id: str
    capability_id: str
    method: Literal["lora", "qlora", "dora"] = "lora"
    specification: dict[str, Any] = Field(default_factory=dict)


class TrainingJobRead(ORMModel):
    id: str
    organization_id: str
    name: str
    base_model_id: str
    dataset_id: str
    capability_id: str
    method: str
    specification: dict[str, Any]
    state: str
    progress: float
    artifact_uri: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class ContractGate(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    evaluator: Literal[
        "metric_threshold", "json_schema", "regex", "required_fields", "latency"
    ]
    metric: str | None = None
    operator: Literal[">=", ">", "<=", "<", "=", "!="] = ">="
    threshold: float | int | str | None = None
    blocking: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class ContractSuiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(ge=1)
    gates: list[ContractGate] = Field(min_length=1)


class ContractSuiteRead(ORMModel):
    id: str
    organization_id: str
    name: str
    version: int
    definition: dict[str, Any]
    state: str
    created_at: datetime


class ContractEvaluateRequest(BaseModel):
    metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    output: Any = None
    latency_ms: float | None = Field(default=None, ge=0)


class ContractGateResult(BaseModel):
    id: str
    passed: bool
    blocking: bool
    observed: Any = None
    message: str


class ContractEvaluationResult(BaseModel):
    passed: bool
    results: list[ContractGateResult]


class PatchCreate(BaseModel):
    family: str = Field(min_length=1, max_length=255)
    version: int = Field(ge=1)
    capability_id: str
    base_model_id: str
    training_job_id: str | None = None
    contract_suite_id: str | None = None
    artifact_uri: str = Field(min_length=1, max_length=2048)
    artifact_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    signature: str | None = None
    rank: int = Field(default=8, ge=1, le=1024)
    risk_tier: RiskTier = RiskTier.MEDIUM
    manifest: dict[str, Any] = Field(default_factory=dict)


class PatchRead(ORMModel):
    id: str
    organization_id: str
    family: str
    version: int
    capability_id: str
    base_model_id: str
    training_job_id: str | None
    contract_suite_id: str | None
    artifact_uri: str
    artifact_sha256: str
    signature: str | None
    rank: int
    risk_tier: str
    manifest: dict[str, Any]
    evaluation_summary: dict[str, Any]
    state: str
    revoked_reason: str | None
    created_at: datetime
    updated_at: datetime


class PatchStateChange(BaseModel):
    target_state: PatchState
    reason: str = Field(default="", max_length=5000)


class PatchDependencyCreate(BaseModel):
    required_patch_id: str
    required: bool = True


class PatchConflictCreate(BaseModel):
    conflicting_patch_id: str
    severity: Literal["informational", "warning", "review_required", "blocking"] = "blocking"
    reason: str = Field(default="", max_length=5000)


class GraphCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(ge=1)
    base_model_id: str
    patch_ids: list[str] = Field(min_length=1, max_length=64)
    router_config: dict[str, Any] = Field(default_factory=dict)
    policy_revision: str = Field(default="local-default", max_length=255)

    @field_validator("patch_ids")
    @classmethod
    def unique_patch_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("patch_ids must be unique")
        return value


class GraphRead(ORMModel):
    id: str
    organization_id: str
    name: str
    version: int
    base_model_id: str
    patch_ids: list[str]
    router_config: dict[str, Any]
    policy_revision: str
    manifest_sha256: str
    signature: str | None
    state: str
    created_at: datetime


class GraphValidationResult(BaseModel):
    valid: bool
    resolved_patch_ids: list[str]
    errors: list[str]
    warnings: list[str]


class DeploymentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    environment: Literal["development", "staging", "production"]
    graph_release_id: str
    traffic_percentage: int = Field(default=0, ge=0, le=100)
    configuration: dict[str, Any] = Field(default_factory=dict)


class DeploymentRead(ORMModel):
    id: str
    organization_id: str
    name: str
    environment: str
    graph_release_id: str
    previous_graph_release_id: str | None
    state: str
    traffic_percentage: int
    configuration: dict[str, Any]
    health: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DeploymentAction(BaseModel):
    traffic_percentage: int | None = Field(default=None, ge=0, le=100)
    reason: str = Field(default="", max_length=5000)


class DeploymentGraphUpdate(BaseModel):
    graph_release_id: str
    traffic_percentage: int = Field(default=5, ge=0, le=100)
    reason: str = Field(default="", max_length=5000)


class TuneGraphInferenceOptions(BaseModel):
    deployment: str | None = None
    graph_release_id: str | None = None
    profile: str | None = None
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    patch_ids: list[str] = Field(default_factory=list, max_length=32)
    trace_level: Literal["none", "minimal", "standard", "debug"] = "standard"


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    tunegraph: TuneGraphInferenceOptions = Field(default_factory=TuneGraphInferenceOptions)
    extra_body: dict[str, Any] = Field(default_factory=dict)


class TraceRead(ORMModel):
    id: str
    organization_id: str
    deployment_id: str | None
    request_id: str
    graph_release_id: str | None
    patch_ids: list[str]
    policy_decision: dict[str, Any]
    latency_ms: float
    token_usage: dict[str, Any]
    validation_result: dict[str, Any]
    status_code: int
    error_code: str | None
    trace_metadata: dict[str, Any]
    created_at: datetime


class RemovalRequestCreate(BaseModel):
    target_type: Literal["record", "dataset", "source", "tenant", "patch"]
    target_id: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=10000)


class RemovalRequestRead(ORMModel):
    id: str
    organization_id: str
    requested_by_user_id: str | None
    target_type: str
    target_id: str
    reason: str
    state: str
    impact_report: dict[str, Any]
    remediation_report: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: str
