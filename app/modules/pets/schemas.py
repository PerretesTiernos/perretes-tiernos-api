import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.animals.models import AnimalSex, AnimalSize


class PetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    species_id: uuid.UUID
    breed_id: uuid.UUID | None = None
    breed_custom: str | None = Field(default=None, max_length=120)
    origin_animal_id: uuid.UUID | None = None
    sex: AnimalSex = AnimalSex.UNKNOWN
    size: AnimalSize = AnimalSize.MEDIUM
    birth_date: date | None = None
    weight_kg: float | None = Field(default=None, gt=0.0, le=200.0)
    is_sterilized: bool = False
    is_microchipped: bool = False
    avatar_url: str | None = Field(default=None, max_length=512)
    notes: str | None = Field(default=None, max_length=2000)


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    breed_id: uuid.UUID | None = None
    breed_custom: str | None = Field(default=None, max_length=120)
    sex: AnimalSex | None = None
    size: AnimalSize | None = None
    birth_date: date | None = None
    weight_kg: float | None = Field(default=None, gt=0.0, le=200.0)
    is_sterilized: bool | None = None
    is_microchipped: bool | None = None
    avatar_url: str | None = Field(default=None, max_length=512)
    notes: str | None = Field(default=None, max_length=2000)


class PetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_user_id: uuid.UUID
    origin_animal_id: uuid.UUID | None = None
    name: str
    species_id: uuid.UUID
    breed_id: uuid.UUID | None = None
    breed_custom: str | None = None
    sex: AnimalSex
    size: AnimalSize
    birth_date: date | None = None
    weight_kg: float | None = None
    is_sterilized: bool
    is_microchipped: bool
    avatar_url: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

