import math
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.animals.models import (
    Animal,
    AnimalBreed,
    AnimalCatalogTrait,
    AnimalCompatibility,
    AnimalLocation,
    AnimalMedia,
    AnimalSpecies,
    AnimalStatus,
    AnimalStatusHistory,
    ShelterAnimal,
)
from app.modules.organizations.repository import haversine_distance_km


class AnimalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # Catalogs
    # =========================================================================
    async def list_species(self, *, active_only: bool = True) -> list[AnimalSpecies]:
        stmt = select(AnimalSpecies)
        if active_only:
            stmt = stmt.where(AnimalSpecies.is_active.is_(True))
        stmt = stmt.order_by(AnimalSpecies.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_species_by_id(self, species_id: uuid.UUID) -> AnimalSpecies | None:
        stmt = select(AnimalSpecies).where(AnimalSpecies.id == species_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_species_by_code(self, code: str) -> AnimalSpecies | None:
        stmt = select(AnimalSpecies).where(AnimalSpecies.code == code.upper())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_breeds(
        self,
        *,
        species_id: uuid.UUID | None = None,
        active_only: bool = True,
    ) -> list[AnimalBreed]:
        stmt = select(AnimalBreed)
        if species_id is not None:
            stmt = stmt.where(AnimalBreed.species_id == species_id)
        if active_only:
            stmt = stmt.where(AnimalBreed.is_active.is_(True))
        stmt = stmt.order_by(AnimalBreed.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_breed_by_id(self, breed_id: uuid.UUID) -> AnimalBreed | None:
        stmt = select(AnimalBreed).where(AnimalBreed.id == breed_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_traits(
        self,
        *,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[AnimalCatalogTrait]:
        stmt = select(AnimalCatalogTrait)
        if category:
            stmt = stmt.where(AnimalCatalogTrait.category == category)
        if active_only:
            stmt = stmt.where(AnimalCatalogTrait.is_active.is_(True))
        stmt = stmt.order_by(AnimalCatalogTrait.label.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_trait_by_code(self, code: str) -> AnimalCatalogTrait | None:
        stmt = select(AnimalCatalogTrait).where(AnimalCatalogTrait.code == code.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # =========================================================================
    # Animals
    # =========================================================================
    async def get_animal_by_id(self, animal_id: uuid.UUID) -> Animal | None:
        stmt = select(Animal).where(
            Animal.id == animal_id,
            Animal.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_animals(
        self,
        *,
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
        stmt = select(Animal).where(Animal.deleted_at.is_(None))
        count_stmt = (
            select(func.count())
            .select_from(Animal)
            .where(Animal.deleted_at.is_(None))
        )

        if status:
            stmt = stmt.where(Animal.status == status)
            count_stmt = count_stmt.where(Animal.status == status)
        else:
            stmt = stmt.where(Animal.status != AnimalStatus.DRAFT.value)
            count_stmt = count_stmt.where(Animal.status != AnimalStatus.DRAFT.value)

        if species_id is not None:
            stmt = stmt.where(Animal.species_id == species_id)
            count_stmt = count_stmt.where(Animal.species_id == species_id)

        if breed_id is not None:
            stmt = stmt.where(Animal.breed_id == breed_id)
            count_stmt = count_stmt.where(Animal.breed_id == breed_id)

        if sex:
            stmt = stmt.where(Animal.sex == sex)
            count_stmt = count_stmt.where(Animal.sex == sex)

        if size:
            stmt = stmt.where(Animal.size == size)
            count_stmt = count_stmt.where(Animal.size == size)

        if age_category:
            stmt = stmt.where(Animal.age_category == age_category)
            count_stmt = count_stmt.where(Animal.age_category == age_category)

        if is_urgent is not None:
            stmt = stmt.where(Animal.is_urgent.is_(is_urgent))
            count_stmt = count_stmt.where(Animal.is_urgent.is_(is_urgent))

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(Animal.name.ilike(pattern))
            count_stmt = count_stmt.where(Animal.name.ilike(pattern))

        if organization_id is not None:
            org_subq = (
                select(ShelterAnimal.animal_id)
                .where(ShelterAnimal.organization_id == organization_id)
                .scalar_subquery()
            )
            stmt = stmt.where(Animal.id.in_(org_subq))
            count_stmt = count_stmt.where(Animal.id.in_(org_subq))

        if any(
            v is not None
            for v in (
                good_with_dogs,
                good_with_cats,
                good_with_children,
                adapts_to_apartment,
            )
        ):
            compat_stmt = select(AnimalCompatibility.animal_id)
            if good_with_dogs:
                compat_stmt = compat_stmt.where(
                    AnimalCompatibility.good_with_dogs == good_with_dogs
                )
            if good_with_cats:
                compat_stmt = compat_stmt.where(
                    AnimalCompatibility.good_with_cats == good_with_cats
                )
            if good_with_children:
                compat_stmt = compat_stmt.where(
                    AnimalCompatibility.good_with_children == good_with_children
                )
            if adapts_to_apartment is not None:
                compat_stmt = compat_stmt.where(
                    AnimalCompatibility.adapts_to_apartment.is_(adapts_to_apartment)
                )
            compat_subq = compat_stmt.scalar_subquery()
            stmt = stmt.where(Animal.id.in_(compat_subq))
            count_stmt = count_stmt.where(Animal.id.in_(compat_subq))

        if latitude is not None and longitude is not None and radius_km is not None:
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / max(1.0, 111.0 * abs(math.cos(math.radians(latitude))))
            loc_subq = (
                select(AnimalLocation.animal_id)
                .where(
                    AnimalLocation.latitude.between(
                        latitude - lat_delta, latitude + lat_delta
                    ),
                    AnimalLocation.longitude.between(
                        longitude - lon_delta, longitude + lon_delta
                    ),
                )
                .scalar_subquery()
            )
            stmt = stmt.where(Animal.id.in_(loc_subq))
            count_stmt = count_stmt.where(Animal.id.in_(loc_subq))

        stmt = (
            stmt.order_by(Animal.is_urgent.desc(), Animal.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        total_result = await self.db.execute(count_stmt)
        items = list(result.scalars().all())

        if latitude is not None and longitude is not None and radius_km is not None:
            filtered: list[Animal] = []
            for animal in items:
                loc = animal.location
                if (
                    loc is not None
                    and loc.latitude is not None
                    and loc.longitude is not None
                    and haversine_distance_km(
                        latitude, longitude, loc.latitude, loc.longitude
                    )
                    <= radius_km
                ):
                    filtered.append(animal)
            return filtered, len(filtered)

        return items, int(total_result.scalar_one())

    async def list_status_history(
        self, animal_id: uuid.UUID
    ) -> list[AnimalStatusHistory]:
        stmt = (
            select(AnimalStatusHistory)
            .where(AnimalStatusHistory.animal_id == animal_id)
            .order_by(AnimalStatusHistory.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_media_by_id(
        self, animal_id: uuid.UUID, media_id: uuid.UUID
    ) -> AnimalMedia | None:
        stmt = select(AnimalMedia).where(
            AnimalMedia.id == media_id,
            AnimalMedia.animal_id == animal_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def unset_cover_media(self, animal_id: uuid.UUID) -> None:
        stmt = (
            update(AnimalMedia)
            .where(AnimalMedia.animal_id == animal_id, AnimalMedia.is_cover.is_(True))
            .values(is_cover=False)
        )
        await self.db.execute(stmt)

