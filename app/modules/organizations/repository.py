import math
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import OrganizationRole
from app.modules.organizations.models import (
    Address,
    MemberStatus,
    Organization,
    OrganizationMember,
    OrganizationVerification,
    OrganizationVerificationState,
)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers between two coordinates."""
    earth_radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        stmt = select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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
        stmt = select(Organization).where(
            Organization.is_active.is_(True),
            Organization.deleted_at.is_(None),
        )
        count_stmt = (
            select(func.count())
            .select_from(Organization)
            .where(
                Organization.is_active.is_(True),
                Organization.deleted_at.is_(None),
            )
        )

        if org_type:
            stmt = stmt.where(Organization.org_type == org_type)
            count_stmt = count_stmt.where(Organization.org_type == org_type)

        if verified_only:
            stmt = stmt.where(
                Organization.verification_status
                == OrganizationVerificationState.VERIFIED.value
            )
            count_stmt = count_stmt.where(
                Organization.verification_status
                == OrganizationVerificationState.VERIFIED.value
            )

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(Organization.name.ilike(pattern))
            count_stmt = count_stmt.where(Organization.name.ilike(pattern))

        if latitude is not None and longitude is not None and radius_km is not None:
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / max(1.0, 111.0 * abs(math.cos(math.radians(latitude))))
            subq = (
                select(Address.organization_id)
                .where(
                    Address.organization_id.is_not(None),
                    Address.latitude.between(latitude - lat_delta, latitude + lat_delta),
                    Address.longitude.between(longitude - lon_delta, longitude + lon_delta),
                )
                .scalar_subquery()
            )
            stmt = stmt.where(Organization.id.in_(subq))
            count_stmt = count_stmt.where(Organization.id.in_(subq))

        stmt = stmt.order_by(Organization.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        total_result = await self.db.execute(count_stmt)
        items = list(result.scalars().all())

        if latitude is not None and longitude is not None and radius_km is not None:
            filtered: list[Organization] = []
            for org in items:
                if any(
                    addr.latitude is not None
                    and addr.longitude is not None
                    and haversine_distance_km(
                        latitude, longitude, addr.latitude, addr.longitude
                    )
                    <= radius_km
                    for addr in org.addresses
                ):
                    filtered.append(org)
            return filtered, len(filtered)

        return items, int(total_result.scalar_one())

    async def get_member_by_org_and_user(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMember | None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_by_id(
        self, org_id: uuid.UUID, member_id: uuid.UUID
    ) -> OrganizationMember | None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_members(self, org_id: uuid.UUID) -> list[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org_id)
            .order_by(OrganizationMember.joined_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active_owners(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.role == OrganizationRole.OWNER.value,
                OrganizationMember.status == MemberStatus.ACTIVE.value,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def list_user_memberships(
        self, user_id: uuid.UUID
    ) -> list[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .where(
                OrganizationMember.user_id == user_id,
                Organization.deleted_at.is_(None),
            )
            .order_by(OrganizationMember.joined_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_org_addresses(self, org_id: uuid.UUID) -> list[Address]:
        stmt = (
            select(Address)
            .where(Address.organization_id == org_id)
            .order_by(Address.is_primary.desc(), Address.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_org_address(
        self, org_id: uuid.UUID, address_id: uuid.UUID
    ) -> Address | None:
        stmt = select(Address).where(
            Address.id == address_id,
            Address.organization_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def unset_primary_org_addresses(self, org_id: uuid.UUID) -> None:
        stmt = (
            update(Address)
            .where(Address.organization_id == org_id, Address.is_primary.is_(True))
            .values(is_primary=False)
        )
        await self.db.execute(stmt)

    async def list_org_verifications(
        self, org_id: uuid.UUID
    ) -> list[OrganizationVerification]:
        stmt = (
            select(OrganizationVerification)
            .where(OrganizationVerification.organization_id == org_id)
            .order_by(OrganizationVerification.submitted_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_verification_by_id(
        self, verification_id: uuid.UUID
    ) -> OrganizationVerification | None:
        stmt = select(OrganizationVerification).where(
            OrganizationVerification.id == verification_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_verifications(
        self,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[OrganizationVerification], int]:
        stmt = select(OrganizationVerification)
        count_stmt = select(func.count()).select_from(OrganizationVerification)

        if status:
            stmt = stmt.where(OrganizationVerification.status == status)
            count_stmt = count_stmt.where(OrganizationVerification.status == status)

        stmt = (
            stmt.order_by(OrganizationVerification.submitted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        total_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), int(total_result.scalar_one())

