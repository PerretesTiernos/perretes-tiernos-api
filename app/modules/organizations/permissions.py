import uuid

from app.core.exceptions import ForbiddenError
from app.core.permissions import (
    OrganizationRole,
    SystemRole,
    has_minimum_org_role,
    has_minimum_system_role,
)
from app.modules.identity.models import User
from app.modules.organizations.models import MemberStatus, OrganizationMember
from app.modules.organizations.repository import OrganizationRepository


async def require_active_org_membership(
    repo: OrganizationRepository,
    *,
    org_id: uuid.UUID,
    user: User,
    minimum_role: OrganizationRole = OrganizationRole.MEMBER,
) -> OrganizationMember | None:
    """Verifies that `user` is an ACTIVE member of `org_id` with at least `minimum_role`
    (or is a platform SUPERADMIN). Raises ForbiddenError (`403`) on unauthorized access.
    """
    if has_minimum_system_role(user.system_role, SystemRole.SUPERADMIN):
        return await repo.get_member_by_org_and_user(org_id, user.id)

    membership = await repo.get_member_by_org_and_user(org_id, user.id)
    if membership is None or membership.status != MemberStatus.ACTIVE.value:
        raise ForbiddenError(
            "No perteneces a esta organización o no tienes acceso a sus recursos internos."
        )

    if not has_minimum_org_role(membership.role, minimum_role):
        raise ForbiddenError(
            f"Esta operación requiere al menos el rol {minimum_role.value} en la organización."
        )

    return membership

