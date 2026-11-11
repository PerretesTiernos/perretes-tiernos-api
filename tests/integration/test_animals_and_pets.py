from collections.abc import Callable

from httpx import AsyncClient


async def test_phase2_animals_lifecycle_and_user_pets(
    client: AsyncClient,
    make_jwt: Callable[..., str],
) -> None:
    moderator_token = make_jwt(
        email="mod@perretes.es",
        full_name="Moderador",
        system_role="MODERATOR",
    )
    shelter_owner_token = make_jwt(
        email="refugio@perretes.es",
        full_name="Refugio Esperanza",
    )
    vet_owner_token = make_jwt(
        email="clinica@perretes.es",
        full_name="Clínica Veterinaria",
    )
    adopter_token = make_jwt(
        email="adoptante@perretes.es",
        full_name="Carlos Adoptante",
    )

    mod_headers = {"Authorization": f"Bearer {moderator_token}"}
    shelter_headers = {"Authorization": f"Bearer {shelter_owner_token}"}
    vet_headers = {"Authorization": f"Bearer {vet_owner_token}"}
    adopter_headers = {"Authorization": f"Bearer {adopter_token}"}

    # Provision users
    await client.get("/api/v1/auth/me", headers=mod_headers)
    await client.get("/api/v1/auth/me", headers=shelter_headers)
    await client.get("/api/v1/auth/me", headers=vet_headers)
    adopter_me = (await client.get("/api/v1/auth/me", headers=adopter_headers)).json()

    # 1. Create catalogs (Species, Breed, Trait)
    species_res = await client.post(
        "/api/v1/animals/catalogs/species",
        headers=mod_headers,
        json={"code": "DOG", "name": "Perro"},
    )
    assert species_res.status_code == 201
    species_id = species_res.json()["id"]

    breed_res = await client.post(
        "/api/v1/animals/catalogs/breeds",
        headers=mod_headers,
        json={
            "species_id": species_id,
            "name": "Podenco Andaluz",
            "default_size": "MEDIUM",
            "is_ppp": False,
        },
    )
    assert breed_res.status_code == 201
    breed_id = breed_res.json()["id"]

    trait_res = await client.post(
        "/api/v1/animals/catalogs/traits",
        headers=mod_headers,
        json={
            "category": "TEMPERAMENT",
            "code": "sociable_con_perros",
            "label": "Sociable con otros perros",
        },
    )
    assert trait_res.status_code == 201

    # 2. Create Shelter organization & Veterinary organization
    shelter_org = (
        await client.post(
            "/api/v1/organizations",
            headers=shelter_headers,
            json={"name": "Refugio Esperanza", "org_type": "SHELTER"},
        )
    ).json()
    vet_org = (
        await client.post(
            "/api/v1/organizations",
            headers=vet_headers,
            json={"name": "Clínica San Antón", "org_type": "VETERINARY"},
        )
    ).json()

    # Non-shelter organization (VETERINARY) cannot create adoption animals (422)
    non_shelter_attempt = await client.post(
        "/api/v1/animals",
        headers=vet_headers,
        json={
            "organization_id": vet_org["id"],
            "name": "Toby",
            "species_id": species_id,
            "location": {"city": "Madrid"},
        },
    )
    assert non_shelter_attempt.status_code == 422

    # 3. Shelter creates an animal in DRAFT status
    animal_res = await client.post(
        "/api/v1/animals",
        headers=shelter_headers,
        json={
            "organization_id": shelter_org["id"],
            "name": "Canela",
            "species_id": species_id,
            "breed_id": breed_id,
            "sex": "FEMALE",
            "size": "MEDIUM",
            "age_category": "ADULT",
            "weight_kg": 14.5,
            "status": "DRAFT",
            "is_urgent": True,
            "internal_code": "EXP-2026-01",
            "custody_type": "FOSTER_HOME",
            "profile": {
                "summary": "Podenca muy cariñosa y tranquila en casa.",
                "energy_level": "MEDIUM",
                "experience_required": "NONE",
                "max_hours_alone": 6,
                "adoption_fee_cents": 15000,
                "trait_codes": ["sociable_con_perros"],
            },
            "health": {
                "is_vaccinated": True,
                "is_dewormed": True,
                "is_sterilized": True,
                "is_microchipped": True,
            },
            "compatibilities": {
                "good_with_dogs": "YES",
                "good_with_cats": "YES",
                "good_with_children": "YES",
                "adapts_to_apartment": True,
            },
            "location": {
                "city": "Madrid",
                "state_province": "Madrid",
                "latitude": 40.4168,
                "longitude": -3.7038,
            },
        },
    )
    assert animal_res.status_code == 201
    animal_id = animal_res.json()["id"]

    # 4. DRAFT animal is hidden from public and non-members (403)
    draft_public = await client.get(f"/api/v1/animals/{animal_id}")
    assert draft_public.status_code == 403

    draft_member = await client.get(
        f"/api/v1/animals/{animal_id}",
        headers=shelter_headers,
    )
    assert draft_member.status_code == 200

    # 5. Add media to animal gallery
    media_res = await client.post(
        f"/api/v1/animals/{animal_id}/media",
        headers=shelter_headers,
        json={
            "media_type": "IMAGE",
            "url": "https://cdn.perretestiernos.es/animals/canela-1.jpg",
            "is_cover": True,
        },
    )
    assert media_res.status_code == 201

    # 6. Transition status: DRAFT -> AVAILABLE -> RESERVED -> ADOPTED
    for next_status, reason in [
        ("AVAILABLE", "Revisión veterinaria completada, lista para adopción"),
        ("RESERVED", "Reserva formalizada con adoptante Carlos"),
        ("ADOPTED", "Contrato de adopción firmado"),
    ]:
        payload = {"to_status": next_status, "reason": reason}
        if next_status == "ADOPTED":
            payload["adopted_by_user_id"] = adopter_me["id"]
        trans_res = await client.post(
            f"/api/v1/animals/{animal_id}/status",
            headers=shelter_headers,
            json=payload,
        )
        assert trans_res.status_code == 200
        assert trans_res.json()["status"] == next_status

    # Verify status history is preserved even after ADOPTED (initial + 3 transitions = 4 records)
    history_res = await client.get(f"/api/v1/animals/{animal_id}/status-history")
    assert history_res.status_code == 200
    assert len(history_res.json()) == 4

    # 7. Adopter registers their personal Pet linked to origin_animal_id
    pet_res = await client.post(
        "/api/v1/pets",
        headers=adopter_headers,
        json={
            "name": "Canela",
            "species_id": species_id,
            "breed_id": breed_id,
            "origin_animal_id": animal_id,
            "sex": "FEMALE",
            "size": "MEDIUM",
            "weight_kg": 15.0,
            "is_sterilized": True,
            "is_microchipped": True,
        },
    )
    assert pet_res.status_code == 201
    pet_id = pet_res.json()["id"]
    assert pet_res.json()["origin_animal_id"] == animal_id

    # Another user cannot modify adopter's pet (403)
    foreign_pet_patch = await client.patch(
        f"/api/v1/pets/{pet_id}",
        headers=vet_headers,
        json={"name": "Intruso"},
    )
    assert foreign_pet_patch.status_code == 403

