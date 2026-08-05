from __future__ import annotations

from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ResourceState(StrEnum):
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    REVOKED = "revoked"
    FAILED = "failed"


class PatchState(StrEnum):
    DRAFT = "draft"
    TRAINING = "training"
    EVALUATION_PENDING = "evaluation_pending"
    FAILED = "failed"
    CANDIDATE = "candidate"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    STAGED = "staged"
    CANARY = "canary"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    REVOKED = "revoked"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentState(StrEnum):
    DRAFT = "draft"
    DEPLOYING = "deploying"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    STOPPED = "stopped"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Role(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    ORG_ADMIN = "org_admin"
    PROJECT_OWNER = "project_owner"
    ML_ENGINEER = "ml_engineer"
    DATA_STEWARD = "data_steward"
    EVALUATOR = "evaluator"
    SECURITY_REVIEWER = "security_reviewer"
    GOVERNANCE_REVIEWER = "governance_reviewer"
    DEPLOYMENT_OPERATOR = "deployment_operator"
    AUDITOR = "auditor"
    INFERENCE_CLIENT = "inference_client"
