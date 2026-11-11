import uuid

from app.core.exceptions import DomainValidationError, ForbiddenError, NotFoundError
from app.core.permissions import (
    OrganizationRole,
    SystemRole,
    has_minimum_org_role,
    has_minimum_system_role,
)
from app.modules.identity.models import User
from app.modules.organizations.models import MemberStatus, Organization, OrganizationType
from app.modules.organizations.repository import OrganizationRepository


async def require_shelter_editor_permission(
    org_repo: OrganizationRepository,
    *,
    organization_id: uuid.UUID,
    user: User,
    minimum_role: OrganizationRole = OrganizationRole.EDITOR,
) -> Organization:
    """Verifies that `organization_id` is an active SHELTER and `user` has at least `minimum_role`."""
    org = await org_repo.get_by_id(organization_id)
    if org is None or not org.is_active:
        raise NotFoundError("La protectora indicada no existe o no está activa.")

    if org.org_type != OrganizationType.SHELTER.value:
        raise DomainValidationError(
            "Solo las organizaciones de tipo protectora (SHELTER) pueden gestionar animales en adopción."
        )

    if has_minimum_system_role(user.system_role, SystemRole.SUPERADMIN):
        return org

    membership = await org_repo.get_member_by_org_and_user(org.id, user.id)
    if membership is None or membership.status != MemberStatus.ACTIVE.value:
        raise ForbiddenError(
            "No perteneces a esta protectora o no tienes permisos para gestionar sus animales."
        )

    if not has_minimum_org_role(membership.role, minimum_role):
        raise ForbiddenError(
            f"Se requiere al menos el rol {minimum_role.value} en la protectora para realizar esta acción."
        )

    return org


async def can_user_view_draft_animal(
    org_repo: OrganizationRepository,
    *,
    organization_id: uuid.UUID,
    user: User | None,
) -> bool:
    """Returns True if `user` is an active member of `organization_id` or a platform moderator."""
    if user is None:
        return False
    if has_minimum_system_role(user.system_role, SystemRole.MODERATOR):
        return True
    membership = await org_repo.get_member_by_org_and_user(organization_id, user.id)
    return membership is not None and membership.status == MemberStatus.ACTIVE.value

