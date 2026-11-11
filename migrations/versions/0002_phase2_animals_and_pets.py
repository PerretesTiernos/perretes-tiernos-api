"""Phase 2: Animals, Catalogs, Shelter Animals, Status History and User Pets.

Revision ID: 0002_phase2_animals_and_pets
Revises: 0001_phase1_foundation
Create Date: 2026-11-11 17:50:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_phase2_animals_and_pets"
down_revision: str | None = "0001_phase1_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. animal_species
    op.create_table(
        "animal_species",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_animal_species_code", "animal_species", ["code"], unique=True)

    # 2. animal_breeds
    op.create_table(
        "animal_breeds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("species_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_size", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("is_ppp", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["species_id"], ["animal_species.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("species_id", "name", name="uq_animal_breeds_species_name"),
    )
    op.create_index("ix_animal_breeds_species_id", "animal_breeds", ["species_id"], unique=False)

    # 3. animal_catalog_traits
    op.create_table(
        "animal_catalog_traits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="TEMPERAMENT"),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_animal_catalog_traits_code", "animal_catalog_traits", ["code"], unique=True)

    # 4. animals
    op.create_table(
        "animals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("species_id", sa.UUID(), nullable=False),
        sa.Column("breed_id", sa.UUID(), nullable=True),
        sa.Column("breed_custom", sa.String(length=120), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("size", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("age_category", sa.String(length=16), nullable=False, server_default="ADULT"),
        sa.Column("birth_date_estimated", sa.Date(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="DRAFT"),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["breed_id"], ["animal_breeds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_id"], ["animal_species.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_animals_status_species", "animals", ["status", "species_id"], unique=False)
    op.create_index("ix_animals_size_age", "animals", ["size", "age_category"], unique=False)

    # 5. shelter_animals
    op.create_table(
        "shelter_animals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("internal_code", sa.String(length=64), nullable=True),
        sa.Column("custody_type", sa.String(length=32), nullable=False, server_default="SHELTER_FACILITY"),
        sa.Column("intake_date", sa.Date(), nullable=True),
        sa.Column("assigned_member_user_id", sa.UUID(), nullable=True),
        sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("adopted_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["adopted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_member_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("animal_id"),
    )
    op.create_index("ix_shelter_animals_org_id", "shelter_animals", ["organization_id"], unique=False)
    op.create_index("ix_shelter_animals_animal_id", "shelter_animals", ["animal_id"], unique=True)

    # 6. animal_profiles
    op.create_table(
        "animal_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("summary", sa.String(length=400), nullable=True),
        sa.Column("story", sa.Text(), nullable=True),
        sa.Column("energy_level", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("experience_required", sa.String(length=24), nullable=False, server_default="NONE"),
        sa.Column("max_hours_alone", sa.Integer(), nullable=True),
        sa.Column("adoption_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trait_codes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("animal_id"),
    )

    # 7. animal_health
    op.create_table(
        "animal_health",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("is_vaccinated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_dewormed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_sterilized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_microchipped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_ppp_license", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_special_needs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_chronic_treatment", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("health_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("animal_id"),
    )

    # 8. animal_compatibilities
    op.create_table(
        "animal_compatibilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("good_with_dogs", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("good_with_cats", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("good_with_children", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("adapts_to_apartment", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("needs_garden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("animal_id"),
    )

    # 9. animal_locations
    op.create_table(
        "animal_locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state_province", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=24), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="ES"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("animal_id"),
    )
    op.create_index("ix_animal_locations_lat_lon", "animal_locations", ["latitude", "longitude"], unique=False)

    # 10. animal_media
    op.create_table(
        "animal_media",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False, server_default="IMAGE"),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_cover", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_animal_media_animal_id_order", "animal_media", ["animal_id", "display_order"], unique=False)

    # 11. animal_status_history
    op.create_table(
        "animal_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("animal_id", sa.UUID(), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("changed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_animal_status_history_animal_id", "animal_status_history", ["animal_id"], unique=False)

    # 12. pets
    op.create_table(
        "pets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("origin_animal_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("species_id", sa.UUID(), nullable=False),
        sa.Column("breed_id", sa.UUID(), nullable=True),
        sa.Column("breed_custom", sa.String(length=120), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("size", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("is_sterilized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_microchipped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["breed_id"], ["animal_breeds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_animal_id"], ["animals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_id"], ["animal_species.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pets_owner_user_id", "pets", ["owner_user_id"], unique=False)
    op.create_index("ix_pets_origin_animal_id", "pets", ["origin_animal_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pets_origin_animal_id", table_name="pets")
    op.drop_index("ix_pets_owner_user_id", table_name="pets")
    op.drop_table("pets")

    op.drop_index("ix_animal_status_history_animal_id", table_name="animal_status_history")
    op.drop_table("animal_status_history")

    op.drop_index("ix_animal_media_animal_id_order", table_name="animal_media")
    op.drop_table("animal_media")

    op.drop_index("ix_animal_locations_lat_lon", table_name="animal_locations")
    op.drop_table("animal_locations")

    op.drop_table("animal_compatibilities")
    op.drop_table("animal_health")
    op.drop_table("animal_profiles")

    op.drop_index("ix_shelter_animals_animal_id", table_name="shelter_animals")
    op.drop_index("ix_shelter_animals_org_id", table_name="shelter_animals")
    op.drop_table("shelter_animals")

    op.drop_index("ix_animals_size_age", table_name="animals")
    op.drop_index("ix_animals_status_species", table_name="animals")
    op.drop_table("animals")

    op.drop_index("ix_animal_catalog_traits_code", table_name="animal_catalog_traits")
    op.drop_table("animal_catalog_traits")

    op.drop_index("ix_animal_breeds_species_id", table_name="animal_breeds")
    op.drop_table("animal_breeds")

    op.drop_index("ix_animal_species_code", table_name="animal_species")
    op.drop_table("animal_species")

