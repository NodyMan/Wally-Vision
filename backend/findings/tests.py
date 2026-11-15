import pytest
from django.urls import reverse

from findings.models import Finding


@pytest.mark.django_db
def test_findings_list_empty(client):
    resp = client.get(reverse("findings"))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_findings_create_and_list(client):
    payload = {
        "ra": 133.795129,
        "dec": -7.245147,
        "note": "Object shifts smoothly across epochs in Diff mode.",
        "nickname": "AstroExplorer",
        "website": "",
    }
    resp = client.post(
        reverse("findings"),
        data=payload,
        content_type="application/json",
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["ra"] == pytest.approx(133.795129)
    assert created["dec"] == pytest.approx(-7.245147)
    assert created["nickname"] == "AstroExplorer"
    assert created["status"] == "new"
    assert "ip_hash" not in created

    list_resp = client.get(reverse("findings"))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.django_db
def test_findings_honeypot_blocks_spam(client):
    payload = {
        "ra": 100.0,
        "dec": 10.0,
        "note": "Buy cheap telescopes!",
        "website": "https://spam.example.com",
    }
    resp = client.post(
        reverse("findings"),
        data=payload,
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert Finding.objects.count() == 0


@pytest.mark.django_db
def test_findings_validation_errors(client):
    # Note > 500 chars
    resp_long = client.post(
        reverse("findings"),
        data={"ra": 10.0, "dec": 10.0, "note": "x" * 501},
        content_type="application/json",
    )
    assert resp_long.status_code == 400

    # Out-of-range coordinates
    resp_coords = client.post(
        reverse("findings"),
        data={"ra": 400.0, "dec": -95.0, "note": "Bad coords"},
        content_type="application/json",
    )
    assert resp_coords.status_code == 400


@pytest.mark.django_db
def test_findings_rate_limit(client):
    for i in range(5):
        resp = client.post(
            reverse("findings"),
            data={"ra": 10.0 + i, "dec": 5.0, "note": f"Candidate {i}"},
            content_type="application/json",
        )
        assert resp.status_code == 201

    resp_6 = client.post(
        reverse("findings"),
        data={"ra": 20.0, "dec": 5.0, "note": "Too many requests"},
        content_type="application/json",
    )
    assert resp_6.status_code == 429
    assert resp_6.json()["code"] == "rate_limited"

    # Spoofing X-Forwarded-For must NOT bypass rate limiting when NUM_PROXIES=0
    resp_spoof = client.post(
        reverse("findings"),
        data={"ra": 21.0, "dec": 5.0, "note": "Spoof attempt"},
        content_type="application/json",
        HTTP_X_FORWARDED_FOR="10.0.0.99",
    )
    assert resp_spoof.status_code == 429
