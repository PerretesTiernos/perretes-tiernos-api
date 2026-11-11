import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainValidationError, NotFoundError
from app.modules.animals.repository import AnimalRepository
from app.modules.identity.models import User
from app.modules.moderation.service import AuditService
from app.modules.pets.models import Pet
from app.modules.pets.permissions import assert_pet_owner
from app.modules.pets.repository import PetRepository
from app.modules.pets.schemas import PetCreate, PetUpdate


class PetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PetRepository(db)
        self.animal_repo = AnimalRepository(db)
        self.audit = AuditService(db)

    async def create_pet(self, owner: User, payload: PetCreate) -> Pet:
        species = await self.animal_repo.get_species_by_id(payload.species_id)
        if species is None or not species.is_active:
            raise NotFoundError("La especie seleccionada no existe o no está activa.")

        if payload.breed_id is not None:
            breed = await self.animal_repo.get_breed_by_id(payload.breed_id)
            if breed is None or breed.species_id != species.id:
                raise DomainValidationError(
                    "La raza indicada no existe o no pertenece a la especie seleccionada."
                )

        if payload.origin_animal_id is not None:
            origin = await self.animal_repo.get_animal_by_id(payload.origin_animal_id)
            if origin is None:
                raise NotFoundError("El animal de origen indicado no existe.")

        pet = Pet(
            owner_user_id=owner.id,
            origin_animal_id=payload.origin_animal_id,
            name=payload.name,
            species_id=payload.species_id,
            breed_id=payload.breed_id,
            breed_custom=payload.breed_custom,
            sex=payload.sex.value,
            size=payload.size.value,
            birth_date=payload.birth_date,
            weight_kg=payload.weight_kg,
            is_sterilized=payload.is_sterilized,
            is_microchipped=payload.is_microchipped,
            avatar_url=payload.avatar_url,
            notes=payload.notes,
        )
        self.db.add(pet)
        await self.db.flush()

        await self.audit.log(
            action="pet.created",
            target_type="pet",
            target_id=pet.id,
            actor_user_id=owner.id,
            metadata={
                "name": pet.name,
                "origin_animal_id": str(pet.origin_animal_id)
                if pet.origin_animal_id
                else None,
            },
        )
        await self.db.refresh(pet)
        return pet

    async def list_my_pets(self, owner: User) -> list[Pet]:
        return await self.repo.list_by_owner(owner.id)

    async def get_pet(self, pet_id: uuid.UUID) -> Pet:
        pet = await self.repo.get_by_id(pet_id)
        if pet is None:
            raise NotFoundError("Mascota no encontrada.")
        return pet

    async def update_pet(
        self, actor: User, pet_id: uuid.UUID, payload: PetUpdate
    ) -> Pet:
        pet = await self.get_pet(pet_id)
        assert_pet_owner(actor, pet)

        update_data = payload.model_dump(exclude_unset=True)
        for enum_key in ("sex", "size"):
            if enum_key in update_data and update_data[enum_key] is not None:
                update_data[enum_key] = update_data[enum_key].value

        for field, value in update_data.items():
            setattr(pet, field, value)

        await self.db.flush()
        await self.db.refresh(pet)
        return pet

    async def delete_pet(self, actor: User, pet_id: uuid.UUID) -> None:
        pet = await self.get_pet(pet_id)
        assert_pet_owner(actor, pet)
        pet.deleted_at = datetime.now(UTC)
        await self.audit.log(
            action="pet.deleted",
            target_type="pet",
            target_id=pet.id,
            actor_user_id=actor.id,
        )
        await self.db.flush()

