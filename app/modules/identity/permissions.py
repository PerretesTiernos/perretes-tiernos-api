from app.core.exceptions import ForbiddenError
from app.modules.identity.models import User


def assert_self_or_moderator(actor: User, target_user_id: object) -> None:
    """Ensures the actor is operating on their own user resource or has moderator/superadmin role."""
    if actor.id != target_user_id and actor.system_role not in ("MODERATOR", "SUPERADMIN"):
        raise ForbiddenError("No tienes permiso para acceder o modificar este usuario.")

