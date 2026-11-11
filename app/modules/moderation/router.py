import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, require_moderator
from app.core.pagination import PaginatedResponse
from app.modules.identity.models import User
from app.modules.moderation.schemas import AuditLogResponse
from app.modules.moderation.service import AuditService
from app.modules.organizations.models import VerificationRequestStatus
from app.modules.organizations.schemas import (
    OrganizationVerificationResponse,
    OrganizationVerificationReview,
)
from app.modules.organizations.service import OrganizationService

router = APIRouter(prefix="/admin", tags=["Moderation & Administration"])


@router.get(
    "/verifications",
    response_model=PaginatedResponse[OrganizationVerificationResponse],
    summary="List Organization Verifications (Admin/Moderator)",
    description="Lista paginada de solicitudes de verificación de organizaciones (exclusivo para MODERATOR y SUPERADMIN).",
)
async def list_admin_verifications(
    status_filter: VerificationRequestStatus | None = Query(
        default=None, alias="status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrganizationVerificationResponse]:
    service = OrganizationService(db)
    offset = (page - 1) * page_size
    items, total = await service.list_admin_verifications(
        current_user,
        status=status_filter.value if status_filter else None,
        offset=offset,
        limit=page_size,
    )
    return PaginatedResponse.create(
        items=[OrganizationVerificationResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/verifications/{verification_id}",
    response_model=OrganizationVerificationResponse,
    summary="Review Organization Verification (Admin/Moderator)",
    description="Aprueba, rechaza o solicita información adicional sobre la verificación de una organización.",
)
async def review_admin_verification(
    verification_id: uuid.UUID,
    payload: OrganizationVerificationReview,
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> OrganizationVerificationResponse:
    service = OrganizationService(db)
    verification = await service.review_verification(
        current_user, verification_id, payload
    )
    return OrganizationVerificationResponse.model_validate(verification)


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="List Audit Logs (Admin/Moderator)",
    description="Consulta el registro de auditoría de operaciones críticas (exclusivo para MODERATOR y SUPERADMIN).",
)
async def list_audit_logs(
    organization_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    service = AuditService(db)
    offset = (page - 1) * page_size
    items, total = await service.list_logs(
        organization_id=organization_id,
        action=action,
        offset=offset,
        limit=page_size,
    )
    return PaginatedResponse.create(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )

