import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    AddressCreate,
    AddressResponse,
    UserMeResponse,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserPublicResponse,
)
from app.modules.identity.service import IdentityService

router = APIRouter(tags=["Identity & Users"])


@router.get(
    "/auth/me",
    response_model=UserMeResponse,
    summary="Get Current Authenticated User",
    description="Devuelve el usuario autenticado mediante Supabase JWT, su perfil, preferencias y membresías en organizaciones.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch(
    "/users/me/profile",
    response_model=UserProfileResponse,
    summary="Update My Profile",
    description="Actualiza el perfil del usuario autenticado.",
)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    service = IdentityService(db)
    profile = await service.update_my_profile(current_user, payload)
    return UserProfileResponse.model_validate(profile)


@router.patch(
    "/users/me/preferences",
    response_model=UserPreferenceResponse,
    summary="Update My Preferences & RGPD Consents",
    description="Actualiza las preferencias de idioma, radio de búsqueda y consentimientos RGPD del usuario autenticado.",
)
async def update_my_preferences(
    payload: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferenceResponse:
    service = IdentityService(db)
    preferences = await service.update_my_preferences(current_user, payload)
    return UserPreferenceResponse.model_validate(preferences)


@router.get(
    "/users/me/addresses",
    response_model=list[AddressResponse],
    summary="List My Addresses",
    description="Lista las direcciones guardadas por el usuario autenticado.",
)
async def list_my_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AddressResponse]:
    service = IdentityService(db)
    addresses = await service.list_my_addresses(current_user)
    return [AddressResponse.model_validate(addr) for addr in addresses]


@router.post(
    "/users/me/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add User Address",
    description="Añade una dirección asociada al usuario autenticado.",
)
async def create_my_address(
    payload: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    service = IdentityService(db)
    address = await service.add_my_address(current_user, payload)
    return AddressResponse.model_validate(address)


@router.delete(
    "/users/me/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete My Address",
    description="Elimina una dirección propia del usuario autenticado.",
)
async def delete_my_address(
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = IdentityService(db)
    await service.delete_my_address(current_user, address_id)


@router.get(
    "/users/{user_id}",
    response_model=UserPublicResponse,
    summary="Get Public User Profile",
    description="Devuelve la información pública de un usuario (sin exponer datos sensibles ni privados).",
)
async def get_public_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UserPublicResponse:
    service = IdentityService(db)
    return await service.get_public_user_profile(user_id)

