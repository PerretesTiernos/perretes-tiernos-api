import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.permissions import OrganizationRole, SystemRole

SupportedLanguage = Literal["es", "en", "ca", "gl", "eu"]


class AddressCreate(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    street_line_1: str = Field(..., min_length=2, max_length=255)
    street_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(..., min_length=2, max_length=120)
    state_province: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=24)
    country_code: str = Field(default="ES", min_length=2, max_length=2)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    is_primary: bool = False


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    label: str | None = None
    street_line_1: str
    street_line_2: str | None = None
    city: str
    state_province: str | None = None
    postal_code: str | None = None
    country_code: str
    latitude: float | None = None
    longitude: float | None = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    primary_address_id: uuid.UUID | None = None
    is_public: bool
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)
    avatar_url: str | None = Field(default=None, max_length=512)
    phone: str | None = Field(default=None, max_length=32)
    primary_address_id: uuid.UUID | None = None
    is_public: bool | None = None
    terms_accepted: bool | None = None


class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    language: str
    search_radius_km: int
    marketing_consent: bool
    marketing_consent_at: datetime | None = None
    geolocation_consent: bool
    extra_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class UserPreferenceUpdate(BaseModel):
    language: SupportedLanguage | None = None
    search_radius_km: int | None = Field(default=None, ge=1, le=1000)
    marketing_consent: bool | None = None
    geolocation_consent: bool | None = None
    extra_settings: dict[str, Any] | None = None


class UserOrganizationMembershipBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: uuid.UUID
    role: OrganizationRole
    status: str


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auth_id: uuid.UUID
    email: EmailStr
    system_role: SystemRole
    is_active: bool
    terms_accepted: bool
    terms_accepted_at: datetime | None = None
    profile: UserProfileResponse | None = None
    preferences: UserPreferenceResponse | None = None
    memberships: list[UserOrganizationMembershipBrief] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    created_at: datetime

