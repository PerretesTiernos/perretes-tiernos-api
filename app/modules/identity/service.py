import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import SystemRole
from app.core.security import SupabaseTokenPayload
from app.modules.identity.models import User, UserPreference, UserProfile
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    AddressCreate,
    UserPreferenceUpdate,
    UserProfileUpdate,
    UserPublicResponse,
)
from app.modules.moderation.service import AuditService
from app.modules.organizations.models import Address


class IdentityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IdentityRepository(db)
        self.audit = AuditService(db)

    async def get_or_provision_user(self, token_payload: SupabaseTokenPayload) -> User:
        """Retrieves the business user by Supabase `auth_id` or provisions it atomically (JIT)."""
        user = await self.repo.get_by_auth_id(token_payload.sub)
        if user is None:
            email = token_payload.email or f"{token_payload.sub}@users.supabase.local"
            existing_by_email = await self.repo.get_by_email(email)
            if existing_by_email is not None:
                raise ConflictError(
                    "Ya existe una cuenta registrada con este correo electrónico vinculada a otra identidad."
                )

            display_name = (
                token_payload.user_metadata.get("full_name")
                or token_payload.user_metadata.get("display_name")
                or email.split("@")[0]
            )
            app_role = str(token_payload.app_metadata.get("system_role", "USER")).upper()
            system_role = (
                app_role
                if app_role in {r.value for r in SystemRole}
                else SystemRole.USER.value
            )

            user = await self.repo.create_user_with_defaults(
                auth_id=token_payload.sub,
                email=email,
                display_name=display_name,
                system_role=system_role,
            )
            await self.audit.log(
                action="user.provisioned",
                target_type="user",
                target_id=user.id,
                actor_user_id=user.id,
                metadata={"system_role": user.system_role},
            )

        if not user.is_active or user.deleted_at is not None:
            raise ForbiddenError("Esta cuenta de usuario se encuentra desactivada.")

        return user

    async def update_my_profile(
        self, user: User, payload: UserProfileUpdate
    ) -> UserProfile:
        profile = user.profile
        if profile is None:
            profile = UserProfile(user_id=user.id, is_public=True)
            self.db.add(profile)
            await self.db.flush()

        update_data = payload.model_dump(exclude_unset=True)
        terms_accepted = update_data.pop("terms_accepted", None)
        if terms_accepted is True and not user.terms_accepted:
            user.terms_accepted = True
            user.terms_accepted_at = datetime.now(UTC)

        new_username = update_data.get("username")
        if new_username and new_username != profile.username:
            existing = await self.repo.get_profile_by_username(new_username)
            if existing is not None and existing.user_id != user.id:
                raise ConflictError("El nombre de usuario elegido ya está en uso.")

        primary_address_id = update_data.get("primary_address_id")
        if primary_address_id is not None:
            addr = await self.repo.get_user_address(user.id, primary_address_id)
            if addr is None:
                raise NotFoundError("La dirección principal indicada no pertenece al usuario.")

        for field, value in update_data.items():
            setattr(profile, field, value)

        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update_my_preferences(
        self, user: User, payload: UserPreferenceUpdate
    ) -> UserPreference:
        preferences = user.preferences
        if preferences is None:
            preferences = UserPreference(user_id=user.id)
            self.db.add(preferences)
            await self.db.flush()

        update_data = payload.model_dump(exclude_unset=True)
        if "marketing_consent" in update_data:
            preferences.marketing_consent = bool(update_data.pop("marketing_consent"))
            preferences.marketing_consent_at = (
                datetime.now(UTC) if preferences.marketing_consent else None
            )

        for field, value in update_data.items():
            setattr(preferences, field, value)

        await self.db.flush()
        await self.db.refresh(preferences)
        return preferences

    async def list_my_addresses(self, user: User) -> list[Address]:
        return await self.repo.list_user_addresses(user.id)

    async def add_my_address(self, user: User, payload: AddressCreate) -> Address:
        if payload.is_primary:
            await self.repo.unset_primary_user_addresses(user.id)

        address = Address(
            user_id=user.id,
            organization_id=None,
            label=payload.label,
            street_line_1=payload.street_line_1,
            street_line_2=payload.street_line_2,
            city=payload.city,
            state_province=payload.state_province,
            postal_code=payload.postal_code,
            country_code=payload.country_code.upper(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            is_primary=payload.is_primary,
        )
        self.db.add(address)
        await self.db.flush()

        if payload.is_primary and user.profile is not None:
            user.profile.primary_address_id = address.id
            await self.db.flush()

        await self.db.refresh(address)
        return address

    async def delete_my_address(self, user: User, address_id: uuid.UUID) -> None:
        address = await self.repo.get_user_address(user.id, address_id)
        if address is None:
            raise NotFoundError("Dirección no encontrada.")
        await self.db.delete(address)
        await self.db.flush()

    async def get_public_user_profile(self, user_id: uuid.UUID) -> UserPublicResponse:
        user = await self.repo.get_by_id(user_id)
        if user is None or not user.is_active or user.profile is None:
            raise NotFoundError("Usuario no encontrado.")
        if not user.profile.is_public:
            raise ForbiddenError("El perfil de este usuario es privado.")

        return UserPublicResponse(
            id=user.id,
            username=user.profile.username,
            display_name=user.profile.display_name,
            bio=user.profile.bio,
            avatar_url=user.profile.avatar_url,
            created_at=user.created_at,
        )

