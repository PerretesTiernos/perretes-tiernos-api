-- ==============================================================================
-- PERRETES TIERNOS API — FASE 1 FOUNDATION (SUPABASE SQL SCRIPT)
-- Equivalente exacto de migrations/versions/0001_phase1_foundation.py
-- Puedes ejecutar este script directamente en el SQL Editor de Supabase.
-- ==============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 0. Tabla de control de versiones de Alembic
CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- 1. users
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_id UUID NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    system_role VARCHAR(32) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    terms_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    terms_accepted_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_auth_id ON public.users (auth_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON public.users (email);

-- 2. organizations
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(180) NOT NULL UNIQUE,
    org_type VARCHAR(32) NOT NULL DEFAULT 'SHELTER',
    tax_id VARCHAR(32) NULL,
    description TEXT NULL,
    logo_url VARCHAR(512) NULL,
    cover_url VARCHAR(512) NULL,
    website_url VARCHAR(512) NULL,
    contact_email VARCHAR(255) NULL,
    contact_phone VARCHAR(32) NULL,
    verification_status VARCHAR(32) NOT NULL DEFAULT 'UNVERIFIED',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_slug ON public.organizations (slug);
CREATE INDEX IF NOT EXISTS ix_organizations_org_type_status ON public.organizations (org_type, verification_status);

-- 3. addresses (XOR entre user_id y organization_id)
CREATE TABLE IF NOT EXISTS public.addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL REFERENCES public.users(id) ON DELETE CASCADE,
    organization_id UUID NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    label VARCHAR(80) NULL,
    street_line_1 VARCHAR(255) NOT NULL,
    street_line_2 VARCHAR(255) NULL,
    city VARCHAR(120) NOT NULL,
    state_province VARCHAR(120) NULL,
    postal_code VARCHAR(24) NULL,
    country_code VARCHAR(2) NOT NULL DEFAULT 'ES',
    latitude DOUBLE PRECISION NULL,
    longitude DOUBLE PRECISION NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_addresses_owner_xor CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL)
        OR (user_id IS NULL AND organization_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS ix_addresses_user_id ON public.addresses (user_id);
CREATE INDEX IF NOT EXISTS ix_addresses_organization_id ON public.addresses (organization_id);
CREATE INDEX IF NOT EXISTS ix_addresses_lat_lon ON public.addresses (latitude, longitude);

-- 4. user_profiles
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    username VARCHAR(64) NULL UNIQUE,
    display_name VARCHAR(120) NULL,
    bio VARCHAR(1000) NULL,
    avatar_url VARCHAR(512) NULL,
    phone VARCHAR(32) NULL,
    primary_address_id UUID NULL REFERENCES public.addresses(id) ON DELETE SET NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_user_profiles_username ON public.user_profiles (username);

-- 5. user_preferences
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    language VARCHAR(8) NOT NULL DEFAULT 'es',
    search_radius_km INTEGER NOT NULL DEFAULT 50,
    marketing_consent BOOLEAN NOT NULL DEFAULT FALSE,
    marketing_consent_at TIMESTAMPTZ NULL,
    geolocation_consent BOOLEAN NOT NULL DEFAULT FALSE,
    extra_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. organization_members
CREATE TABLE IF NOT EXISTS public.organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'MEMBER',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    invited_by_user_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_organization_members_org_user UNIQUE (organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_organization_members_user_id ON public.organization_members (user_id);
CREATE INDEX IF NOT EXISTS ix_organization_members_org_id_role ON public.organization_members (organization_id, role);

-- 7. organization_verifications
CREATE TABLE IF NOT EXISTS public.organization_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    submitted_by_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    reviewed_by_user_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    legal_name VARCHAR(200) NOT NULL,
    tax_id VARCHAR(32) NOT NULL,
    registry_number VARCHAR(80) NULL,
    documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT NULL,
    rejection_reason TEXT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_organization_verifications_org_id ON public.organization_verifications (organization_id);
CREATE INDEX IF NOT EXISTS ix_organization_verifications_status ON public.organization_verifications (status);

-- 8. audit_logs
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    organization_id UUID NULL REFERENCES public.organizations(id) ON DELETE SET NULL,
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id UUID NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_hash VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_user_id ON public.audit_logs (actor_user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_organization_id ON public.audit_logs (organization_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action_created_at ON public.audit_logs (action, created_at);

-- 9. Trigger opcional para sincronizar nuevos usuarios desde auth.users
CREATE OR REPLACE FUNCTION public.handle_new_supabase_user()
RETURNS TRIGGER AS $$
DECLARE
    new_user_id UUID;
BEGIN
    INSERT INTO public.users (auth_id, email, system_role, is_active, terms_accepted)
    VALUES (
        NEW.id,
        LOWER(NEW.email),
        COALESCE(UPPER(NEW.raw_app_meta_data->>'system_role'), 'USER'),
        TRUE,
        FALSE
    )
    ON CONFLICT (auth_id) DO NOTHING
    RETURNING id INTO new_user_id;

    IF new_user_id IS NOT NULL THEN
        INSERT INTO public.user_profiles (user_id, display_name, is_public)
        VALUES (
            new_user_id,
            COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
            TRUE
        )
        ON CONFLICT (user_id) DO NOTHING;

        INSERT INTO public.user_preferences (user_id, language, search_radius_km)
        VALUES (new_user_id, 'es', 50)
        ON CONFLICT (user_id) DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_supabase_user();

-- 10. Registrar versión en Alembic para que Railway reconozca la migración como aplicada
INSERT INTO public.alembic_version (version_num)
VALUES ('0001_phase1_foundation')
ON CONFLICT (version_num) DO NOTHING;

COMMIT;

