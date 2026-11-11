"""Centralized model registry so Alembic autogenerate discovers all domain tables."""

from app.core.database import Base
from app.modules.animals.models import (
    Animal,
    AnimalBreed,
    AnimalCatalogTrait,
    AnimalCompatibility,
    AnimalHealth,
    AnimalLocation,
    AnimalMedia,
    AnimalProfile,
    AnimalSpecies,
    AnimalStatusHistory,
    ShelterAnimal,
)
from app.modules.identity.models import User, UserPreference, UserProfile
from app.modules.moderation.models import AuditLog
from app.modules.organizations.models import (
    Address,
    Organization,
    OrganizationMember,
    OrganizationVerification,
)
from app.modules.pets.models import Pet

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "UserPreference",
    "Address",
    "Organization",
    "OrganizationMember",
    "OrganizationVerification",
    "AuditLog",
    "AnimalSpecies",
    "AnimalBreed",
    "AnimalCatalogTrait",
    "Animal",
    "ShelterAnimal",
    "AnimalProfile",
    "AnimalHealth",
    "AnimalCompatibility",
    "AnimalLocation",
    "AnimalMedia",
    "AnimalStatusHistory",
    "Pet",
]
