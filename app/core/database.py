import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def get_engine_args(url: str) -> dict[str, Any]:
    """Configures connection pool compatible with Supabase PostgreSQL (Transaction Pooler port 6543)."""
    args: dict[str, Any] = {
        "echo": settings.DB_ECHO,
        "future": True,
        "pool_pre_ping": True,
    }

    if "postgresql" in url or "postgres" in url:
        args["pool_size"] = settings.DB_POOL_SIZE
        args["max_overflow"] = settings.DB_MAX_OVERFLOW
        args["pool_recycle"] = 1800
        args["connect_args"] = {
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
        }
    return args


def normalize_database_url(url: str) -> str:
    """Ensures asyncpg driver is specified and strips query params handled via connect_args."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    for param in (
        "?prepared_statement_cache_size=0",
        "&prepared_statement_cache_size=0",
        "%3Fprepared_statement_cache_size=0",
        "%3fprepared_statement_cache_size=0",
    ):
        url = url.replace(param, "")
    return url


database_url = normalize_database_url(settings.DATABASE_URL)
engine = create_async_engine(database_url, **get_engine_args(database_url))

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""


class UUIDPrimaryKeyMixin:
    """Mixin providing standard UUID v4 primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Mixin providing UTC created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin providing optional soft deletion timestamp (RGPD compliance)."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency providing a transactional async SQLAlchemy session per request."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

