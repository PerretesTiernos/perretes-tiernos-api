import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.moderation.models import AuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        action: str,
        target_type: str,
        target_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_hash: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            extra_metadata=metadata or {},
            ip_hash=ip_hash,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        action: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)

        if organization_id is not None:
            stmt = stmt.where(AuditLog.organization_id == organization_id)
            count_stmt = count_stmt.where(AuditLog.organization_id == organization_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        total_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), int(total_result.scalar_one())

