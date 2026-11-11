import uuid
from typing import Any

import jwt
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


class SupabaseTokenPayload(BaseModel):
    """Validated claims extracted from a Supabase Auth JWT."""

    sub: uuid.UUID
    email: str | None = None
    role: str = "authenticated"
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    app_metadata: dict[str, Any] = Field(default_factory=dict)


def decode_supabase_jwt(token: str) -> SupabaseTokenPayload:
    """Validates a Supabase JWT (HS256 secret or JWKS) and returns typed claims."""
    if not token:
        raise UnauthorizedError("No se proporcionó un token de autenticación.")

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": bool(settings.SUPABASE_JWT_AUDIENCE),
    }

    try:
        if settings.SUPABASE_JWKS_URL:
            jwks_client = jwt.PyJWKClient(settings.SUPABASE_JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token).key
            algorithms = ["RS256", "ES256"]
        else:
            signing_key = settings.SUPABASE_JWT_SECRET
            algorithms = ["HS256"]

        decode_kwargs: dict[str, Any] = {
            "jwt": token,
            "key": signing_key,
            "algorithms": algorithms,
            "options": options,
        }
        if settings.SUPABASE_JWT_AUDIENCE:
            decode_kwargs["audience"] = settings.SUPABASE_JWT_AUDIENCE

        payload = jwt.decode(**decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "El token de sesión ha expirado.",
            error_code="token_expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(
            "El token de autenticación es inválido.",
            error_code="invalid_token",
        ) from exc

    sub_raw = payload.get("sub")
    if not sub_raw:
        raise UnauthorizedError(
            "El token no contiene el identificador de usuario (sub).",
            error_code="invalid_token_claims",
        )

    try:
        sub_uuid = uuid.UUID(str(sub_raw))
    except ValueError as exc:
        raise UnauthorizedError(
            "El identificador sub del token no es un UUID válido.",
            error_code="invalid_token_sub",
        ) from exc

    return SupabaseTokenPayload(
        sub=sub_uuid,
        email=payload.get("email"),
        role=payload.get("role") or "authenticated",
        user_metadata=payload.get("user_metadata") or {},
        app_metadata=payload.get("app_metadata") or {},
    )

