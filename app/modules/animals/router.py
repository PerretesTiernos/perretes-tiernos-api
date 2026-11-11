import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db,
    get_optional_user,
    require_moderator,
)
from app.core.pagination import PaginatedResponse
from app.modules.animals.models import (
    AnimalAgeCategory,
    AnimalSex,
    AnimalSize,
    AnimalStatus,
    CompatibilityLevel,
    TraitCategory,
)
from app.modules.animals.schemas import (
    AnimalCreate,
    AnimalMediaCreate,
    AnimalMediaResponse,
    AnimalResponse,
    AnimalStatusHistoryResponse,
    AnimalStatusTransitionInput,
    AnimalUpdate,
    BreedCreate,
    BreedResponse,
    CatalogTraitCreate,
    CatalogTraitResponse,
    SpeciesCreate,
    SpeciesResponse,
)
from app.modules.animals.service import AnimalService
from app.modules.identity.models import User

router = APIRouter(prefix="/animals", tags=["Animals & Adoption Catalog"])


# =============================================================================
# Catalogs (Species, Breeds, Traits)
# =============================================================================
@router.get(
    "/catalogs/species",
    response_model=list[SpeciesResponse],
    summary="List Animal Species Catalog",
    description="Lista el catálogo de especies activas (perros, gatos, conejos, etc.).",
)
async def list_species(db: AsyncSession = Depends(get_db)) -> list[SpeciesResponse]:
    service = AnimalService(db)
    items = await service.list_species()
    return [SpeciesResponse.model_validate(item) for item in items]


@router.post(
    "/catalogs/species",
    response_model=SpeciesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Animal Species (Admin/Moderator)",
    description="Añade una nueva especie al catálogo configurable.",
)
async def create_species(
    payload: SpeciesCreate,
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> SpeciesResponse:
    service = AnimalService(db)
    species = await service.create_species(current_user, payload)
    return SpeciesResponse.model_validate(species)


@router.get(
    "/catalogs/breeds",
    response_model=list[BreedResponse],
    summary="List Animal Breeds Catalog",
    description="Lista las razas activas, opcionalmente filtradas por especie.",
)
async def list_breeds(
    species_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[BreedResponse]:
    service = AnimalService(db)
    items = await service.list_breeds(species_id=species_id)
    return [BreedResponse.model_validate(item) for item in items]


@router.post(
    "/catalogs/breeds",
    response_model=BreedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Animal Breed (Admin/Moderator)",
    description="Añade una raza asociada a una especie en el catálogo.",
)
async def create_breed(
    payload: BreedCreate,
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> BreedResponse:
    service = AnimalService(db)
    breed = await service.create_breed(current_user, payload)
    return BreedResponse.model_validate(breed)


@router.get(
    "/catalogs/traits",
    response_model=list[CatalogTraitResponse],
    summary="List Animal Traits & Temperaments Catalog",
    description="Lista el catálogo de características, temperamentos y necesidades especiales.",
)
async def list_traits(
    category: TraitCategory | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[CatalogTraitResponse]:
    service = AnimalService(db)
    items = await service.list_traits(
        category=category.value if category else None
    )
    return [CatalogTraitResponse.model_validate(item) for item in items]


@router.post(
    "/catalogs/traits",
    response_model=CatalogTraitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Animal Catalog Trait (Admin/Moderator)",
    description="Crea una nueva etiqueta de temperamento o característica en el catálogo.",
)
async def create_trait(
    payload: CatalogTraitCreate,
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> CatalogTraitResponse:
    service = AnimalService(db)
    trait = await service.create_trait(current_user, payload)
    return CatalogTraitResponse.model_validate(trait)


# =============================================================================
# Animals CRUD, Search, Media & Status History
# =============================================================================
@router.post(
    "",
    response_model=AnimalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Animal Profile",
    description="Crea la ficha de un animal vinculada a una protectora (requiere rol EDITOR o superior en la protectora).",
)
async def create_animal(
    payload: AnimalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalResponse:
    service = AnimalService(db)
    animal = await service.create_animal(current_user, payload)
    return AnimalResponse.model_validate(animal)


@router.get(
    "",
    response_model=PaginatedResponse[AnimalResponse],
    summary="Search & List Animals",
    description="Busca animales en adopción con filtros por especie, raza, tamaño, edad, compatibilidad, protectora y distancia en km.",
)
async def list_animals(
    species_id: uuid.UUID | None = Query(default=None),
    breed_id: uuid.UUID | None = Query(default=None),
    sex: AnimalSex | None = Query(default=None),
    size: AnimalSize | None = Query(default=None),
    age_category: AnimalAgeCategory | None = Query(default=None),
    status_filter: AnimalStatus | None = Query(
        default=AnimalStatus.AVAILABLE, alias="status"
    ),
    organization_id: uuid.UUID | None = Query(default=None),
    good_with_dogs: CompatibilityLevel | None = Query(default=None),
    good_with_cats: CompatibilityLevel | None = Query(default=None),
    good_with_children: CompatibilityLevel | None = Query(default=None),
    adapts_to_apartment: bool | None = Query(default=None),
    is_urgent: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    latitude: float | None = Query(default=None, ge=-90.0, le=90.0),
    longitude: float | None = Query(default=None, ge=-180.0, le=180.0),
    radius_km: float | None = Query(default=None, gt=0.0, le=1000.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AnimalResponse]:
    service = AnimalService(db)
    offset = (page - 1) * page_size
    items, total = await service.list_animals(
        viewer=viewer,
        species_id=species_id,
        breed_id=breed_id,
        sex=sex.value if sex else None,
        size=size.value if size else None,
        age_category=age_category.value if age_category else None,
        status=status_filter.value if status_filter else None,
        organization_id=organization_id,
        good_with_dogs=good_with_dogs.value if good_with_dogs else None,
        good_with_cats=good_with_cats.value if good_with_cats else None,
        good_with_children=good_with_children.value if good_with_children else None,
        adapts_to_apartment=adapts_to_apartment,
        is_urgent=is_urgent,
        search=search,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        offset=offset,
        limit=page_size,
    )
    return PaginatedResponse.create(
        items=[AnimalResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{animal_id}",
    response_model=AnimalResponse,
    summary="Get Animal Details",
    description="Obtiene la ficha completa de un animal (las fichas en estado DRAFT solo son accesibles para su protectora).",
)
async def get_animal(
    animal_id: uuid.UUID,
    viewer: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalResponse:
    service = AnimalService(db)
    animal = await service.get_animal_detail(animal_id, viewer=viewer)
    return AnimalResponse.model_validate(animal)


@router.patch(
    "/{animal_id}",
    response_model=AnimalResponse,
    summary="Update Animal Profile",
    description="Actualiza los datos, perfil, salud, compatibilidades o ubicación del animal (requiere rol EDITOR+ en su protectora).",
)
async def update_animal(
    animal_id: uuid.UUID,
    payload: AnimalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalResponse:
    service = AnimalService(db)
    animal = await service.update_animal(current_user, animal_id, payload)
    return AnimalResponse.model_validate(animal)


@router.delete(
    "/{animal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Animal Profile",
    description="Realiza la baja lógica de una ficha de animal (requiere rol MANAGER+ en su protectora).",
)
async def delete_animal(
    animal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = AnimalService(db)
    await service.delete_animal(current_user, animal_id)


@router.post(
    "/{animal_id}/status",
    response_model=AnimalResponse,
    summary="Transition Animal Status",
    description="Cambia el estado del animal (DRAFT, AVAILABLE, RESERVED, ADOPTED, UNAVAILABLE) conservando su historial inmutable.",
)
async def transition_animal_status(
    animal_id: uuid.UUID,
    payload: AnimalStatusTransitionInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalResponse:
    service = AnimalService(db)
    animal = await service.transition_status(current_user, animal_id, payload)
    return AnimalResponse.model_validate(animal)


@router.get(
    "/{animal_id}/status-history",
    response_model=list[AnimalStatusHistoryResponse],
    summary="Get Animal Status History",
    description="Devuelve el historial cronológico completo de cambios de estado del animal.",
)
async def list_animal_status_history(
    animal_id: uuid.UUID,
    viewer: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnimalStatusHistoryResponse]:
    service = AnimalService(db)
    history = await service.list_status_history(animal_id, viewer=viewer)
    return [AnimalStatusHistoryResponse.model_validate(h) for h in history]


@router.post(
    "/{animal_id}/media",
    response_model=AnimalMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Animal Media",
    description="Añade una imagen o vídeo a la galería del animal (requiere rol EDITOR+ en su protectora).",
)
async def add_animal_media(
    animal_id: uuid.UUID,
    payload: AnimalMediaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalMediaResponse:
    service = AnimalService(db)
    media = await service.add_media(current_user, animal_id, payload)
    return AnimalMediaResponse.model_validate(media)


@router.delete(
    "/{animal_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Animal Media",
    description="Elimina un elemento multimedia de la galería del animal (requiere rol EDITOR+ en su protectora).",
)
async def delete_animal_media(
    animal_id: uuid.UUID,
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = AnimalService(db)
    await service.delete_media(current_user, animal_id, media_id)

