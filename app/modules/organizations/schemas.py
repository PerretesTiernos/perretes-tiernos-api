import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.permissions import OrganizationRole
from app.modules.identity.schemas import AddressResponse
from app.modules.organizations.models import (
    MemberStatus,
    OrganizationType,
    OrganizationVerificationState,
    VerificationRequestStatus,
)


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    org_type: OrganizationType = OrganizationType.SHELTER
    tax_id: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=3000)
    logo_url: str | None = Field(default=None, max_length=512)
    cover_url: str | None = Field(default=None, max_length=512)
    website_url: str | None = Field(default=None, max_length=512)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    org_type: OrganizationType | None = None
    tax_id: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=3000)
    logo_url: str | None = Field(default=None, max_length=512)
    cover_url: str | None = Field(default=None, max_length=512)
    website_url: str | None = Field(default=None, max_length=512)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    org_type: OrganizationType
    tax_id: str | None = None
    description: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    website_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    verification_status: OrganizationVerificationState
    is_active: bool
    created_by_user_id: uuid.UUID
    addresses: list[AddressResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MyOrganizationMembershipResponse(BaseModel):
    organization: OrganizationResponse
    role: OrganizationRole
    status: MemberStatus
    joined_at: datetime


class OrganizationMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: OrganizationRole = OrganizationRole.MEMBER


class OrganizationMemberUpdate(BaseModel):
    role: OrganizationRole | None = None
    status: MemberStatus | None = None


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: OrganizationRole
    status: MemberStatus
    invited_by_user_id: uuid.UUID | None = None
    joined_at: datetime
    created_at: datetime
    updated_at: datetime


class VerificationDocumentItem(BaseModel):
    file_path: str = Field(..., min_length=3, max_length=512)
    document_type: str = Field(..., min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=255)


class OrganizationVerificationCreate(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=200)
    tax_id: str = Field(..., min_length=4, max_length=32)
    registry_number: str | None = Field(default=None, max_length=80)
    documents: list[VerificationDocumentItem] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class OrganizationVerificationReview(BaseModel):
    status: Literal[
        VerificationRequestStatus.UNDER_REVIEW,
        VerificationRequestStatus.APPROVED,
        VerificationRequestStatus.REJECTED,
        VerificationRequestStatus.MORE_INFO_REQUIRED,
    ]
    notes: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)


class OrganizationVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    submitted_by_user_id: uuid.UUID
    reviewed_by_user_id: uuid.UUID | None = None
    status: VerificationRequestStatus
    legal_name: str
    tax_id: str
    registry_number: str | None = None
    documents: list[VerificationDocumentItem] = Field(default_factory=list)
    notes: str | None = None
    rejection_reason: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

