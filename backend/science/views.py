"""
Science API (plan #2), built on real SPHEREx and catalog data only — nothing is simulated.

    GET /api/catalog?ra=&dec=&fov=300&source=all|gaia|catwise
        Gaia DR3 + CatWISE2020 sources on the blink grid centred on (ra, dec) = blink.target.
    GET /api/spectrum?ra=&dec=[&cra=&cdec=&fov=300]
        one brightness point per exposure, across all six bands → preview spectrum
    GET /api/lightcurve?ra=&dec=&detector=1..6[&cra=&cdec=&fov=300]
        the same measurement over time in one band → preview light curve

(ra, dec) is the point to measure; (cra, cdec) is the centre of the field being viewed (blink.target), so
that the cutouts already downloaded for the blink are reused. Spectrum and light curve answer 200 from
cache or 202 + job_id; poll /api/blink/status/<job_id> exactly like /api/blink.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from core import blink, catalogs, config, photometry, spherex
from core.targets import propagate
from viewer import jobs, store
from viewer.views import _error, _number

log = logging.getLogger(__name__)

SPECTRUM_PER_EPOCH = 2      # images per epoch and band: 6 bands × ~3 epochs × 2 ≈ 36 cutouts on a cold request
LIGHTCURVE_PER_EPOCH = config.MAX_PER_EPOCH   # same selection as the blink → cutouts come from the cache
TRACK_RADIUS_ARCSEC = 20.0
TRACK_MIN_PM_MAS = 1000.0   # follow only real movers; RW Aur and R Dra barely move  # a point this close to a moving preset target is that target: follow its motion
# Molecules whose absorption shows up in cold atmospheres; names and explanations are on the frontend (i18n).
FEATURES = [{"key": "h2o", "wavelength_um": 3.0}, {"key": "ch4", "wavelength_um": 3.3},
            {"key": "co2", "wavelength_um": 4.27}, {"key": "co", "wavelength_um": 4.67}]
METHOD = {"box_px": 3, "background_ring_px": [photometry.SKY_INNER, photometry.SKY_OUTER], "unit": "MJy/sr"}


def _point(q, a: str, b: str) -> tuple[float, float] | None:
    ra, dec = _number(q.get(a)), _number(q.get(b))
    if ra is None or dec is None or not (0 <= ra < 360) or not (-90 <= dec <= 90):
        return None
    return ra, dec


def _fov(q) -> float | str:
    fov = _number(q.get("fov", "300"))
    if fov is None or fov <= 0:
        return "invalid_parameters"
    return "fov_too_large" if fov > config.FOV_MAX_ARCSEC else round(fov, 1)


@require_GET
def catalog_view(request):
    pos, fov = _point(request.GET, "ra", "dec"), _fov(request.GET)
    if pos is None:
        return _error("invalid_coordinates", 400)
    if isinstance(fov, str):
        return _error(fov, 400)
    source = request.GET.get("source", "all")
    if source not in ("all", "gaia", "catwise"):
        return _error("invalid_parameters", 400)
    try:
        raw = catalogs.fetch(pos[0], pos[1], fov, allow_download=jobs.ALLOW_COLD)
    except Exception:  # noqa: BLE001 — IRSA TAP is slow or down; the viewer works without the overlay
        log.warning("catalog query failed", exc_info=True)
        return _error("catalog_unavailable", 502)
    data = catalogs.project(raw, pos[0], pos[1], fov)
    if source != "all":
        data["sources"] = [s for s in data["sources"] if s["catalog"] == source]
    return JsonResponse(data)


def _series_view(request, kind: str):
    q = request.GET
    pos = _point(q, "ra", "dec")
    if pos is None:
        return _error("invalid_coordinates", 400)
    centre = pos
    if q.get("cra") is not None or q.get("cdec") is not None:
        centre = _point(q, "cra", "cdec")
        if centre is None:
            return _error("invalid_coordinates", 400)
    fov = _fov(q)
    if isinstance(fov, str):
        return _error(fov, 400)
    detector = None
    if kind == "lightcurve":
        if q.get("detector") not in ("1", "2", "3", "4", "5", "6"):
            return _error("invalid_parameters", 400)
        detector = int(q["detector"])

    # A moving preset target: use the same field centre as its blink and follow the target between dates.
    pm = None
    preset = store.match_preset(*centre)
    if preset and preset.pm:
        centre = propagate(preset.ra, preset.dec, preset.pm, config.SPHEREX_MID_EPOCH)
        fast = math.hypot(preset.pm.pmra_mas_yr, preset.pm.pmdec_mas_yr) >= TRACK_MIN_PM_MAS
        if fast and store._sep_arcsec(pos[0], pos[1], centre[0], centre[1]) <= TRACK_RADIUS_ARCSEC:
            pos, pm = (preset.ra, preset.dec), preset.pm

    key = hashlib.sha1(f"v2|{kind}|{pos[0]:.6f}|{pos[1]:.6f}|{centre[0]:.6f}|{centre[1]:.6f}|{fov:g}|{detector}|"
                       f"{bool(pm)}".encode()).hexdigest()[:24]
    path = config.CACHE_DIR / "science" / f"{key}.json"
    for candidate in (config.SHIPPED_DIR / "science" / f"{key}.json", path):
        try:
            cached = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if "error_code" in cached:          # a remembered verdict such as target_saturated
            return _error(cached["error_code"], 422)
        return JsonResponse(cached)

    def work(progress):
        progress("search", 0.02)
        try:
            metas = spherex.find_images(*centre)
        except Exception as e:  # noqa: BLE001
            raise blink.BlinkError("irsa_timeout", str(e)) from e
        if kind == "spectrum":
            chosen = [m for d in range(1, 7) for m in photometry.pick_images(metas, d, SPECTRUM_PER_EPOCH)]
        else:
            chosen = photometry.pick_images(metas, detector, LIGHTCURVE_PER_EPOCH)
        if not chosen:
            raise blink.BlinkError("no_data")
        size = fov * config.CUTOUT_MARGIN
        points = photometry.series(chosen, pos[0], pos[1],
                                   lambda m: spherex.fetch_cutout(m, centre[0], centre[1], size),
                                   pm=pm, progress=progress)
        saturated = [p for p in points if p.get("saturated")]
        points = [p for p in points if not p.get("saturated")]
        flagged = sum(1 for p in points if p["flagged"])
        # a bright star (RW Aur, R Dra in D2) is saturated in SPHEREx: its brightness cannot be measured here
        if (saturated or flagged) and len(saturated) + flagged >= photometry.SATURATED_SHARE * (len(saturated) + len(points)):
            path.parent.mkdir(parents=True, exist_ok=True)      # remember it: the answer will not change
            path.write_text(json.dumps({"error_code": "target_saturated"}), encoding="utf-8")
            raise blink.BlinkError("target_saturated")
        if kind == "spectrum":
            points = sorted((p for p in points if p["wavelength_um"] is not None),
                            key=lambda p: p["wavelength_um"])
        if not points:
            raise blink.BlinkError("no_data")
        response = {"points": points, "quality": "preview", "method": METHOD,
                    "target": {"ra": round(pos[0], 6), "dec": round(pos[1], 6), "moving": bool(pm)},
                    "n_requested": len(chosen)}
        if kind == "spectrum":
            response["features"] = FEATURES
        else:
            wls = [p["wavelength_um"] for p in points if p["wavelength_um"] is not None]
            response["detector"] = detector
            response["wavelength_span_um"] = [min(wls), max(wls)] if wls else None
        if all(math.isfinite(p["flux"]) for p in points):
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(response), encoding="utf-8")
            tmp.replace(path)
        progress("done", 1.0)
        return response

    try:
        job = jobs.submit(key, work)
    except jobs.ColdDisabled:   # small demo server: only cached fields (COMMON §16, free hosting)
        return _error("cold_disabled", 503)
    except jobs.QueueFull:
        resp = _error("busy", 429)
        resp["Retry-After"] = "30"
        return resp
    return JsonResponse(job.payload(), status=202)


@require_GET
def spectrum_view(request):
    return _series_view(request, "spectrum")


@require_GET
def lightcurve_view(request):
    return _series_view(request, "lightcurve")
