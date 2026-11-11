import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AnimalStatus(StrEnum):
    DRAFT = "DRAFT"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    ADOPTED = "ADOPTED"
    UNAVAILABLE = "UNAVAILABLE"


class AnimalSex(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"


class AnimalSize(StrEnum):
    TOY = "TOY"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    GIANT = "GIANT"


class AnimalAgeCategory(StrEnum):
    PUPPY = "PUPPY"
    YOUNG = "YOUNG"
    ADULT = "ADULT"
    SENIOR = "SENIOR"


class EnergyLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ExperienceRequired(StrEnum):
    NONE = "NONE"
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERIENCED = "EXPERIENCED"


class CompatibilityLevel(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class CustodyType(StrEnum):
    SHELTER_FACILITY = "SHELTER_FACILITY"
    FOSTER_HOME = "FOSTER_HOME"


class AnimalMediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class TraitCategory(StrEnum):
    TEMPERAMENT = "TEMPERAMENT"
    CHARACTERISTIC = "CHARACTERISTIC"
    SPECIAL_NEED = "SPECIAL_NEED"


class AnimalSpecies(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable catalog of animal species (DOG, CAT, RABBIT, etc.)."""

    __tablename__ = "animal_species"
    __table_args__ = (Index("ix_animal_species_code", "code", unique=True),)

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    breeds: Mapped[list["AnimalBreed"]] = relationship(
        "AnimalBreed",
        back_populates="species",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AnimalBreed(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable catalog of breeds per species."""

    __tablename__ = "animal_breeds"
    __table_args__ = (
        UniqueConstraint("species_id", "name", name="uq_animal_breeds_species_name"),
        Index("ix_animal_breeds_species_id", "species_id"),
    )

    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animal_species.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    default_size: Mapped[str] = mapped_column(
        String(16),
        default=AnimalSize.MEDIUM.value,
        nullable=False,
    )
    is_ppp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    species: Mapped["AnimalSpecies"] = relationship("AnimalSpecies", back_populates="breeds")


class AnimalCatalogTrait(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable catalog of temperaments, characteristics, and special needs."""

    __tablename__ = "animal_catalog_traits"
    __table_args__ = (Index("ix_animal_catalog_traits_code", "code", unique=True),)

    category: Mapped[str] = mapped_column(
        String(32),
        default=TraitCategory.TEMPERAMENT.value,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Animal(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Core entity for an animal managed by a shelter for adoption."""

    __tablename__ = "animals"
    __table_args__ = (
        Index("ix_animals_status_species", "status", "species_id"),
        Index("ix_animals_size_age", "size", "age_category"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animal_species.id", ondelete="RESTRICT"),
        nullable=False,
    )
    breed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animal_breeds.id", ondelete="SET NULL"),
        nullable=True,
    )
    breed_custom: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sex: Mapped[str] = mapped_column(
        String(16),
        default=AnimalSex.UNKNOWN.value,
        nullable=False,
    )
    size: Mapped[str] = mapped_column(
        String(16),
        default=AnimalSize.MEDIUM.value,
        nullable=False,
    )
    age_category: Mapped[str] = mapped_column(
        String(16),
        default=AnimalAgeCategory.ADULT.value,
        nullable=False,
    )
    birth_date_estimated: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=AnimalStatus.DRAFT.value,
        nullable=False,
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    shelter_record: Mapped["ShelterAnimal"] = relationship(
        "ShelterAnimal",
        back_populates="animal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    profile: Mapped["AnimalProfile"] = relationship(
        "AnimalProfile",
        back_populates="animal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    health: Mapped["AnimalHealth"] = relationship(
        "AnimalHealth",
        back_populates="animal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    compatibilities: Mapped["AnimalCompatibility"] = relationship(
        "AnimalCompatibility",
        back_populates="animal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    location: Mapped["AnimalLocation"] = relationship(
        "AnimalLocation",
        back_populates="animal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    media: Mapped[list["AnimalMedia"]] = relationship(
        "AnimalMedia",
        back_populates="animal",
        cascade="all, delete-orphan",
        order_by="AnimalMedia.display_order.asc()",
        lazy="selectin",
    )
    status_history: Mapped[list["AnimalStatusHistory"]] = relationship(
        "AnimalStatusHistory",
        back_populates="animal",
        cascade="all, delete-orphan",
        order_by="AnimalStatusHistory.created_at.desc()",
        lazy="selectin",
    )


class ShelterAnimal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Links an Animal with its managing Shelter organization and custody metadata."""

    __tablename__ = "shelter_animals"
    __table_args__ = (
        Index("ix_shelter_animals_org_id", "organization_id"),
        Index("ix_shelter_animals_animal_id", "animal_id", unique=True),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    internal_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    custody_type: Mapped[str] = mapped_column(
        String(32),
        default=CustodyType.SHELTER_FACILITY.value,
        nullable=False,
    )
    intake_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_member_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    adopted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    animal: Mapped["Animal"] = relationship("Animal", back_populates="shelter_record")


class AnimalProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Behavioral and narrative profile of an animal."""

    __tablename__ = "animal_profiles"

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(String(400), nullable=True)
    story: Mapped[str | None] = mapped_column(Text, nullable=True)
    energy_level: Mapped[str] = mapped_column(
        String(16),
        default=EnergyLevel.MEDIUM.value,
        nullable=False,
    )
    experience_required: Mapped[str] = mapped_column(
        String(24),
        default=ExperienceRequired.NONE.value,
        nullable=False,
    )
    max_hours_alone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adoption_fee_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trait_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="profile")


class AnimalHealth(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Veterinary and medical record of an animal."""

    __tablename__ = "animal_health"

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_vaccinated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dewormed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sterilized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_microchipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_ppp_license: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_special_needs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_chronic_treatment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    health_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="health")


class AnimalCompatibility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Compatibility flags used for filtering and Phase 4 matching."""

    __tablename__ = "animal_compatibilities"

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    good_with_dogs: Mapped[str] = mapped_column(
        String(16),
        default=CompatibilityLevel.UNKNOWN.value,
        nullable=False,
    )
    good_with_cats: Mapped[str] = mapped_column(
        String(16),
        default=CompatibilityLevel.UNKNOWN.value,
        nullable=False,
    )
    good_with_children: Mapped[str] = mapped_column(
        String(16),
        default=CompatibilityLevel.UNKNOWN.value,
        nullable=False,
    )
    adapts_to_apartment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    needs_garden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="compatibilities")


class AnimalLocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Approximate geographical location of an animal (shelter or foster city)."""

    __tablename__ = "animal_locations"
    __table_args__ = (Index("ix_animal_locations_lat_lon", "latitude", "longitude"),)

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state_province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="ES", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="location")


class AnimalMedia(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Photos and videos belonging to an animal profile."""

    __tablename__ = "animal_media"
    __table_args__ = (Index("ix_animal_media_animal_id_order", "animal_id", "display_order"),)

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_type: Mapped[str] = mapped_column(
        String(16),
        default=AnimalMediaType.IMAGE.value,
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="media")


class AnimalStatusHistory(Base, UUIDPrimaryKeyMixin):
    """Immutable audit trail of all status transitions of an animal."""

    __tablename__ = "animal_status_history"
    __table_args__ = (Index("ix_animal_status_history_animal_id", "animal_id"),)

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    animal: Mapped["Animal"] = relationship("Animal", back_populates="status_history")

