import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User, UserPreference, UserProfile
from app.modules.organizations.models import Address


class IdentityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_auth_id(self, auth_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.auth_id == auth_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_profile_by_username(self, username: str) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_with_defaults(
        self,
        *,
        auth_id: uuid.UUID,
        email: str,
        display_name: str | None = None,
        system_role: str = "USER",
    ) -> User:
        user = User(
            auth_id=auth_id,
            email=email.lower(),
            system_role=system_role,
            is_active=True,
            terms_accepted=False,
        )
        self.db.add(user)
        await self.db.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name=display_name or email.split("@")[0],
            is_public=True,
        )
        preferences = UserPreference(
            user_id=user.id,
            language="es",
            search_radius_km=50,
            marketing_consent=False,
            geolocation_consent=False,
            extra_settings={},
        )
        self.db.add_all([profile, preferences])
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def list_user_addresses(self, user_id: uuid.UUID) -> list[Address]:
        stmt = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_primary.desc(), Address.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_address(
        self, user_id: uuid.UUID, address_id: uuid.UUID
    ) -> Address | None:
        stmt = select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def unset_primary_user_addresses(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(Address)
            .where(Address.user_id == user_id, Address.is_primary.is_(True))
            .values(is_primary=False)
        )
        await self.db.execute(stmt)

