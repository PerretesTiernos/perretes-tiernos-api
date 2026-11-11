import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pets.models import Pet


class PetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, pet_id: uuid.UUID) -> Pet | None:
        stmt = select(Pet).where(Pet.id == pet_id, Pet.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(self, owner_user_id: uuid.UUID) -> list[Pet]:
        stmt = (
            select(Pet)
            .where(Pet.owner_user_id == owner_user_id, Pet.deleted_at.is_(None))
            .order_by(Pet.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

