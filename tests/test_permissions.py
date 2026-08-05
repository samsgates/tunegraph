from tunegraph.domain.enums import Role
from tunegraph.domain.permissions import has_permission


def test_namespace_permission() -> None:
    assert has_permission({Role.ML_ENGINEER}, "training:create")
    assert not has_permission({Role.ML_ENGINEER}, "deployments:promote")


def test_platform_admin_has_all_permissions() -> None:
    assert has_permission({Role.PLATFORM_ADMIN}, "anything:dangerous")


def test_reviewer_approval_permissions() -> None:
    assert has_permission({Role.SECURITY_REVIEWER}, "patches:approve")
    assert has_permission({Role.GOVERNANCE_REVIEWER}, "graphs:approve")
    assert has_permission({Role.GOVERNANCE_REVIEWER}, "removals:approve")
    assert not has_permission({Role.GOVERNANCE_REVIEWER}, "deployments:promote")
