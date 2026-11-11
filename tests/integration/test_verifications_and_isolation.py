from collections.abc import Callable

from httpx import AsyncClient


async def test_foreign_organization_isolation_and_verification_workflow(
    client: AsyncClient,
    make_jwt: Callable[..., str],
) -> None:
    org_owner_token = make_jwt(email="protectora@perretes.es", full_name="Protectora Norte")
    outsider_token = make_jwt(email="intruso@perretes.es", full_name="Usuario Ajeno")
    moderator_token = make_jwt(
        email="moderador@perretes.es",
        full_name="Moderador Plataforma",
        system_role="MODERATOR",
    )

    owner_headers = {"Authorization": f"Bearer {org_owner_token}"}
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    moderator_headers = {"Authorization": f"Bearer {moderator_token}"}

    # Provision users
    await client.get("/api/v1/auth/me", headers=owner_headers)
    outsider_me = (await client.get("/api/v1/auth/me", headers=outsider_headers)).json()
    await client.get("/api/v1/auth/me", headers=moderator_headers)

    # Create organization by owner
    org_res = await client.post(
        "/api/v1/organizations",
        headers=owner_headers,
        json={"name": "Asociación Peludos del Norte", "org_type": "SHELTER"},
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # =========================================================================
    # Security Check: Outsider CANNOT access or mutate foreign organization
    # =========================================================================
    res_members = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=outsider_headers,
    )
    assert res_members.status_code == 403

    res_update = await client.patch(
        f"/api/v1/organizations/{org_id}",
        headers=outsider_headers,
        json={"name": "Nombre Saboteado"},
    )
    assert res_update.status_code == 403

    res_add_member = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers=outsider_headers,
        json={"user_id": outsider_me["id"], "role": "OWNER"},
    )
    assert res_add_member.status_code == 403

    res_delete = await client.delete(
        f"/api/v1/organizations/{org_id}",
        headers=outsider_headers,
    )
    assert res_delete.status_code == 403

    res_verifications = await client.get(
        f"/api/v1/organizations/{org_id}/verifications",
        headers=outsider_headers,
    )
    assert res_verifications.status_code == 403

    # =========================================================================
    # Verification & Moderation Workflow
    # =========================================================================
    submit_res = await client.post(
        f"/api/v1/organizations/{org_id}/verifications",
        headers=owner_headers,
        json={
            "legal_name": "Asociación Protectora Peludos del Norte",
            "tax_id": "G12345678",
            "registry_number": "REG-PROT-2026-009",
            "documents": [
                {
                    "file_path": "verifications/peludos-norte/cif.pdf",
                    "document_type": "TAX_ID",
                    "description": "CIF oficial de la asociación",
                }
            ],
            "notes": "Documentación oficial adjunta.",
        },
    )
    assert submit_res.status_code == 201
    verification_id = submit_res.json()["id"]
    assert submit_res.json()["status"] == "PENDING"

    # Duplicate submission while PENDING is rejected with 409 Conflict
    dup_res = await client.post(
        f"/api/v1/organizations/{org_id}/verifications",
        headers=owner_headers,
        json={
            "legal_name": "Asociación Protectora Peludos del Norte",
            "tax_id": "G12345678",
        },
    )
    assert dup_res.status_code == 409

    # Regular user cannot access admin verification queue
    forbidden_admin = await client.get(
        "/api/v1/admin/verifications",
        headers=owner_headers,
    )
    assert forbidden_admin.status_code == 403

    # Moderator lists pending verifications and approves it
    admin_list = await client.get(
        "/api/v1/admin/verifications",
        headers=moderator_headers,
        params={"status": "PENDING"},
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1

    review_res = await client.patch(
        f"/api/v1/admin/verifications/{verification_id}",
        headers=moderator_headers,
        json={
            "status": "APPROVED",
            "notes": "CIF y registro autonómico comprobados.",
        },
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # Organization is now VERIFIED
    org_after = await client.get(f"/api/v1/organizations/{org_id}")
    assert org_after.status_code == 200
    assert org_after.json()["verification_status"] == "VERIFIED"

    # Audit logs recorded all critical operations
    audit_res = await client.get(
        "/api/v1/admin/audit-logs",
        headers=moderator_headers,
        params={"organization_id": org_id},
    )
    assert audit_res.status_code == 200
    actions = {item["action"] for item in audit_res.json()["items"]}
    assert "organization.created" in actions
    assert "organization.verification_submitted" in actions
    assert "organization.verification_reviewed" in actions

