import pytest

from app.core.exceptions import ForbiddenError, RateLimitExceededError
from app.core.permissions import (
    OrganizationRole,
    SlidingWindowRateLimiter,
    SystemRole,
    assert_can_assign_org_role,
    has_minimum_org_role,
    has_minimum_system_role,
)


def test_organization_role_hierarchy() -> None:
    assert has_minimum_org_role(OrganizationRole.OWNER, OrganizationRole.MEMBER)
    assert has_minimum_org_role(OrganizationRole.ADMIN, OrganizationRole.MANAGER)
    assert has_minimum_org_role(OrganizationRole.MANAGER, OrganizationRole.EDITOR)
    assert not has_minimum_org_role(OrganizationRole.MEMBER, OrganizationRole.EDITOR)
    assert not has_minimum_org_role("INVALID_ROLE", OrganizationRole.MEMBER)


def test_system_role_hierarchy() -> None:
    assert has_minimum_system_role(SystemRole.SUPERADMIN, SystemRole.MODERATOR)
    assert has_minimum_system_role(SystemRole.MODERATOR, SystemRole.USER)
    assert not has_minimum_system_role(SystemRole.USER, SystemRole.MODERATOR)


def test_role_assignment_constraints() -> None:
    assert_can_assign_org_role(OrganizationRole.OWNER, OrganizationRole.OWNER)
    assert_can_assign_org_role(OrganizationRole.OWNER, OrganizationRole.ADMIN)
    assert_can_assign_org_role(OrganizationRole.ADMIN, OrganizationRole.MANAGER)

    with pytest.raises(ForbiddenError):
        assert_can_assign_org_role(OrganizationRole.ADMIN, OrganizationRole.OWNER)

    with pytest.raises(ForbiddenError):
        assert_can_assign_org_role(OrganizationRole.ADMIN, OrganizationRole.ADMIN)

    with pytest.raises(ForbiddenError):
        assert_can_assign_org_role(OrganizationRole.MANAGER, OrganizationRole.MEMBER)


def test_sliding_window_rate_limiter() -> None:
    limiter = SlidingWindowRateLimiter()
    limiter.check("client-1", max_requests=2, window_seconds=60)
    limiter.check("client-1", max_requests=2, window_seconds=60)
    with pytest.raises(RateLimitExceededError):
        limiter.check("client-1", max_requests=2, window_seconds=60)

