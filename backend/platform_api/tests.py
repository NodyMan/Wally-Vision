from unittest.mock import patch

import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from django.core.cache import cache
from django.urls import reverse


@pytest.fixture(autouse=True)
def clear_cache_and_disk(tmp_path, settings):
    cache.clear()
    settings.CACHE_DIR = tmp_path
    yield
    cache.clear()


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_presets_endpoint(client):
    response = client.get(reverse("presets"))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    slugs = {item["slug"] for item in data}
    assert slugs == {
        "barnards-star",
        "epsilon-indi-b",
        "wise-0855",
        "rw-aurigae",
        "r-draconis",
    }


@pytest.mark.parametrize(
    "query,expected_ra,expected_dec,expected_source",
    [
        ("133.795 -7.245", 133.795, -7.245, "coords_deg"),
        ("133.795, +7.245", 133.795, 7.245, "coords_deg"),
        ("0° 0°", 0.0, 0.0, "coords_deg"),
        ("360 0", 0.0, 0.0, "coords_deg"),
        ("08h55m10.8s -07d14m42s", 133.795, -7.245, "coords_hms"),
        ("08h55m10.831s −07°14′42.53″", 133.795129, -7.245147, "coords_hms"),
        ("RA 08h55m10.831s, Dec −07°14′42.53″", 133.795129, -7.245147, "coords_hms"),
        ("ra=133.795, dec=-7.245", 133.795, -7.245, "coords_deg"),
        ("08:55:10.8 -07:14:42", 133.795, -7.245, "coords_colon"),
        ("24:00:00 00:00:00", 0.0, 0.0, "coords_colon"),
    ],
)
@pytest.mark.django_db
def test_resolve_coordinate_formats(
    client, query, expected_ra, expected_dec, expected_source
):
    response = client.get(reverse("resolve"), {"q": query})
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == expected_source
    assert payload["ra"] == pytest.approx(expected_ra, abs=1e-3)
    assert payload["dec"] == pytest.approx(expected_dec, abs=1e-3)


@pytest.mark.django_db
def test_resolve_name_via_sesame_and_cache(client):
    mock_coord = SkyCoord(ra=10.684708 * u.deg, dec=41.26875 * u.deg, frame="icrs")
    with patch("platform_api.resolver.resolve_via_sesame", return_value=mock_coord) as mocked:
        resp1 = client.get(reverse("resolve"), {"q": "M31"})
        assert resp1.status_code == 200
        assert resp1.json()["source"] == "sesame"
        assert resp1.json()["ra"] == pytest.approx(10.684708, abs=1e-5)

        # Second call should hit cache rather than Sesame
        resp2 = client.get(reverse("resolve"), {"q": "M31"})
        assert resp2.status_code == 200
        assert mocked.call_count == 1


@pytest.mark.parametrize("query", ["WISE 0855", "Звезда Барнарда", "Barnard yulduzi"])
@pytest.mark.django_db
def test_resolve_localized_presets_without_sesame_call(client, query):
    with patch("platform_api.resolver.resolve_via_sesame") as mocked:
        resp = client.get(reverse("resolve"), {"q": query})
        assert resp.status_code == 200
        assert resp.json()["source"] == "preset"
        assert mocked.call_count == 0


@pytest.mark.parametrize(
    "bad_coord",
    ["360.1 0", "-1 0", "999 999", "08h65m00s 00d00m00s", "25:00:00 00:00:00"],
)
@pytest.mark.django_db
def test_resolve_invalid_coordinates_do_not_call_sesame(client, bad_coord):
    with patch("platform_api.resolver.resolve_via_sesame") as mocked:
        resp = client.get(reverse("resolve"), {"q": bad_coord})
        assert resp.status_code == 404
        assert resp.json()["code"] == "not_found"
        assert mocked.call_count == 0


@pytest.mark.parametrize("bad_query", ["", "   ", "nonexistent-object-xyz-123"])
@pytest.mark.django_db
def test_resolve_not_found(client, bad_query):
    with patch(
        "platform_api.resolver.resolve_via_sesame",
        side_effect=NameResolveError("not found"),
    ):
        resp = client.get(reverse("resolve"), {"q": bad_query})
        assert resp.status_code == 404
        assert resp.json()["code"] == "not_found"
