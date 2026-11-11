from collections.abc import Callable

from httpx import AsyncClient


async def test_organization_creation_members_and_last_owner_protection(
    client: AsyncClient,
    make_jwt: Callable[..., str],
) -> None:
    owner_token = make_jwt(email="owner@protectora.es", full_name="Owner Protectora")
    admin_token = make_jwt(email="admin@protectora.es", full_name="Admin Protectora")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Provision both users
    owner_me = (await client.get("/api/v1/auth/me", headers=owner_headers)).json()
    admin_me = (await client.get("/api/v1/auth/me", headers=admin_headers)).json()
    assert owner_me["id"] != admin_me["id"]

    # 1. Create organization
    create_res = await client.post(
        "/api/v1/organizations",
        headers=owner_headers,
        json={
            "name": "Protectora Huellas Felices",
            "org_type": "SHELTER",
            "description": "Rescate y adopción responsable en Madrid",
            "contact_email": "contacto@huellasfelices.org",
        },
    )
    assert create_res.status_code == 201
    org = create_res.json()
    org_id = org["id"]
    assert org["slug"] == "protectora-huellas-felices"
    assert org["verification_status"] == "UNVERIFIED"

    # 2. Creator is automatically OWNER in /organizations/my
    my_orgs = await client.get("/api/v1/organizations/my", headers=owner_headers)
    assert my_orgs.status_code == 200
    assert len(my_orgs.json()) == 1
    assert my_orgs.json()[0]["role"] == "OWNER"

    # 3. Add organization address & test geolocation search
    addr_res = await client.post(
        f"/api/v1/organizations/{org_id}/addresses",
        headers=owner_headers,
        json={
            "label": "Refugio Central",
            "street_line_1": "Camino del Río 12",
            "city": "Madrid",
            "latitude": 40.4168,
            "longitude": -3.7038,
            "is_primary": True,
        },
    )
    assert addr_res.status_code == 201

    nearby_res = await client.get(
        "/api/v1/organizations",
        params={"latitude": 40.4200, "longitude": -3.7000, "radius_km": 15},
    )
    assert nearby_res.status_code == 200
    assert nearby_res.json()["total"] == 1

    far_res = await client.get(
        "/api/v1/organizations",
        params={"latitude": 41.3874, "longitude": 2.1686, "radius_km": 15},
    )
    assert far_res.status_code == 200
    assert far_res.json()["total"] == 0

    # 4. Add second user as ADMIN
    add_member_res = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers=owner_headers,
        json={"user_id": admin_me["id"], "role": "ADMIN"},
    )
    assert add_member_res.status_code == 201
    admin_member_id = add_member_res.json()["id"]

    # 5. ADMIN cannot promote themselves or anyone to OWNER (403)
    promote_attempt = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{admin_member_id}",
        headers=admin_headers,
        json={"role": "OWNER"},
    )
    assert promote_attempt.status_code == 403

    # 6. Sole OWNER cannot be downgraded or removed (422 DomainValidationError)
    members_list = (
        await client.get(
            f"/api/v1/organizations/{org_id}/members",
            headers=owner_headers,
        )
    ).json()
    owner_member = next(m for m in members_list if m["user_id"] == owner_me["id"])

    downgrade_sole_owner = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{owner_member['id']}",
        headers=owner_headers,
        json={"role": "ADMIN"},
    )
    assert downgrade_sole_owner.status_code == 422

    delete_sole_owner = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{owner_member['id']}",
        headers=owner_headers,
    )
    assert delete_sole_owner.status_code == 422

