from __future__ import annotations

from tunegraph.domain.enums import Role

ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.PLATFORM_ADMIN: {"*"},
    Role.ORG_ADMIN: {
        "models:*",
        "datasets:*",
        "patches:*",
        "graphs:*",
        "deployments:*",
        "traces:read",
        "users:*",
        "audit:read",
        "removals:*",
    },
    Role.PROJECT_OWNER: {
        "models:read",
        "datasets:*",
        "patches:*",
        "graphs:*",
        "deployments:read",
        "traces:read",
    },
    Role.ML_ENGINEER: {
        "models:read",
        "datasets:read",
        "training:*",
        "patches:create",
        "patches:read",
        "patches:evaluate",
        "graphs:read",
        "traces:read",
    },
    Role.DATA_STEWARD: {"datasets:*", "removals:*", "audit:read"},
    Role.EVALUATOR: {"patches:read", "patches:evaluate", "contracts:*", "traces:read"},
    Role.SECURITY_REVIEWER: {"patches:read", "patches:approve", "audit:read"},
    Role.GOVERNANCE_REVIEWER: {
        "patches:read",
        "patches:approve",
        "graphs:approve",
        "audit:read",
        "removals:approve",
    },
    Role.DEPLOYMENT_OPERATOR: {"patches:read", "graphs:read", "deployments:*"},
    Role.AUDITOR: {"models:read", "datasets:read", "patches:read", "audit:read"},
    Role.INFERENCE_CLIENT: {"inference:invoke", "traces:read:own"},
}


def has_permission(roles: set[Role], permission: str) -> bool:
    for role in roles:
        granted = ROLE_PERMISSIONS.get(role, set())
        if "*" in granted or permission in granted:
            return True
        namespace = permission.split(":", 1)[0] + ":*"
        if namespace in granted:
            return True
    return False
