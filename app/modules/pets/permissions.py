from app.core.exceptions import ForbiddenError
from app.core.permissions import SystemRole, has_minimum_system_role
from app.modules.identity.models import User
from app.modules.pets.models import Pet


def assert_pet_owner(actor: User, pet: Pet) -> None:
    """Ensures only the pet's owner (or a platform SUPERADMIN) can modify or delete the pet."""
    if pet.owner_user_id != actor.id and not has_minimum_system_role(
        actor.system_role, SystemRole.SUPERADMIN
    ):
        raise ForbiddenError("No tienes permiso para modificar o eliminar una mascota ajena.")

