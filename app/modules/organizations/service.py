import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    ForbiddenError,
    NotFoundError,
)
from app.core.permissions import (
    OrganizationRole,
    SystemRole,
    assert_can_assign_org_role,
    has_minimum_system_role,
)
from app.modules.identity.models import User
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import AddressCreate
from app.modules.moderation.service import AuditService
from app.modules.organizations.models import (
    Address,
    MemberStatus,
    Organization,
    OrganizationMember,
    OrganizationVerification,
    OrganizationVerificationState,
    VerificationRequestStatus,
)
from app.modules.organizations.permissions import require_active_org_membership
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import (
    MyOrganizationMembershipResponse,
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberUpdate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationVerificationCreate,
    OrganizationVerificationReview,
)


def slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"org-{uuid.uuid4().hex[:8]}"


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrganizationRepository(db)
        self.identity_repo = IdentityRepository(db)
        self.audit = AuditService(db)

    async def create_organization(
        self, actor: User, payload: OrganizationCreate
    ) -> Organization:
        slug = payload.slug or slugify_name(payload.name)
        existing = await self.repo.get_by_slug(slug)
        if existing is not None:
            if payload.slug:
                raise ConflictError("El identificador (slug) de la organización ya existe.")
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        org = Organization(
            name=payload.name,
            slug=slug,
            org_type=payload.org_type.value,
            tax_id=payload.tax_id,
            description=payload.description,
            logo_url=payload.logo_url,
            cover_url=payload.cover_url,
            website_url=payload.website_url,
            contact_email=str(payload.contact_email) if payload.contact_email else None,
            contact_phone=payload.contact_phone,
            verification_status=OrganizationVerificationState.UNVERIFIED.value,
            is_active=True,
            created_by_user_id=actor.id,
        )
        self.db.add(org)
        await self.db.flush()

        owner_member = OrganizationMember(
            organization_id=org.id,
            user_id=actor.id,
            role=OrganizationRole.OWNER.value,
            status=MemberStatus.ACTIVE.value,
            invited_by_user_id=actor.id,
        )
        self.db.add(owner_member)
        await self.db.flush()

        await self.audit.log(
            action="organization.created",
            target_type="organization",
            target_id=org.id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"slug": org.slug, "org_type": org.org_type},
        )
        await self.db.refresh(org)
        return org

    async def get_organization(self, org_id: uuid.UUID) -> Organization:
        org = await self.repo.get_by_id(org_id)
        if org is None:
            raise NotFoundError("Organización no encontrada.")
        return org

    async def list_organizations(
        self,
        *,
        org_type: str | None = None,
        verified_only: bool = False,
        search: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Organization], int]:
        return await self.repo.list_organizations(
            org_type=org_type,
            verified_only=verified_only,
            search=search,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            offset=offset,
            limit=limit,
        )

    async def list_my_organizations(
        self, actor: User
    ) -> list[MyOrganizationMembershipResponse]:
        memberships = await self.repo.list_user_memberships(actor.id)
        results: list[MyOrganizationMembershipResponse] = []
        for m in memberships:
            org = await self.repo.get_by_id(m.organization_id)
            if org is not None:
                results.append(
                    MyOrganizationMembershipResponse(
                        organization=OrganizationResponse.model_validate(org),
                        role=OrganizationRole(m.role),
                        status=MemberStatus(m.status),
                        joined_at=m.joined_at,
                    )
                )
        return results

    async def update_organization(
        self,
        actor: User,
        org_id: uuid.UUID,
        payload: OrganizationUpdate,
    ) -> Organization:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.ADMIN,
        )

        update_data = payload.model_dump(exclude_unset=True)
        if "org_type" in update_data and update_data["org_type"] is not None:
            update_data["org_type"] = update_data["org_type"].value
        if "contact_email" in update_data and update_data["contact_email"] is not None:
            update_data["contact_email"] = str(update_data["contact_email"])

        for field, value in update_data.items():
            setattr(org, field, value)

        await self.audit.log(
            action="organization.updated",
            target_type="organization",
            target_id=org.id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"updated_fields": list(update_data.keys())},
        )
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def delete_organization(self, actor: User, org_id: uuid.UUID) -> None:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.OWNER,
        )
        org.is_active = False
        org.deleted_at = datetime.now(UTC)
        await self.audit.log(
            action="organization.deleted",
            target_type="organization",
            target_id=org.id,
            actor_user_id=actor.id,
            organization_id=org.id,
        )
        await self.db.flush()

    async def list_organization_addresses(
        self, org_id: uuid.UUID
    ) -> list[Address]:
        await self.get_organization(org_id)
        return await self.repo.list_org_addresses(org_id)

    async def add_organization_address(
        self,
        actor: User,
        org_id: uuid.UUID,
        payload: AddressCreate,
    ) -> Address:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.MANAGER,
        )

        if payload.is_primary:
            await self.repo.unset_primary_org_addresses(org.id)

        address = Address(
            user_id=None,
            organization_id=org.id,
            label=payload.label,
            street_line_1=payload.street_line_1,
            street_line_2=payload.street_line_2,
            city=payload.city,
            state_province=payload.state_province,
            postal_code=payload.postal_code,
            country_code=payload.country_code.upper(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            is_primary=payload.is_primary,
        )
        self.db.add(address)
        await self.db.flush()
        await self.db.refresh(address)
        return address

    async def delete_organization_address(
        self,
        actor: User,
        org_id: uuid.UUID,
        address_id: uuid.UUID,
    ) -> None:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.MANAGER,
        )
        address = await self.repo.get_org_address(org.id, address_id)
        if address is None:
            raise NotFoundError("Dirección de la organización no encontrada.")
        await self.db.delete(address)
        await self.db.flush()

    async def list_members(
        self, actor: User, org_id: uuid.UUID
    ) -> list[OrganizationMember]:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.MEMBER,
        )
        return await self.repo.list_members(org.id)

    async def add_member(
        self,
        actor: User,
        org_id: uuid.UUID,
        payload: OrganizationMemberCreate,
    ) -> OrganizationMember:
        org = await self.get_organization(org_id)
        actor_membership = await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.ADMIN,
        )
        actor_role = (
            OrganizationRole.OWNER
            if actor_membership is None
            else OrganizationRole(actor_membership.role)
        )
        assert_can_assign_org_role(actor_role, payload.role)

        target_user = await self.identity_repo.get_by_id(payload.user_id)
        if target_user is None or not target_user.is_active:
            raise NotFoundError("El usuario indicado no existe o no está activo.")

        existing = await self.repo.get_member_by_org_and_user(org.id, target_user.id)
        if existing is not None:
            raise ConflictError("El usuario ya es miembro de esta organización.")

        member = OrganizationMember(
            organization_id=org.id,
            user_id=target_user.id,
            role=payload.role.value,
            status=MemberStatus.ACTIVE.value,
            invited_by_user_id=actor.id,
        )
        self.db.add(member)
        await self.db.flush()

        await self.audit.log(
            action="organization.member_added",
            target_type="organization_member",
            target_id=member.id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"user_id": str(target_user.id), "role": member.role},
        )
        await self.db.refresh(member)
        return member

    async def update_member(
        self,
        actor: User,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        payload: OrganizationMemberUpdate,
    ) -> OrganizationMember:
        org = await self.get_organization(org_id)
        actor_membership = await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.ADMIN,
        )
        actor_role = (
            OrganizationRole.OWNER
            if actor_membership is None
            else OrganizationRole(actor_membership.role)
        )

        member = await self.repo.get_member_by_id(org.id, member_id)
        if member is None:
            raise NotFoundError("Miembro no encontrado en esta organización.")

        if member.role == OrganizationRole.OWNER.value and actor_role != OrganizationRole.OWNER:
            raise ForbiddenError("Solo un propietario (OWNER) puede modificar a otro OWNER.")

        if payload.role is not None:
            assert_can_assign_org_role(actor_role, payload.role)

        is_losing_owner = (
            member.role == OrganizationRole.OWNER.value
            and member.status == MemberStatus.ACTIVE.value
            and (
                (payload.role is not None and payload.role != OrganizationRole.OWNER)
                or (payload.status is not None and payload.status != MemberStatus.ACTIVE)
            )
        )
        if is_losing_owner:
            active_owners = await self.repo.count_active_owners(org.id)
            if active_owners <= 1:
                raise DomainValidationError(
                    "No se puede degradar ni suspender al único propietario (OWNER) activo de la organización."
                )

        if payload.role is not None:
            member.role = payload.role.value
        if payload.status is not None:
            member.status = payload.status.value

        await self.audit.log(
            action="organization.member_updated",
            target_type="organization_member",
            target_id=member.id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"role": member.role, "status": member.status},
        )
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(
        self,
        actor: User,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> None:
        org = await self.get_organization(org_id)
        member = await self.repo.get_member_by_id(org.id, member_id)
        if member is None:
            raise NotFoundError("Miembro no encontrado en esta organización.")

        is_self = member.user_id == actor.id
        if not is_self:
            actor_membership = await require_active_org_membership(
                self.repo,
                org_id=org.id,
                user=actor,
                minimum_role=OrganizationRole.ADMIN,
            )
            actor_role = (
                OrganizationRole.OWNER
                if actor_membership is None
                else OrganizationRole(actor_membership.role)
            )
            if (
                member.role in (OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value)
                and actor_role != OrganizationRole.OWNER
            ):
                raise ForbiddenError(
                    "Solo un propietario (OWNER) puede eliminar a un miembro OWNER o ADMIN."
                )

        if (
            member.role == OrganizationRole.OWNER.value
            and member.status == MemberStatus.ACTIVE.value
        ):
            active_owners = await self.repo.count_active_owners(org.id)
            if active_owners <= 1:
                raise DomainValidationError(
                    "No se puede eliminar al único propietario (OWNER) activo de la organización."
                )

        await self.db.delete(member)
        await self.audit.log(
            action="organization.member_removed",
            target_type="organization_member",
            target_id=member_id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"removed_user_id": str(member.user_id)},
        )
        await self.db.flush()

    async def submit_verification(
        self,
        actor: User,
        org_id: uuid.UUID,
        payload: OrganizationVerificationCreate,
    ) -> OrganizationVerification:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.ADMIN,
        )

        existing_verifications = await self.repo.list_org_verifications(org.id)
        if any(
            v.status
            in (
                VerificationRequestStatus.PENDING.value,
                VerificationRequestStatus.UNDER_REVIEW.value,
            )
            for v in existing_verifications
        ):
            raise ConflictError(
                "Ya existe una solicitud de verificación pendiente de revisión para esta organización."
            )

        verification = OrganizationVerification(
            organization_id=org.id,
            submitted_by_user_id=actor.id,
            status=VerificationRequestStatus.PENDING.value,
            legal_name=payload.legal_name,
            tax_id=payload.tax_id,
            registry_number=payload.registry_number,
            documents=[doc.model_dump() for doc in payload.documents],
            notes=payload.notes,
        )
        org.verification_status = OrganizationVerificationState.PENDING.value
        if not org.tax_id:
            org.tax_id = payload.tax_id

        self.db.add(verification)
        await self.db.flush()

        await self.audit.log(
            action="organization.verification_submitted",
            target_type="organization_verification",
            target_id=verification.id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"legal_name": payload.legal_name},
        )
        await self.db.refresh(verification)
        return verification

    async def list_org_verifications(
        self,
        actor: User,
        org_id: uuid.UUID,
    ) -> list[OrganizationVerification]:
        org = await self.get_organization(org_id)
        await require_active_org_membership(
            self.repo,
            org_id=org.id,
            user=actor,
            minimum_role=OrganizationRole.ADMIN,
        )
        return await self.repo.list_org_verifications(org.id)

    async def list_admin_verifications(
        self,
        actor: User,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[OrganizationVerification], int]:
        if not has_minimum_system_role(actor.system_role, SystemRole.MODERATOR):
            raise ForbiddenError("Acceso restringido a moderadores y administradores.")
        return await self.repo.list_all_verifications(
            status=status, offset=offset, limit=limit
        )

    async def review_verification(
        self,
        actor: User,
        verification_id: uuid.UUID,
        payload: OrganizationVerificationReview,
    ) -> OrganizationVerification:
        if not has_minimum_system_role(actor.system_role, SystemRole.MODERATOR):
            raise ForbiddenError("Acceso restringido a moderadores y administradores.")

        verification = await self.repo.get_verification_by_id(verification_id)
        if verification is None:
            raise NotFoundError("Solicitud de verificación no encontrada.")

        org = await self.get_organization(verification.organization_id)

        if (
            payload.status == VerificationRequestStatus.REJECTED
            and not payload.rejection_reason
        ):
            raise DomainValidationError(
                "Es obligatorio especificar el motivo de rechazo (rejection_reason)."
            )

        verification.status = payload.status.value
        verification.reviewed_by_user_id = actor.id
        verification.reviewed_at = datetime.now(UTC)
        if payload.notes is not None:
            verification.notes = payload.notes
        if payload.rejection_reason is not None:
            verification.rejection_reason = payload.rejection_reason

        if payload.status == VerificationRequestStatus.APPROVED:
            org.verification_status = OrganizationVerificationState.VERIFIED.value
        elif payload.status == VerificationRequestStatus.REJECTED:
            org.verification_status = OrganizationVerificationState.REJECTED.value
        else:
            org.verification_status = OrganizationVerificationState.PENDING.value

        await self.audit.log(
            action="organization.verification_reviewed",
            target_type="organization_verification",
            target_id=verification.id,
            actor_user_id=actor.id,
            organization_id=org.id,
            metadata={"status": verification.status},
        )
        await self.db.flush()
        await self.db.refresh(verification)
        return verification

