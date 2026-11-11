from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import SystemRole, has_minimum_system_role, rate_limiter
from app.core.security import SupabaseTokenPayload, decode_supabase_jwt
from app.modules.identity.models import User
from app.modules.identity.service import IdentityService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SupabaseTokenPayload:
    """Extracts and validates the Supabase Bearer JWT token."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Se requiere autenticación mediante token Bearer.")
    return decode_supabase_jwt(credentials.credentials)


async def get_current_user(
    token_payload: SupabaseTokenPayload = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolves the authenticated business User (provisioning via JIT on first login)."""
    identity_service = IdentityService(db)
    return await identity_service.get_or_provision_user(token_payload)


async def require_moderator(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures the current user has at least MODERATOR system privileges."""
    if not has_minimum_system_role(current_user.system_role, SystemRole.MODERATOR):
        raise ForbiddenError("Esta operación requiere permisos de moderación o administración.")
    return current_user


async def rate_limit_sensitive(request: Request) -> None:
    """Applies rate limiting to sensitive write endpoints."""
    client_host = request.client.host if request.client else "anonymous"
    key = f"sensitive:{client_host}:{request.url.path}"
    rate_limiter.check(key, max_requests=settings.RATE_LIMIT_SENSITIVE_PER_MINUTE)


__all__ = [
    "get_db",
    "get_token_payload",
    "get_current_user",
    "require_moderator",
    "rate_limit_sensitive",
]

