import os
import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.dependencies import get_db
from app.core.config import settings
from app.core.database import Base, get_engine_args, normalize_database_url
from app.core.permissions import rate_limiter
from app.main import create_app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    rate_limiter.reset()
    url = normalize_database_url(TEST_DATABASE_URL)
    if url.startswith("sqlite"):
        engine = create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_async_engine(url, **get_engine_args(url))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture()
def make_jwt() -> Callable[..., str]:
    def _generate(
        *,
        auth_id: uuid.UUID | None = None,
        email: str = "usuario@perretestiernos.es",
        system_role: str = "USER",
        full_name: str = "Usuario Prueba",
        expires_delta: timedelta = timedelta(hours=1),
        secret: str | None = None,
        audience: str | None = None,
    ) -> str:
        user_sub = auth_id or uuid.uuid4()
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user_sub),
            "email": email,
            "role": "authenticated",
            "aud": audience if audience is not None else settings.SUPABASE_JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + expires_delta).timestamp()),
            "user_metadata": {"full_name": full_name},
            "app_metadata": {"system_role": system_role},
        }
        signing_secret = secret if secret is not None else settings.SUPABASE_JWT_SECRET
        return jwt.encode(payload, signing_secret, algorithm="HS256")

    return _generate

