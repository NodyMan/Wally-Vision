"""
Viewer API tests without network:  cd backend && python -m pytest viewer/tests -q
build_blink is replaced by a fake; presets are written to a temporary folder.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import json
import threading
import time

import pytest
from django.test import Client

from core import blink, config
from core.targets import PRESET_PM
from viewer import jobs, store

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
FID = "ab12" * 5


def _response(ra, dec, fov, detector, mode, pm=None, cat=None, fid=FID):
    return {
        "target": {"ra": ra, "dec": dec, "name": None, "coordinate_epoch": 2025.9 if pm else None,
                   "catalog_ra": cat[0] if cat else None, "catalog_dec": cat[1] if cat else None,
                   "pm_mas_yr": [pm.pmra_mas_yr, pm.pmdec_mas_yr] if pm else None},
        "fov_arcsec": fov, "mode": mode, "grid": {"id": "g", "width": 49, "height": 49},
        "frames": [{"id": fid, "url": f"/api/frame/{fid}.png", "detector": detector if detector != "all" else 1,
                    "kind": "epoch", "date_mjd": 60000.0}],
        "warnings": [], "flags_summary": {"bad_pixel_fraction": 0.0, "policy": "display_v1"},
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(store, "STATIC_CACHE", tmp_path / "static_cache")
    store.reload()
    yield Client()
    store.reload()


@pytest.fixture
def fake_build(monkeypatch):
    """build_blink that records its calls and can be held back with .gate."""
    calls: list[dict] = []
    gate = threading.Event()
    gate.set()

    def fake(ra, dec, fov=300, detector=6, mode="frames", name=None, pm=None, progress=None, **kw):
        calls.append({"ra": ra, "dec": dec, "detector": detector, "mode": mode, "pm": pm, "name": name})
        progress("download:3", 0.05)
        assert gate.wait(10)
        return _response(ra, dec, fov, detector, mode), {FID: PNG}

    fake.calls, fake.gate = calls, gate
    monkeypatch.setattr(blink, "build_blink", fake)
    return fake


def _wait(client, job_id, timeout=10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        body = client.get(f"/api/blink/status/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.02)
    raise AssertionError("job did not finish")


@pytest.mark.parametrize("query, code", [
    ("dec=1", "invalid_coordinates"),
    ("ra=abc&dec=1", "invalid_coordinates"),
    ("ra=nan&dec=1", "invalid_coordinates"),
    ("ra=inf&dec=1", "invalid_coordinates"),
    ("ra=360&dec=1", "invalid_coordinates"),
    ("ra=10&dec=90.5", "invalid_coordinates"),
    ("ra=10&dec=1&fov=99999", "fov_too_large"),
    ("ra=10&dec=1&fov=-5", "invalid_parameters"),
    ("ra=10&dec=1&fov=nan", "invalid_parameters"),
    ("ra=10&dec=1&detector=7", "invalid_parameters"),
    ("ra=10&dec=1&mode=rgb", "invalid_parameters"),
])
def test_invalid_parameters_are_rejected(client, fake_build, query, code):
    r = client.get(f"/api/blink?{query}")
    assert r.status_code == 400 and r.json() == {"error_code": code}
    assert fake_build.calls == []


def test_cold_request_runs_a_job_then_is_served_from_cache(client, fake_build):
    url = "/api/blink?ra=10&dec=20&fov=300&detector=2&mode=diff"
    r = client.get(url)
    assert r.status_code == 202
    job = r.json()
    assert job["status"] in ("queued", "running") and len(job["job_id"]) == 32 and "result" not in job

    done = _wait(client, job["job_id"])
    assert done["status"] == "done" and done["progress"] == 1 and done["stage"] == "done"
    assert done["result"]["mode"] == "diff" and done["result"]["frames"][0]["detector"] == 2

    again = client.get(url)
    assert again.status_code == 200 and again.json() == done["result"]
    assert len(fake_build.calls) == 1

    png = client.get(f"/api/frame/{FID}.png")
    assert png.status_code == 200 and png["Content-Type"] == "image/png"
    assert b"".join(png.streaming_content) == PNG


def test_only_cached_never_starts_a_job(client, fake_build):
    url = "/api/blink?ra=15&dec=20&detector=2&only_cached=1"
    r = client.get(url)
    assert r.status_code == 204 and r.content == b"" and fake_build.calls == []
    _wait(client, client.get("/api/blink?ra=15&dec=20&detector=2").json()["job_id"])
    assert client.get(url).status_code == 200 and len(fake_build.calls) == 1


def test_same_request_shares_one_job_and_reports_progress(client, fake_build):
    fake_build.gate.clear()
    try:
        url = "/api/blink?ra=11&dec=20&detector=3"
        a, b = client.get(url).json(), client.get(url).json()
        assert a["job_id"] == b["job_id"]
        t0 = time.time()
        while (body := client.get(f"/api/blink/status/{a['job_id']}").json())["stage"] != "download:3":
            assert time.time() - t0 < 5
            time.sleep(0.02)
        assert body["status"] == "running" and 0 < body["progress"] < 1
    finally:
        fake_build.gate.set()
    assert _wait(client, a["job_id"])["status"] == "done"
    assert len(fake_build.calls) == 1


def test_job_errors_become_codes_without_details(client, monkeypatch):
    def no_data(*a, **k):
        raise blink.BlinkError("no_data", "internal detail")

    monkeypatch.setattr(blink, "build_blink", no_data)
    body = _wait(client, client.get("/api/blink?ra=12&dec=20").json()["job_id"])
    assert body["status"] == "error" and body["error_code"] == "no_data" and "internal detail" not in json.dumps(body)

    def crash(*a, **k):
        raise RuntimeError(r"C:\secret\path")

    monkeypatch.setattr(blink, "build_blink", crash)
    body = _wait(client, client.get("/api/blink?ra=13&dec=20").json()["job_id"])
    assert body["error_code"] == "server_error" and "secret" not in json.dumps(body)


def test_queue_limit_answers_429(client, fake_build):
    fake_build.gate.clear()
    try:
        ids = [client.get(f"/api/blink?ra={20 + i}&dec=5").json()["job_id"] for i in range(jobs.MAX_ACTIVE)]
        r = client.get("/api/blink?ra=99&dec=5")
        assert r.status_code == 429 and r.json() == {"error_code": "busy"} and r["Retry-After"]
    finally:
        fake_build.gate.set()
    for jid in ids:
        assert _wait(client, jid)["status"] == "done"


def test_cold_requests_can_be_switched_off(client, fake_build, monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "ALLOW_COLD", False)
    r = client.get("/api/blink?ra=40&dec=5&detector=2")
    assert r.status_code == 503 and r.json() == {"error_code": "cold_disabled"} and fake_build.calls == []
    _write_preset(tmp_path)                                  # presets still answer at once
    store.reload()
    assert client.get("/api/blink?ra=269.452083&dec=4.693364&detector=2&mode=diff").status_code == 200


def test_unknown_job_and_bad_frame_ids(client):
    assert client.get("/api/blink/status/" + "0" * 32).status_code == 404
    assert client.get("/api/blink/status/nope").status_code == 404
    assert client.get("/api/frame/" + "f" * 20 + ".png").json() == {"error_code": "not_found"}
    for bad in ("..%2F..%2Fsettings", "ABCDEF", "a/b", "a.b"):
        assert client.get(f"/api/frame/{bad}.png").status_code == 404
    assert client.post("/api/blink?ra=1&dec=1").status_code == 405


def _write_preset(tmp_path, slug="barnards-star"):
    pm = PRESET_PM[slug]
    cat = (269.452083, 4.693364)
    d = tmp_path / "static_cache" / slug
    (d / "frames").mkdir(parents=True)
    pid = "cd34" * 5
    for mode in ("frames", "diff"):
        resp = _response(269.44629, 4.767917, 300, 2, mode, pm=pm, cat=cat, fid=pid)
        (d / f"blink_{mode}_d2.json").write_text(json.dumps(resp), encoding="utf-8")
    (d / "frames" / f"{pid}.png").write_bytes(PNG)
    return cat, pid, pm


def test_preset_is_served_at_once_with_its_frames(client, fake_build, tmp_path):
    cat, pid, _ = _write_preset(tmp_path)
    for ra, dec in (cat, (269.44629, 4.767917)):          # catalog position or the propagated one
        r = client.get(f"/api/blink?ra={ra}&dec={dec}&fov=300&detector=2&mode=diff")
        assert r.status_code == 200 and r.json()["mode"] == "diff"
    assert fake_build.calls == []
    assert client.get(f"/api/frame/{pid}.png").status_code == 200


def test_preset_cache_never_answers_with_another_band_or_field(client, fake_build, tmp_path):
    _write_preset(tmp_path)                                   # D2, fov 300, frames + diff
    for q in ("detector=6&mode=diff", "detector=2&mode=diff&fov=900", "detector=all&mode=diff"):
        r = client.get(f"/api/blink?ra=269.452083&dec=4.693364&{q}")
        assert r.status_code == 202, q                        # computed, not a wrong cached answer
        _wait(client, r.json()["job_id"])
    assert sorted(str(c["detector"]) for c in fake_build.calls) == ["2", "6", "all"]


def test_preset_target_in_another_mode_keeps_proper_motion(client, fake_build, tmp_path):
    cat, _, pm = _write_preset(tmp_path)
    r = client.get("/api/blink?ra=269.44629&dec=4.767917&detector=2&mode=sum")
    assert r.status_code == 202
    _wait(client, r.json()["job_id"])
    call = fake_build.calls[0]
    assert (call["ra"], call["dec"]) == cat and call["pm"] == pm and call["mode"] == "sum"
