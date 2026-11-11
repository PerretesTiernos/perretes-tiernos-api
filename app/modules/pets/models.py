import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.animals.models import AnimalSex, AnimalSize


class Pet(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User-owned companion pet, distinct from animals available for adoption.
    Can optionally reference `origin_animal_id` when adopted through the platform.
    """

    __tablename__ = "pets"
    __table_args__ = (
        Index("ix_pets_owner_user_id", "owner_user_id"),
        Index("ix_pets_origin_animal_id", "origin_animal_id"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    origin_animal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animals.id", ondelete="SET NULL"),
        nullable=True,
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
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_sterilized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_microchipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

