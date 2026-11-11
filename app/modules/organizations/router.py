import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, rate_limit_sensitive
from app.core.pagination import PaginatedResponse
from app.modules.identity.models import User
from app.modules.identity.schemas import AddressCreate, AddressResponse
from app.modules.organizations.models import OrganizationType
from app.modules.organizations.schemas import (
    MyOrganizationMembershipResponse,
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberResponse,
    OrganizationMemberUpdate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationVerificationCreate,
    OrganizationVerificationResponse,
)
from app.modules.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations & Members"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_sensitive)],
    summary="Create Organization",
    description="Crea una organización independiente (protectora o empresa) y asigna al creador como OWNER activo.",
)
async def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    service = OrganizationService(db)
    org = await service.create_organization(current_user, payload)
    return OrganizationResponse.model_validate(org)


@router.get(
    "",
    response_model=PaginatedResponse[OrganizationResponse],
    summary="List Organizations",
    description="Lista organizaciones activas con soporte de paginación y filtros por tipo, verificación, búsqueda y radio en km.",
)
async def list_organizations(
    org_type: OrganizationType | None = Query(default=None),
    verified_only: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=120),
    latitude: float | None = Query(default=None, ge=-90.0, le=90.0),
    longitude: float | None = Query(default=None, ge=-180.0, le=180.0),
    radius_km: float | None = Query(default=None, gt=0.0, le=1000.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrganizationResponse]:
    service = OrganizationService(db)
    offset = (page - 1) * page_size
    items, total = await service.list_organizations(
        org_type=org_type.value if org_type else None,
        verified_only=verified_only,
        search=search,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        offset=offset,
        limit=page_size,
    )
    return PaginatedResponse.create(
        items=[OrganizationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/my",
    response_model=list[MyOrganizationMembershipResponse],
    summary="List My Organizations",
    description="Devuelve las organizaciones a las que pertenece el usuario autenticado junto con su rol.",
)
async def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyOrganizationMembershipResponse]:
    service = OrganizationService(db)
    return await service.list_my_organizations(current_user)


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get Organization Details",
    description="Obtiene el detalle de una organización.",
)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    return OrganizationResponse.model_validate(org)


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Update Organization",
    description="Actualiza los datos de una organización (requiere rol OWNER o ADMIN en la organización).",
)
async def update_organization(
    org_id: uuid.UUID,
    payload: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    service = OrganizationService(db)
    org = await service.update_organization(current_user, org_id, payload)
    return OrganizationResponse.model_validate(org)


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Organization",
    description="Realiza la baja lógica de una organización (requiere rol OWNER en la organización).",
)
async def delete_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = OrganizationService(db)
    await service.delete_organization(current_user, org_id)


@router.get(
    "/{org_id}/addresses",
    response_model=list[AddressResponse],
    summary="List Organization Addresses",
    description="Lista las direcciones físicas asociadas a una organización.",
)
async def list_organization_addresses(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AddressResponse]:
    service = OrganizationService(db)
    addresses = await service.list_organization_addresses(org_id)
    return [AddressResponse.model_validate(a) for a in addresses]


@router.post(
    "/{org_id}/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Organization Address",
    description="Añade una dirección física a la organización (requiere al menos rol MANAGER).",
)
async def add_organization_address(
    org_id: uuid.UUID,
    payload: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    service = OrganizationService(db)
    address = await service.add_organization_address(current_user, org_id, payload)
    return AddressResponse.model_validate(address)


@router.delete(
    "/{org_id}/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Organization Address",
    description="Elimina una dirección de la organización (requiere al menos rol MANAGER).",
)
async def delete_organization_address(
    org_id: uuid.UUID,
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = OrganizationService(db)
    await service.delete_organization_address(current_user, org_id, address_id)


@router.get(
    "/{org_id}/members",
    response_model=list[OrganizationMemberResponse],
    summary="List Organization Members",
    description="Lista los miembros de una organización (exclusivo para miembros activos de dicha organización).",
)
async def list_organization_members(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationMemberResponse]:
    service = OrganizationService(db)
    members = await service.list_members(current_user, org_id)
    return [OrganizationMemberResponse.model_validate(m) for m in members]


@router.post(
    "/{org_id}/members",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Organization Member",
    description="Añade un miembro a la organización con el rol indicado (requiere OWNER o ADMIN).",
)
async def add_organization_member(
    org_id: uuid.UUID,
    payload: OrganizationMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberResponse:
    service = OrganizationService(db)
    member = await service.add_member(current_user, org_id, payload)
    return OrganizationMemberResponse.model_validate(member)


@router.patch(
    "/{org_id}/members/{member_id}",
    response_model=OrganizationMemberResponse,
    summary="Update Organization Member Role or Status",
    description="Modifica el rol o estado de un miembro (protege que nunca quede la organización sin al menos un OWNER activo).",
)
async def update_organization_member(
    org_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: OrganizationMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberResponse:
    service = OrganizationService(db)
    member = await service.update_member(current_user, org_id, member_id, payload)
    return OrganizationMemberResponse.model_validate(member)


@router.delete(
    "/{org_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Organization Member",
    description="Elimina un miembro de la organización o permite que un miembro abandone la organización (salvo el único OWNER).",
)
async def remove_organization_member(
    org_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = OrganizationService(db)
    await service.remove_member(current_user, org_id, member_id)


@router.post(
    "/{org_id}/verifications",
    response_model=OrganizationVerificationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_sensitive)],
    summary="Submit Organization Verification Request",
    description="Inicia una solicitud de verificación oficial para la organización (requiere OWNER o ADMIN).",
)
async def submit_organization_verification(
    org_id: uuid.UUID,
    payload: OrganizationVerificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationVerificationResponse:
    service = OrganizationService(db)
    verification = await service.submit_verification(current_user, org_id, payload)
    return OrganizationVerificationResponse.model_validate(verification)


@router.get(
    "/{org_id}/verifications",
    response_model=list[OrganizationVerificationResponse],
    summary="List Organization Verification Requests",
    description="Consulta las solicitudes de verificación de la propia organización (requiere OWNER o ADMIN).",
)
async def list_organization_verifications(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationVerificationResponse]:
    service = OrganizationService(db)
    verifications = await service.list_org_verifications(current_user, org_id)
    return [OrganizationVerificationResponse.model_validate(v) for v in verifications]

