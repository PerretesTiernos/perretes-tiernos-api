import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.modules.identity.models import User
from app.modules.pets.schemas import PetCreate, PetResponse, PetUpdate
from app.modules.pets.service import PetService

router = APIRouter(prefix="/pets", tags=["User Pets"])


@router.post(
    "",
    response_model=PetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User Pet",
    description="Registra una mascota perteneciente al usuario autenticado (con vínculo opcional al animal adoptado).",
)
async def create_pet(
    payload: PetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetResponse:
    service = PetService(db)
    pet = await service.create_pet(current_user, payload)
    return PetResponse.model_validate(pet)


@router.get(
    "/my",
    response_model=list[PetResponse],
    summary="List My Pets",
    description="Lista las mascotas activas del usuario autenticado.",
)
async def list_my_pets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PetResponse]:
    service = PetService(db)
    pets = await service.list_my_pets(current_user)
    return [PetResponse.model_validate(p) for p in pets]


@router.get(
    "/{pet_id}",
    response_model=PetResponse,
    summary="Get Pet Details",
    description="Obtiene el detalle de una mascota.",
)
async def get_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PetResponse:
    service = PetService(db)
    pet = await service.get_pet(pet_id)
    return PetResponse.model_validate(pet)


@router.patch(
    "/{pet_id}",
    response_model=PetResponse,
    summary="Update Pet",
    description="Actualiza los datos de una mascota (exclusivo para su usuario propietario).",
)
async def update_pet(
    pet_id: uuid.UUID,
    payload: PetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetResponse:
    service = PetService(db)
    pet = await service.update_pet(current_user, pet_id, payload)
    return PetResponse.model_validate(pet)


@router.delete(
    "/{pet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Pet",
    description="Realiza la baja lógica de una mascota (exclusivo para su usuario propietario).",
)
async def delete_pet(
    pet_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = PetService(db)
    await service.delete_pet(current_user, pet_id)

