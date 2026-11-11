from collections import defaultdict
from enum import StrEnum
from time import monotonic

from app.core.exceptions import ForbiddenError, RateLimitExceededError


class SystemRole(StrEnum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    SUPERADMIN = "SUPERADMIN"


class OrganizationRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EDITOR = "EDITOR"
    MEMBER = "MEMBER"


ORGANIZATION_ROLE_PRIORITY: dict[OrganizationRole, int] = {
    OrganizationRole.MEMBER: 10,
    OrganizationRole.EDITOR: 20,
    OrganizationRole.MANAGER: 30,
    OrganizationRole.ADMIN: 40,
    OrganizationRole.OWNER: 50,
}

SYSTEM_ROLE_PRIORITY: dict[SystemRole, int] = {
    SystemRole.USER: 10,
    SystemRole.MODERATOR: 50,
    SystemRole.SUPERADMIN: 100,
}


def has_minimum_org_role(
    actual_role: OrganizationRole | str,
    minimum_role: OrganizationRole,
) -> bool:
    """Returns True if actual_role is equal to or higher than minimum_role in hierarchy."""
    try:
        role_enum = OrganizationRole(actual_role)
    except ValueError:
        return False
    return ORGANIZATION_ROLE_PRIORITY[role_enum] >= ORGANIZATION_ROLE_PRIORITY[minimum_role]


def has_minimum_system_role(
    actual_role: SystemRole | str,
    minimum_role: SystemRole,
) -> bool:
    """Returns True if actual_role meets or exceeds minimum_role in platform hierarchy."""
    try:
        role_enum = SystemRole(actual_role)
    except ValueError:
        return False
    return SYSTEM_ROLE_PRIORITY[role_enum] >= SYSTEM_ROLE_PRIORITY[minimum_role]


def assert_can_assign_org_role(
    actor_role: OrganizationRole | str,
    target_role: OrganizationRole | str,
) -> None:
    """Enforces that only OWNER can assign or modify OWNER/ADMIN roles."""
    actor_enum = OrganizationRole(actor_role)
    target_enum = OrganizationRole(target_role)

    if actor_enum not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        raise ForbiddenError(
            "No tienes permisos para gestionar roles dentro de esta organización."
        )

    if (
        actor_enum == OrganizationRole.ADMIN
        and target_enum in (OrganizationRole.OWNER, OrganizationRole.ADMIN)
    ):
        raise ForbiddenError(
            "Solo un propietario (OWNER) puede asignar o modificar roles OWNER o ADMIN."
        )


class SlidingWindowRateLimiter:
    """Lightweight sliding-window rate limiter for sensitive endpoints."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> None:
        now = monotonic()
        window_start = now - window_seconds
        timestamps = [ts for ts in self._hits[key] if ts > window_start]
        if len(timestamps) >= max_requests:
            self._hits[key] = timestamps
            raise RateLimitExceededError(
                "Has superado el límite de peticiones permitidas. Inténtalo de nuevo más tarde."
            )
        timestamps.append(now)
        self._hits[key] = timestamps

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = SlidingWindowRateLimiter()

