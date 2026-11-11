import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    ForbiddenError,
    NotFoundError,
)
from app.core.permissions import OrganizationRole
from app.modules.animals.models import (
    Animal,
    AnimalBreed,
    AnimalCatalogTrait,
    AnimalCompatibility,
    AnimalHealth,
    AnimalLocation,
    AnimalMedia,
    AnimalProfile,
    AnimalSpecies,
    AnimalStatus,
    AnimalStatusHistory,
    ShelterAnimal,
)
from app.modules.animals.permissions import (
    can_user_view_draft_animal,
    require_shelter_editor_permission,
)
from app.modules.animals.repository import AnimalRepository
from app.modules.animals.schemas import (
    AnimalCreate,
    AnimalMediaCreate,
    AnimalStatusTransitionInput,
    AnimalUpdate,
    BreedCreate,
    CatalogTraitCreate,
    SpeciesCreate,
)
from app.modules.identity.models import User
from app.modules.moderation.service import AuditService
from app.modules.organizations.repository import OrganizationRepository


class AnimalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnimalRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.audit = AuditService(db)

    # =========================================================================
    # Catalogs
    # =========================================================================
    async def list_species(self) -> list[AnimalSpecies]:
        return await self.repo.list_species(active_only=True)

    async def create_species(self, actor: User, payload: SpeciesCreate) -> AnimalSpecies:
        existing = await self.repo.get_species_by_code(payload.code)
        if existing is not None:
            raise ConflictError("Ya existe una especie con ese código.")

        species = AnimalSpecies(
            code=payload.code.upper(),
            name=payload.name,
            is_active=payload.is_active,
        )
        self.db.add(species)
        await self.db.flush()
        await self.audit.log(
            action="catalog.species_created",
            target_type="animal_species",
            target_id=species.id,
            actor_user_id=actor.id,
            metadata={"code": species.code},
        )
        await self.db.refresh(species)
        return species

    async def list_breeds(
        self, *, species_id: uuid.UUID | None = None
    ) -> list[AnimalBreed]:
        return await self.repo.list_breeds(species_id=species_id, active_only=True)

    async def create_breed(self, actor: User, payload: BreedCreate) -> AnimalBreed:
        species = await self.repo.get_species_by_id(payload.species_id)
        if species is None:
            raise NotFoundError("La especie indicada no existe.")

        breed = AnimalBreed(
            species_id=payload.species_id,
            name=payload.name,
            default_size=payload.default_size.value,
            is_ppp=payload.is_ppp,
            is_active=payload.is_active,
        )
        self.db.add(breed)
        await self.db.flush()
        await self.audit.log(
            action="catalog.breed_created",
            target_type="animal_breed",
            target_id=breed.id,
            actor_user_id=actor.id,
            metadata={"name": breed.name, "is_ppp": breed.is_ppp},
        )
        await self.db.refresh(breed)
        return breed

    async def list_traits(
        self, *, category: str | None = None
    ) -> list[AnimalCatalogTrait]:
        return await self.repo.list_traits(category=category, active_only=True)

    async def create_trait(
        self, actor: User, payload: CatalogTraitCreate
    ) -> AnimalCatalogTrait:
        existing = await self.repo.get_trait_by_code(payload.code)
        if existing is not None:
            raise ConflictError("Ya existe una característica con ese código.")

        trait = AnimalCatalogTrait(
            category=payload.category.value,
            code=payload.code.lower(),
            label=payload.label,
            is_active=payload.is_active,
        )
        self.db.add(trait)
        await self.db.flush()
        await self.audit.log(
            action="catalog.trait_created",
            target_type="animal_catalog_trait",
            target_id=trait.id,
            actor_user_id=actor.id,
            metadata={"code": trait.code, "category": trait.category},
        )
        await self.db.refresh(trait)
        return trait

    # =========================================================================
    # Animals CRUD & Status Lifecycle
    # =========================================================================
    async def create_animal(self, actor: User, payload: AnimalCreate) -> Animal:
        await require_shelter_editor_permission(
            self.org_repo,
            organization_id=payload.organization_id,
            user=actor,
            minimum_role=OrganizationRole.EDITOR,
        )

        species = await self.repo.get_species_by_id(payload.species_id)
        if species is None or not species.is_active:
            raise NotFoundError("La especie seleccionada no existe o no está activa.")

        if payload.breed_id is not None:
            breed = await self.repo.get_breed_by_id(payload.breed_id)
            if breed is None or breed.species_id != species.id:
                raise DomainValidationError(
                    "La raza seleccionada no existe o no pertenece a la especie indicada."
                )

        animal = Animal(
            name=payload.name,
            species_id=payload.species_id,
            breed_id=payload.breed_id,
            breed_custom=payload.breed_custom,
            sex=payload.sex.value,
            size=payload.size.value,
            age_category=payload.age_category.value,
            birth_date_estimated=payload.birth_date_estimated,
            weight_kg=payload.weight_kg,
            status=payload.status.value,
            is_urgent=payload.is_urgent,
        )
        self.db.add(animal)
        await self.db.flush()

        shelter_record = ShelterAnimal(
            organization_id=payload.organization_id,
            animal_id=animal.id,
            internal_code=payload.internal_code,
            custody_type=payload.custody_type.value,
            intake_date=payload.intake_date,
            assigned_member_user_id=actor.id,
        )
        profile = AnimalProfile(
            animal_id=animal.id,
            summary=payload.profile.summary,
            story=payload.profile.story,
            energy_level=payload.profile.energy_level.value,
            experience_required=payload.profile.experience_required.value,
            max_hours_alone=payload.profile.max_hours_alone,
            adoption_fee_cents=payload.profile.adoption_fee_cents,
            trait_codes=payload.profile.trait_codes,
        )
        health = AnimalHealth(
            animal_id=animal.id,
            is_vaccinated=payload.health.is_vaccinated,
            is_dewormed=payload.health.is_dewormed,
            is_sterilized=payload.health.is_sterilized,
            is_microchipped=payload.health.is_microchipped,
            requires_ppp_license=payload.health.requires_ppp_license,
            has_special_needs=payload.health.has_special_needs,
            has_chronic_treatment=payload.health.has_chronic_treatment,
            health_notes=payload.health.health_notes,
        )
        compat = AnimalCompatibility(
            animal_id=animal.id,
            good_with_dogs=payload.compatibilities.good_with_dogs.value,
            good_with_cats=payload.compatibilities.good_with_cats.value,
            good_with_children=payload.compatibilities.good_with_children.value,
            adapts_to_apartment=payload.compatibilities.adapts_to_apartment,
            needs_garden=payload.compatibilities.needs_garden,
        )
        location = AnimalLocation(
            animal_id=animal.id,
            city=payload.location.city,
            state_province=payload.location.state_province,
            postal_code=payload.location.postal_code,
            country_code=payload.location.country_code.upper(),
            latitude=payload.location.latitude,
            longitude=payload.location.longitude,
        )
        initial_history = AnimalStatusHistory(
            animal_id=animal.id,
            from_status=None,
            to_status=animal.status,
            changed_by_user_id=actor.id,
            reason="Creación inicial de la ficha del animal",
        )

        self.db.add_all(
            [shelter_record, profile, health, compat, location, initial_history]
        )
        await self.db.flush()

        await self.audit.log(
            action="animal.created",
            target_type="animal",
            target_id=animal.id,
            actor_user_id=actor.id,
            organization_id=payload.organization_id,
            metadata={"name": animal.name, "status": animal.status},
        )
        await self.db.refresh(animal)
        return animal

    async def get_animal_detail(
        self,
        animal_id: uuid.UUID,
        viewer: User | None = None,
    ) -> Animal:
        animal = await self.repo.get_animal_by_id(animal_id)
        if animal is None:
            raise NotFoundError("Animal no encontrado.")

        if animal.status == AnimalStatus.DRAFT.value:
            org_id = animal.shelter_record.organization_id if animal.shelter_record else None
            if org_id is None or not await can_user_view_draft_animal(
                self.org_repo, organization_id=org_id, user=viewer
            ):
                raise ForbiddenError(
                    "Esta ficha se encuentra en borrador (DRAFT) y solo es visible para miembros de su protectora."
                )

        return animal

    async def list_animals(
        self,
        *,
        viewer: User | None = None,
        species_id: uuid.UUID | None = None,
        breed_id: uuid.UUID | None = None,
        sex: str | None = None,
        size: str | None = None,
        age_category: str | None = None,
        status: str | None = AnimalStatus.AVAILABLE.value,
        organization_id: uuid.UUID | None = None,
        good_with_dogs: str | None = None,
        good_with_cats: str | None = None,
        good_with_children: str | None = None,
        adapts_to_apartment: bool | None = None,
        is_urgent: bool | None = None,
        search: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Animal], int]:
        if status == AnimalStatus.DRAFT.value:
            if organization_id is None or not await can_user_view_draft_animal(
                self.org_repo, organization_id=organization_id, user=viewer
            ):
                raise ForbiddenError(
                    "Para filtrar animales en estado DRAFT debes indicar la protectora y ser miembro activo de ella."
                )

        return await self.repo.list_animals(
            species_id=species_id,
            breed_id=breed_id,
            sex=sex,
            size=size,
            age_category=age_category,
            status=status,
            organization_id=organization_id,
            good_with_dogs=good_with_dogs,
            good_with_cats=good_with_cats,
            good_with_children=good_with_children,
            adapts_to_apartment=adapts_to_apartment,
            is_urgent=is_urgent,
            search=search,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            offset=offset,
            limit=limit,
        )

    async def update_animal(
        self,
        actor: User,
        animal_id: uuid.UUID,
        payload: AnimalUpdate,
    ) -> Animal:
        animal = await self.repo.get_animal_by_id(animal_id)
        if animal is None or animal.shelter_record is None:
            raise NotFoundError("Animal no encontrado.")

        await require_shelter_editor_permission(
            self.org_repo,
            organization_id=animal.shelter_record.organization_id,
            user=actor,
            minimum_role=OrganizationRole.EDITOR,
        )

        update_data = payload.model_dump(exclude_unset=True)
        for sub_key in ("profile", "health", "compatibilities", "location"):
            update_data.pop(sub_key, None)

        for shelter_key in ("internal_code", "custody_type", "intake_date"):
            if shelter_key in update_data:
                val = update_data.pop(shelter_key)
                if shelter_key == "custody_type" and val is not None:
                    val = val.value
                setattr(animal.shelter_record, shelter_key, val)

        for enum_key in ("sex", "size", "age_category"):
            if enum_key in update_data and update_data[enum_key] is not None:
                update_data[enum_key] = update_data[enum_key].value

        for field, value in update_data.items():
            setattr(animal, field, value)

        if payload.profile is not None and animal.profile is not None:
            p_data = payload.profile.model_dump()
            p_data["energy_level"] = payload.profile.energy_level.value
            p_data["experience_required"] = payload.profile.experience_required.value
            for k, v in p_data.items():
                setattr(animal.profile, k, v)

        if payload.health is not None and animal.health is not None:
            for k, v in payload.health.model_dump().items():
                setattr(animal.health, k, v)

        if payload.compatibilities is not None and animal.compatibilities is not None:
            c_data = payload.compatibilities.model_dump()
            c_data["good_with_dogs"] = payload.compatibilities.good_with_dogs.value
            c_data["good_with_cats"] = payload.compatibilities.good_with_cats.value
            c_data["good_with_children"] = payload.compatibilities.good_with_children.value
            for k, v in c_data.items():
                setattr(animal.compatibilities, k, v)

        if payload.location is not None and animal.location is not None:
            l_data = payload.location.model_dump()
            l_data["country_code"] = payload.location.country_code.upper()
            for k, v in l_data.items():
                setattr(animal.location, k, v)

        await self.audit.log(
            action="animal.updated",
            target_type="animal",
            target_id=animal.id,
            actor_user_id=actor.id,
            organization_id=animal.shelter_record.organization_id,
        )
        await self.db.flush()
        await self.db.refresh(animal)
        return animal

    async def transition_status(
        self,
        actor: User,
        animal_id: uuid.UUID,
        payload: AnimalStatusTransitionInput,
    ) -> Animal:
        animal = await self.repo.get_animal_by_id(animal_id)
        if animal is None or animal.shelter_record is None:
            raise NotFoundError("Animal no encontrado.")

        await require_shelter_editor_permission(
            self.org_repo,
            organization_id=animal.shelter_record.organization_id,
            user=actor,
            minimum_role=OrganizationRole.EDITOR,
        )

        old_status = animal.status
        new_status = payload.to_status.value
        if old_status == new_status:
            raise DomainValidationError("El animal ya se encuentra en el estado indicado.")

        animal.status = new_status
        if new_status == AnimalStatus.ADOPTED.value:
            animal.shelter_record.adopted_at = datetime.now(UTC)
            animal.shelter_record.adopted_by_user_id = payload.adopted_by_user_id
            animal.is_urgent = False

        history_entry = AnimalStatusHistory(
            animal_id=animal.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_user_id=actor.id,
            reason=payload.reason,
        )
        self.db.add(history_entry)
        await self.db.flush()

        await self.audit.log(
            action="animal.status_changed",
            target_type="animal",
            target_id=animal.id,
            actor_user_id=actor.id,
            organization_id=animal.shelter_record.organization_id,
            metadata={"from_status": old_status, "to_status": new_status},
        )
        await self.db.refresh(animal)
        return animal

    async def list_status_history(
        self,
        animal_id: uuid.UUID,
        viewer: User | None = None,
    ) -> list[AnimalStatusHistory]:
        await self.get_animal_detail(animal_id, viewer=viewer)
        return await self.repo.list_status_history(animal_id)

    async def add_media(
        self,
        actor: User,
        animal_id: uuid.UUID,
        payload: AnimalMediaCreate,
    ) -> AnimalMedia:
        animal = await self.repo.get_animal_by_id(animal_id)
        if animal is None or animal.shelter_record is None:
            raise NotFoundError("Animal no encontrado.")

        await require_shelter_editor_permission(
            self.org_repo,
            organization_id=animal.shelter_record.organization_id,
            user=actor,
            minimum_role=OrganizationRole.EDITOR,
        )

        if payload.is_cover:
            await self.repo.unset_cover_media(animal.id)

        media = AnimalMedia(
            animal_id=animal.id,
            media_type=payload.media_type.value,
            url=payload.url,
            storage_path=payload.storage_path,
            display_order=payload.display_order,
            is_cover=payload.is_cover,
        )
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def delete_media(
        self,
        actor: User,
        animal_id: uuid.UUID,
        media_id: uuid.UUID,
    ) -> None:
        animal = await self.repo.get_animal_by_id(animal_id)
        if animal is None or animal.shelter_record is None:
            raise NotFoundError("Animal no encontrado.")

        await require_shelter_editor_permission(
            self.org_repo,
            organization_id=animal.shelter_record.organization_id,
            user=actor,
            minimum_role=OrganizationRole.EDITOR,
        )

        media = await self.repo.get_media_by_id(animal.id, media_id)
        if media is None:
            raise NotFoundError("Elemento multimedia no encontrado.")

        await self.db.delete(media)
        await self.db.flush()

    async def delete_animal(self, actor: User, animal_id: uuid.UUID) -> None:
        animal = await self.repo.get_animal_by_id(animal_id)
        if animal is None or animal.shelter_record is None:
            raise NotFoundError("Animal no encontrado.")

        await require_shelter_editor_permission(
            self.org_repo,
            organization_id=animal.shelter_record.organization_id,
            user=actor,
            minimum_role=OrganizationRole.MANAGER,
        )
        animal.deleted_at = datetime.now(UTC)
        await self.audit.log(
            action="animal.deleted",
            target_type="animal",
            target_id=animal.id,
            actor_user_id=actor.id,
            organization_id=animal.shelter_record.organization_id,
        )
        await self.db.flush()

