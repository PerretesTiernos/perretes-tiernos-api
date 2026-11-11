from app.modules.organizations.repository import haversine_distance_km
from app.modules.organizations.service import slugify_name


def test_haversine_distance_calculation() -> None:
    # Madrid (40.4168, -3.7038) -> Barcelona (41.3874, 2.1686) ~ 505 km
    dist = haversine_distance_km(40.4168, -3.7038, 41.3874, 2.1686)
    assert 495.0 <= dist <= 515.0
    assert haversine_distance_km(40.4168, -3.7038, 40.4168, -3.7038) == 0.0


def test_slugify_organization_name() -> None:
    assert slugify_name("Protectora Perretes Tiernos Madrid!") == "protectora-perretes-tiernos-madrid"

