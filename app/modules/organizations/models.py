import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.core.permissions import OrganizationRole

if TYPE_CHECKING:
    from app.modules.identity.models import User


class OrganizationType(StrEnum):
    SHELTER = "SHELTER"
    VETERINARY = "VETERINARY"
    INSURANCE = "INSURANCE"
    PET_STORE = "PET_STORE"
    TRAINER = "TRAINER"
    GROOMING = "GROOMING"
    BOARDING = "BOARDING"
    OTHER = "OTHER"


class OrganizationVerificationState(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class MemberStatus(StrEnum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class VerificationRequestStatus(StrEnum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MORE_INFO_REQUIRED = "MORE_INFO_REQUIRED"


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Independent business or shelter entity managed by multiple users with explicit roles."""

    __tablename__ = "organizations"
    __table_args__ = (
        Index("ix_organizations_slug", "slug", unique=True),
        Index("ix_organizations_org_type_status", "org_type", "verification_status"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    org_type: Mapped[str] = mapped_column(
        String(32),
        default=OrganizationType.SHELTER.value,
        nullable=False,
    )
    tax_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        default=OrganizationVerificationState.UNVERIFIED.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    verifications: Mapped[list["OrganizationVerification"]] = relationship(
        "OrganizationVerification",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    addresses: Mapped[list["Address"]] = relationship(
        "Address",
        back_populates="organization",
        foreign_keys="Address.organization_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrganizationMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Many-to-many membership between Users and Organizations with contextual role."""

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_members_org_user",
        ),
        Index("ix_organization_members_user_id", "user_id"),
        Index("ix_organization_members_org_id_role", "organization_id", "role"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        default=OrganizationRole.MEMBER.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MemberStatus.ACTIVE.value,
        nullable=False,
    )
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="members")
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
    )


class OrganizationVerification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Verification request and review lifecycle for shelters and businesses."""

    __tablename__ = "organization_verifications"
    __table_args__ = (
        Index("ix_organization_verifications_org_id", "organization_id"),
        Index("ix_organization_verifications_status", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=VerificationRequestStatus.PENDING.value,
        nullable=False,
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(32), nullable=False)
    registry_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    documents: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="verifications",
    )


class Address(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Physical address belonging exclusively to either a User OR an Organization (XOR)."""

    __tablename__ = "addresses"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND organization_id IS NULL) OR "
            "(user_id IS NULL AND organization_id IS NOT NULL)",
            name="ck_addresses_owner_xor",
        ),
        Index("ix_addresses_user_id", "user_id"),
        Index("ix_addresses_organization_id", "organization_id"),
        Index("ix_addresses_lat_lon", "latitude", "longitude"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    street_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    street_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state_province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="ES", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="addresses",
        foreign_keys=[user_id],
    )
    organization: Mapped["Organization | None"] = relationship(
        "Organization",
        back_populates="addresses",
        foreign_keys=[organization_id],
    )

