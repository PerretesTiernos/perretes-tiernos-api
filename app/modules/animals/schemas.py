import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.animals.models import (
    AnimalAgeCategory,
    AnimalMediaType,
    AnimalSex,
    AnimalSize,
    AnimalStatus,
    CompatibilityLevel,
    CustodyType,
    EnergyLevel,
    ExperienceRequired,
    TraitCategory,
)


class SpeciesCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=32, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(..., min_length=2, max_length=80)
    is_active: bool = True


class SpeciesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BreedCreate(BaseModel):
    species_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=120)
    default_size: AnimalSize = AnimalSize.MEDIUM
    is_ppp: bool = False
    is_active: bool = True


class BreedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    species_id: uuid.UUID
    name: str
    default_size: AnimalSize
    is_ppp: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CatalogTraitCreate(BaseModel):
    category: TraitCategory = TraitCategory.TEMPERAMENT
    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    label: str = Field(..., min_length=2, max_length=120)
    is_active: bool = True


class CatalogTraitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: TraitCategory
    code: str
    label: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AnimalProfileInput(BaseModel):
    summary: str | None = Field(default=None, max_length=400)
    story: str | None = Field(default=None, max_length=5000)
    energy_level: EnergyLevel = EnergyLevel.MEDIUM
    experience_required: ExperienceRequired = ExperienceRequired.NONE
    max_hours_alone: int | None = Field(default=None, ge=0, le=24)
    adoption_fee_cents: int = Field(default=0, ge=0)
    trait_codes: list[str] = Field(default_factory=list)


class AnimalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    summary: str | None = None
    story: str | None = None
    energy_level: EnergyLevel
    experience_required: ExperienceRequired
    max_hours_alone: int | None = None
    adoption_fee_cents: int
    trait_codes: list[str] = Field(default_factory=list)


class AnimalHealthInput(BaseModel):
    is_vaccinated: bool = False
    is_dewormed: bool = False
    is_sterilized: bool = False
    is_microchipped: bool = False
    requires_ppp_license: bool = False
    has_special_needs: bool = False
    has_chronic_treatment: bool = False
    health_notes: str | None = Field(default=None, max_length=3000)


class AnimalHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_vaccinated: bool
    is_dewormed: bool
    is_sterilized: bool
    is_microchipped: bool
    requires_ppp_license: bool
    has_special_needs: bool
    has_chronic_treatment: bool
    health_notes: str | None = None


class AnimalCompatibilityInput(BaseModel):
    good_with_dogs: CompatibilityLevel = CompatibilityLevel.UNKNOWN
    good_with_cats: CompatibilityLevel = CompatibilityLevel.UNKNOWN
    good_with_children: CompatibilityLevel = CompatibilityLevel.UNKNOWN
    adapts_to_apartment: bool = True
    needs_garden: bool = False


class AnimalCompatibilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    good_with_dogs: CompatibilityLevel
    good_with_cats: CompatibilityLevel
    good_with_children: CompatibilityLevel
    adapts_to_apartment: bool
    needs_garden: bool


class AnimalLocationInput(BaseModel):
    city: str = Field(..., min_length=2, max_length=120)
    state_province: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=24)
    country_code: str = Field(default="ES", min_length=2, max_length=2)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)


class AnimalLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    city: str
    state_province: str | None = None
    postal_code: str | None = None
    country_code: str
    latitude: float | None = None
    longitude: float | None = None


class ShelterAnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    animal_id: uuid.UUID
    internal_code: str | None = None
    custody_type: CustodyType
    intake_date: date | None = None
    assigned_member_user_id: uuid.UUID | None = None
    adopted_at: datetime | None = None
    adopted_by_user_id: uuid.UUID | None = None


class AnimalMediaCreate(BaseModel):
    media_type: AnimalMediaType = AnimalMediaType.IMAGE
    url: str = Field(..., min_length=5, max_length=512)
    storage_path: str | None = Field(default=None, max_length=512)
    display_order: int = Field(default=0, ge=0)
    is_cover: bool = False


class AnimalMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    animal_id: uuid.UUID
    media_type: AnimalMediaType
    url: str
    storage_path: str | None = None
    display_order: int
    is_cover: bool
    created_at: datetime


class AnimalStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    animal_id: uuid.UUID
    from_status: AnimalStatus | None = None
    to_status: AnimalStatus
    changed_by_user_id: uuid.UUID | None = None
    reason: str | None = None
    created_at: datetime


class AnimalStatusTransitionInput(BaseModel):
    to_status: AnimalStatus
    reason: str | None = Field(default=None, max_length=500)
    adopted_by_user_id: uuid.UUID | None = None


class AnimalCreate(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=120)
    species_id: uuid.UUID
    breed_id: uuid.UUID | None = None
    breed_custom: str | None = Field(default=None, max_length=120)
    sex: AnimalSex = AnimalSex.UNKNOWN
    size: AnimalSize = AnimalSize.MEDIUM
    age_category: AnimalAgeCategory = AnimalAgeCategory.ADULT
    birth_date_estimated: date | None = None
    weight_kg: float | None = Field(default=None, gt=0.0, le=200.0)
    status: AnimalStatus = AnimalStatus.DRAFT
    is_urgent: bool = False
    internal_code: str | None = Field(default=None, max_length=64)
    custody_type: CustodyType = CustodyType.SHELTER_FACILITY
    intake_date: date | None = None
    profile: AnimalProfileInput = Field(default_factory=AnimalProfileInput)
    health: AnimalHealthInput = Field(default_factory=AnimalHealthInput)
    compatibilities: AnimalCompatibilityInput = Field(
        default_factory=AnimalCompatibilityInput
    )
    location: AnimalLocationInput


class AnimalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    breed_id: uuid.UUID | None = None
    breed_custom: str | None = Field(default=None, max_length=120)
    sex: AnimalSex | None = None
    size: AnimalSize | None = None
    age_category: AnimalAgeCategory | None = None
    birth_date_estimated: date | None = None
    weight_kg: float | None = Field(default=None, gt=0.0, le=200.0)
    is_urgent: bool | None = None
    internal_code: str | None = Field(default=None, max_length=64)
    custody_type: CustodyType | None = None
    intake_date: date | None = None
    profile: AnimalProfileInput | None = None
    health: AnimalHealthInput | None = None
    compatibilities: AnimalCompatibilityInput | None = None
    location: AnimalLocationInput | None = None


class AnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    species_id: uuid.UUID
    breed_id: uuid.UUID | None = None
    breed_custom: str | None = None
    sex: AnimalSex
    size: AnimalSize
    age_category: AnimalAgeCategory
    birth_date_estimated: date | None = None
    weight_kg: float | None = None
    status: AnimalStatus
    is_urgent: bool
    shelter_record: ShelterAnimalResponse | None = None
    profile: AnimalProfileResponse | None = None
    health: AnimalHealthResponse | None = None
    compatibilities: AnimalCompatibilityResponse | None = None
    location: AnimalLocationResponse | None = None
    media: list[AnimalMediaResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

