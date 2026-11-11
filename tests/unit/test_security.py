import uuid
from collections.abc import Callable
from datetime import timedelta

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_supabase_jwt


def test_decode_valid_supabase_jwt(make_jwt: Callable[..., str]) -> None:
    auth_id = uuid.uuid4()
    token = make_jwt(
        auth_id=auth_id,
        email="adoptante@perretestiernos.es",
        system_role="USER",
    )
    payload = decode_supabase_jwt(token)
    assert payload.sub == auth_id
    assert payload.email == "adoptante@perretestiernos.es"
    assert payload.role == "authenticated"


def test_decode_expired_jwt_raises_unauthorized(make_jwt: Callable[..., str]) -> None:
    token = make_jwt(expires_delta=timedelta(seconds=-10))
    with pytest.raises(UnauthorizedError) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.error_code == "token_expired"


def test_decode_invalid_signature_raises_unauthorized(
    make_jwt: Callable[..., str],
) -> None:
    token = make_jwt(secret="wrong-secret-key-with-at-least-32-bytes")
    with pytest.raises(UnauthorizedError) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.error_code == "invalid_token"


def test_decode_wrong_audience_raises_unauthorized(
    make_jwt: Callable[..., str],
) -> None:
    token = make_jwt(audience="wrong-audience")
    with pytest.raises(UnauthorizedError) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.error_code == "invalid_token"

