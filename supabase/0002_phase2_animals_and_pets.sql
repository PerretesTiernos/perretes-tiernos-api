-- ==============================================================================
-- PERRETES TIERNOS API — FASE 2: ANIMALS & PETS (SUPABASE SQL SCRIPT)
-- Equivalente exacto de migrations/versions/0002_phase2_animals_and_pets.py
-- ==============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.animal_species (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(80) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_animal_species_code ON public.animal_species (code);

CREATE TABLE IF NOT EXISTS public.animal_breeds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id UUID NOT NULL REFERENCES public.animal_species(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    default_size VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    is_ppp BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_animal_breeds_species_name UNIQUE (species_id, name)
);
CREATE INDEX IF NOT EXISTS ix_animal_breeds_species_id ON public.animal_breeds (species_id);

CREATE TABLE IF NOT EXISTS public.animal_catalog_traits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(32) NOT NULL DEFAULT 'TEMPERAMENT',
    code VARCHAR(64) NOT NULL UNIQUE,
    label VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_animal_catalog_traits_code ON public.animal_catalog_traits (code);

CREATE TABLE IF NOT EXISTS public.animals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    species_id UUID NOT NULL REFERENCES public.animal_species(id) ON DELETE RESTRICT,
    breed_id UUID NULL REFERENCES public.animal_breeds(id) ON DELETE SET NULL,
    breed_custom VARCHAR(120) NULL,
    sex VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    size VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    age_category VARCHAR(16) NOT NULL DEFAULT 'ADULT',
    birth_date_estimated DATE NULL,
    weight_kg DOUBLE PRECISION NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'DRAFT',
    is_urgent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_animals_status_species ON public.animals (status, species_id);
CREATE INDEX IF NOT EXISTS ix_animals_size_age ON public.animals (size, age_category);

CREATE TABLE IF NOT EXISTS public.shelter_animals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE RESTRICT,
    animal_id UUID NOT NULL UNIQUE REFERENCES public.animals(id) ON DELETE CASCADE,
    internal_code VARCHAR(64) NULL,
    custody_type VARCHAR(32) NOT NULL DEFAULT 'SHELTER_FACILITY',
    intake_date DATE NULL,
    assigned_member_user_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    adopted_at TIMESTAMPTZ NULL,
    adopted_by_user_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_shelter_animals_org_id ON public.shelter_animals (organization_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_shelter_animals_animal_id ON public.shelter_animals (animal_id);

CREATE TABLE IF NOT EXISTS public.animal_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id UUID NOT NULL UNIQUE REFERENCES public.animals(id) ON DELETE CASCADE,
    summary VARCHAR(400) NULL,
    story TEXT NULL,
    energy_level VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    experience_required VARCHAR(24) NOT NULL DEFAULT 'NONE',
    max_hours_alone INTEGER NULL,
    adoption_fee_cents INTEGER NOT NULL DEFAULT 0,
    trait_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.animal_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id UUID NOT NULL UNIQUE REFERENCES public.animals(id) ON DELETE CASCADE,
    is_vaccinated BOOLEAN NOT NULL DEFAULT FALSE,
    is_dewormed BOOLEAN NOT NULL DEFAULT FALSE,
    is_sterilized BOOLEAN NOT NULL DEFAULT FALSE,
    is_microchipped BOOLEAN NOT NULL DEFAULT FALSE,
    requires_ppp_license BOOLEAN NOT NULL DEFAULT FALSE,
    has_special_needs BOOLEAN NOT NULL DEFAULT FALSE,
    has_chronic_treatment BOOLEAN NOT NULL DEFAULT FALSE,
    health_notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.animal_compatibilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id UUID NOT NULL UNIQUE REFERENCES public.animals(id) ON DELETE CASCADE,
    good_with_dogs VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    good_with_cats VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    good_with_children VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    adapts_to_apartment BOOLEAN NOT NULL DEFAULT TRUE,
    needs_garden BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.animal_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id UUID NOT NULL UNIQUE REFERENCES public.animals(id) ON DELETE CASCADE,
    city VARCHAR(120) NOT NULL,
    state_province VARCHAR(120) NULL,
    postal_code VARCHAR(24) NULL,
    country_code VARCHAR(2) NOT NULL DEFAULT 'ES',
    latitude DOUBLE PRECISION NULL,
    longitude DOUBLE PRECISION NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_animal_locations_lat_lon ON public.animal_locations (latitude, longitude);

CREATE TABLE IF NOT EXISTS public.animal_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id UUID NOT NULL REFERENCES public.animals(id) ON DELETE CASCADE,
    media_type VARCHAR(16) NOT NULL DEFAULT 'IMAGE',
    url VARCHAR(512) NOT NULL,
    storage_path VARCHAR(512) NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_cover BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_animal_media_animal_id_order ON public.animal_media (animal_id, display_order);

CREATE TABLE IF NOT EXISTS public.animal_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id UUID NOT NULL REFERENCES public.animals(id) ON DELETE CASCADE,
    from_status VARCHAR(24) NULL,
    to_status VARCHAR(24) NOT NULL,
    changed_by_user_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    reason VARCHAR(500) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_animal_status_history_animal_id ON public.animal_status_history (animal_id);

CREATE TABLE IF NOT EXISTS public.pets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    origin_animal_id UUID NULL REFERENCES public.animals(id) ON DELETE SET NULL,
    name VARCHAR(120) NOT NULL,
    species_id UUID NOT NULL REFERENCES public.animal_species(id) ON DELETE RESTRICT,
    breed_id UUID NULL REFERENCES public.animal_breeds(id) ON DELETE SET NULL,
    breed_custom VARCHAR(120) NULL,
    sex VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    size VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    birth_date DATE NULL,
    weight_kg DOUBLE PRECISION NULL,
    is_sterilized BOOLEAN NOT NULL DEFAULT FALSE,
    is_microchipped BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_url VARCHAR(512) NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_pets_owner_user_id ON public.pets (owner_user_id);
CREATE INDEX IF NOT EXISTS ix_pets_origin_animal_id ON public.pets (origin_animal_id);

-- Actualizar versión de Alembic
UPDATE public.alembic_version SET version_num = '0002_phase2_animals_and_pets';

COMMIT;

