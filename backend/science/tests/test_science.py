"""
Science tests without network:  cd backend && python -m pytest science/tests -q
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import time

import pytest
from django.test import Client

from core import catalogs, config, grid, photometry, spherex
from core.targets import mjd_to_year, propagate
from core.tests import synth
from viewer import store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(store, "STATIC_CACHE", tmp_path / "static_cache")
    store.reload()
    yield Client()
    store.reload()


def _wait(client, job_id):
    t0 = time.time()
    while time.time() - t0 < 20:
        body = client.get(f"/api/blink/status/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.02)
    raise AssertionError("job did not finish")


# ───────── photometry ─────────

def test_measure_finds_the_star_and_empty_sky():
    meta = synth.make_metas()[0]
    hdul = synth.make_loader()(meta)
    star = photometry.measure(hdul, *propagate(synth.RA0, synth.DEC0, synth.PM, mjd_to_year(meta.date_mjd)))
    sky = photometry.measure(hdul, synth.RA0 + 30 / 3600, synth.DEC0 - 10 / 3600)
    assert star["flux"] > 30 and star["flux"] / star["err"] > 20
    assert abs(sky["flux"]) < 5 * sky["err"] + 1
    assert star["flagged"] is False                       # SOURCE alone is not a defect
    assert photometry.measure(hdul, synth.RA0 + 1.0, synth.DEC0) is None   # off the image


def test_series_follows_a_moving_target():
    metas = photometry.pick_images(synth.make_metas(), 6, 3)
    assert len(metas) == 9 and photometry.pick_images(synth.make_metas(), 2, 3) == []
    tracked = photometry.series(metas, synth.RA0, synth.DEC0, synth.make_loader(), pm=synth.PM)
    fixed = photometry.series(metas, synth.RA0, synth.DEC0, synth.make_loader())
    assert len(tracked) == 9 and [p["date_mjd"] for p in tracked] == sorted(p["date_mjd"] for p in tracked)
    # the star drifts 10″/yr: following it keeps the flux, staring at the old position loses it
    assert min(p["flux"] for p in tracked) > 30
    assert fixed[-1]["flux"] < 0.8 * tracked[-1]["flux"]      # 1.7 px away after a year: partly out of the box


# ───────── catalogs ─────────

RAW = [
    {"id": "gaia:1", "catalog": "gaia", "ra": 10.0, "dec": 20.0, "epoch": 2016.0, "pmra": 0.0, "pmdec": 0.0,
     "mag": 12.0, "mag_band": "G"},
    {"id": "gaia:2", "catalog": "gaia", "ra": 10.0, "dec": 20.0 - 99.0 / 3600, "epoch": 2016.0, "pmra": 0.0,
     "pmdec": 10000.0, "mag": 9.5, "mag_band": "G"},                       # fast star, 10″/yr north
    {"id": "catwise:a", "catalog": "catwise", "ra": 10.0, "dec": 20.0 + 1.0 / 3600, "epoch": 2015.405,
     "pmra": None, "pmdec": None, "mag": 11.0, "mag_band": "W2"},           # 1″ from gaia:1
    {"id": "catwise:b", "catalog": "catwise", "ra": 10.01, "dec": 20.01, "epoch": 2015.405, "pmra": 0.0,
     "pmdec": 0.0, "mag": 14.0, "mag_band": "W2"},                          # nothing in Gaia nearby
    {"id": "gaia:far", "catalog": "gaia", "ra": 10.3, "dec": 20.0, "epoch": 2016.0, "pmra": 0.0, "pmdec": 0.0,
     "mag": 15.0, "mag_band": "G"},                                         # outside the field
]


def test_project_places_sources_on_the_blink_grid():
    data = catalogs.project(RAW, 10.0, 20.0, 300, epoch=2025.9)
    by_id = {s["id"]: s for s in data["sources"]}
    assert set(by_id) == {"gaia:1", "gaia:2", "catwise:a", "catwise:b"}
    assert (by_id["gaia:1"]["x"], by_id["gaia:1"]["y"]) == (24.0, 24.0)
    wcs, shape = grid.make_grid(10.0, 20.0, 300)
    assert data["grid_id"] == grid.grid_payload(wcs, shape)["id"]
    # 9.9 yr × 10″ = 99″: the fast star has arrived at the centre and moves up (north) by 10″/6.15″ px a year
    fast = by_id["gaia:2"]
    assert fast["y"] == pytest.approx(24.0, abs=0.05)
    assert fast["dy_per_yr"] == pytest.approx(-10.0 / 6.15, abs=0.01) and abs(fast["dx_per_yr"]) < 0.01
    assert by_id["catwise:a"]["match_status"] == "gaia_match"
    assert by_id["catwise:b"]["match_status"] == "no_gaia_match"
    assert by_id["catwise:a"]["pmra"] is None and by_id["catwise:a"]["dx_per_yr"] == 0


def test_catwise_motion_is_converted_from_arcsec(monkeypatch):
    monkeypatch.setattr(catalogs, "_tap", lambda q: [
        {"source_name": "J1", "ra": "133.8", "dec": "-7.2", "meanobsmjd": "57170.0", "pmra": "-8.118",
         "pmdec": "0.680", "sigpmra": "0.19", "sigpmdec": "0.26", "w2mpro_pm": "14.0"},
        {"source_name": "J2", "ra": "", "dec": "", "meanobsmjd": "", "pmra": "", "pmdec": "", "sigpmra": "",
         "sigpmdec": "", "w2mpro_pm": ""}])
    rows = catalogs.query_catwise(133.8, -7.2, 0.05)
    assert len(rows) == 1 and rows[0]["pmra"] == pytest.approx(-8118.0) and rows[0]["pmdec"] == pytest.approx(680.0)
    assert rows[0]["epoch"] == pytest.approx(2015.405, abs=0.01) and rows[0]["pm_sigma"] > 20


def test_a_fast_mover_listed_twice_is_merged_and_marked_as_moving():
    # one object moving 8 arcsec/yr north, catalogued at two mean epochs (as CatWISE does for WISE 0855)
    def entry(name, epoch):
        return {"id": name, "catalog": "catwise", "ra": 50.0, "dec": 10.0 + 8.0 * (epoch - 2025.9) / 3600,
                "epoch": epoch, "pmra": 0.0, "pmdec": 8000.0, "pm_sigma": 30.0, "mag": 14.0, "mag_band": "W2"}
    slow = {"id": "slow", "catalog": "catwise", "ra": 50.01, "dec": 10.0, "epoch": 2015.4, "pmra": 60.0,
            "pmdec": 0.0, "pm_sigma": 1.2, "mag": 16.0, "mag_band": "W2"}
    data = catalogs.project([entry("a", 2012.0), entry("b", 2018.0), slow], 50.0, 10.0, 300, epoch=2025.9)
    by_id = {s["id"]: s for s in data["sources"]}
    assert set(by_id) == {"a", "slow"}
    assert (by_id["a"]["x"], by_id["a"]["y"]) == pytest.approx((24.0, 24.0), abs=0.02)
    assert by_id["a"]["moving"] is True and by_id["a"]["match_status"] == "no_gaia_match"
    assert by_id["slow"]["moving"] is False


def test_false_fast_sources_around_a_saturated_star_are_dropped():
    star = {"id": "gaia:bright", "catalog": "gaia", "ra": 80.0, "dec": 5.0, "epoch": 2016.0, "pmra": 0.0,
            "pmdec": 0.0, "pm_sigma": None, "mag": 8.2, "mag_band": "G"}

    def cw(name, dra_arcsec, pm):
        return {"id": name, "catalog": "catwise", "ra": 80.0 + dra_arcsec / 3600, "dec": 5.0, "epoch": 2015.4,
                "pmra": 0.0, "pmdec": pm, "pm_sigma": 50.0, "mag": 12.0, "mag_band": "W2"}
    raw = [star, cw("ghost", 60.0, 300.0), cw("still", 70.0, 5.0)]
    data = catalogs.project(raw, 80.0, 5.0, 300, epoch=2025.9)
    assert {s["id"] for s in data["sources"]} == {"gaia:bright", "still"} and data["dropped_near_bright_star"] == 1
    # without the bright star the same fast source is kept and marked
    alone = catalogs.project(raw[1:], 80.0, 5.0, 300, epoch=2025.9)
    kept = {s["id"]: s for s in alone["sources"]}
    assert kept["ghost"]["moving"] is True and alone["dropped_near_bright_star"] == 0


# ───────── API ─────────

def test_catalog_endpoint(client, monkeypatch):
    monkeypatch.setattr(catalogs, "fetch", lambda ra, dec, fov: RAW)
    r = client.get("/api/catalog?ra=10&dec=20&fov=300")
    assert r.status_code == 200 and len(r.json()["sources"]) == 4 and r.json()["releases"]["gaia"] == "Gaia DR3"
    only = client.get("/api/catalog?ra=10&dec=20&source=catwise").json()["sources"]
    assert {s["catalog"] for s in only} == {"catwise"}
    assert client.get("/api/catalog?ra=10&dec=120").json() == {"error_code": "invalid_coordinates"}
    assert client.get("/api/catalog?ra=10&dec=20&source=x").status_code == 400

    def down(*a):
        raise OSError("IRSA is down")
    monkeypatch.setattr(catalogs, "fetch", down)
    r = client.get("/api/catalog?ra=10&dec=20")
    assert r.status_code == 502 and r.json() == {"error_code": "catalog_unavailable"}


def test_spectrum_and_lightcurve_run_as_jobs_and_are_cached(client, monkeypatch):
    calls = []
    load = synth.make_loader()
    wl = iter(range(1000))
    monkeypatch.setattr(spherex, "find_images", lambda ra, dec: synth.make_metas(6) + synth.make_metas(2))
    monkeypatch.setattr(spherex, "fetch_cutout", lambda m, ra, dec, size: (calls.append(size), load(m))[1])
    monkeypatch.setattr(photometry.imaging, "pixel_wavelength", lambda h, x, y: (1.0 + next(wl) * 0.01, 0.03))

    url = f"/api/spectrum?ra={synth.RA0}&dec={synth.DEC0}&fov=300"
    r = client.get(url)
    assert r.status_code == 202
    done = _wait(client, r.json()["job_id"])
    res = done["result"]
    assert done["status"] == "done" and res["quality"] == "preview"
    assert len(res["points"]) == 12 and {p["detector"] for p in res["points"]} == {2, 6}   # 2 bands × 3 epochs × 2
    assert [p["wavelength_um"] for p in res["points"]] == sorted(p["wavelength_um"] for p in res["points"])
    assert {f["key"] for f in res["features"]} == {"h2o", "ch4", "co2", "co"}
    assert set(calls) == {300 * config.CUTOUT_MARGIN}        # same cutout size as the blink → shared cache
    assert client.get(url).status_code == 200 and client.get(url).json() == res

    r = client.get(f"/api/lightcurve?ra={synth.RA0}&dec={synth.DEC0}&detector=6")
    lc = _wait(client, r.json()["job_id"])["result"]
    assert lc["detector"] == 6 and len(lc["points"]) == 24 and lc["wavelength_span_um"][0] < lc["wavelength_span_um"][1]
    assert [p["date_mjd"] for p in lc["points"]] == sorted(p["date_mjd"] for p in lc["points"])

    assert client.get(f"/api/lightcurve?ra={synth.RA0}&dec={synth.DEC0}").status_code == 400   # detector required
    assert client.get("/api/spectrum?ra=x&dec=1").json() == {"error_code": "invalid_coordinates"}
    assert client.get("/api/spectrum?ra=1&dec=1&cra=400&cdec=1").status_code == 400


def test_no_images_is_an_error_code(client, monkeypatch):
    monkeypatch.setattr(spherex, "find_images", lambda ra, dec: [])
    body = _wait(client, client.get("/api/spectrum?ra=1&dec=1").json()["job_id"])
    assert body["status"] == "error" and body["error_code"] == "no_data"
