import uuid
from collections.abc import Callable

from httpx import AsyncClient


async def test_auth_me_requires_token(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


async def test_jit_user_provisioning_and_profile_lifecycle(
    client: AsyncClient,
    make_jwt: Callable[..., str],
) -> None:
    auth_id = uuid.uuid4()
    token = make_jwt(
        auth_id=auth_id,
        email="laura@perretestiernos.es",
        full_name="Laura Gómez",
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First call provisions user, profile, and preferences automatically
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["auth_id"] == str(auth_id)
    assert me_data["email"] == "laura@perretestiernos.es"
    assert me_data["profile"]["display_name"] == "Laura Gómez"
    assert me_data["preferences"]["language"] == "es"
    user_id = me_data["id"]

    # 2. Update profile and accept RGPD terms
    patch_profile = await client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={
            "username": "laura_gomez",
            "bio": "Amante de los perros senior en adopción",
            "terms_accepted": True,
        },
    )
    assert patch_profile.status_code == 200
    assert patch_profile.json()["username"] == "laura_gomez"

    # 3. Update preferences and marketing consent
    patch_prefs = await client.patch(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={
            "language": "ca",
            "search_radius_km": 35,
            "marketing_consent": True,
            "geolocation_consent": True,
        },
    )
    assert patch_prefs.status_code == 200
    prefs_data = patch_prefs.json()
    assert prefs_data["language"] == "ca"
    assert prefs_data["search_radius_km"] == 35
    assert prefs_data["marketing_consent"] is True
    assert prefs_data["marketing_consent_at"] is not None

    # 4. Create and list user address
    addr_res = await client.post(
        "/api/v1/users/me/addresses",
        headers=headers,
        json={
            "label": "Casa",
            "street_line_1": "Calle Alcalá 100",
            "city": "Madrid",
            "postal_code": "28009",
            "country_code": "ES",
            "latitude": 40.4238,
            "longitude": -3.6768,
            "is_primary": True,
        },
    )
    assert addr_res.status_code == 201
    address_id = addr_res.json()["id"]

    list_addr = await client.get("/api/v1/users/me/addresses", headers=headers)
    assert list_addr.status_code == 200
    assert len(list_addr.json()) == 1

    # 5. Public profile visibility check
    pub_res = await client.get(f"/api/v1/users/{user_id}")
    assert pub_res.status_code == 200
    assert pub_res.json()["username"] == "laura_gomez"

    # Set profile private -> public endpoint returns 403
    await client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={"is_public": False},
    )
    priv_res = await client.get(f"/api/v1/users/{user_id}")
    assert priv_res.status_code == 403

    # Delete address
    del_res = await client.delete(
        f"/api/v1/users/me/addresses/{address_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

