import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.moderation.models import AuditLog
from app.modules.moderation.repository import AuditLogRepository


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AuditLogRepository(db)

    async def log(
        self,
        *,
        action: str,
        target_type: str,
        target_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        return await self.repo.create(
            action=action,
            target_type=target_type,
            target_id=target_id,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            metadata=metadata,
        )

    async def list_logs(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        action: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AuditLog], int]:
        return await self.repo.list_paginated(
            organization_id=organization_id,
            action=action,
            offset=offset,
            limit=limit,
        )

