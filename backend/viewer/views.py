"""
Viewer API (#1), contract in plans/00_COMMON.md §6 and §16:

    GET /api/blink?ra=&dec=&fov=300&detector=all|1..6&mode=frames|diff|sum[&name=]
        200 + response (preset or cached)  |  202 {job_id, status, progress, stage}
        with &only_cached=1: 200 or 204 (not cached), never starts a job (home page thumbnails)
    GET /api/blink/status/<job_id>   {job_id, status, progress, stage, result | error_code}
    GET /api/frame/<id>.png          PNG

Errors are {"error_code": "<machine code>"}; the frontend translates them.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import math

from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from core import blink, config

from . import jobs, store

MODES = ("frames", "diff", "sum")
DEFAULT_FOV = 300.0
MAX_NAME_LEN = 80


def _error(code: str, status: int) -> JsonResponse:
    return JsonResponse({"error_code": code}, status=status)


def _number(raw: str | None) -> float | None:
    """A finite float, or None for missing, malformed, NaN and Infinity."""
    try:
        v = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _parse(q) -> tuple[float, float, float, int | str, str, str | None] | str:
    """Validated (ra, dec, fov, detector, mode, name), or an error code."""
    ra, dec = _number(q.get("ra")), _number(q.get("dec"))
    if ra is None or dec is None or not (0 <= ra < 360) or not (-90 <= dec <= 90):
        return "invalid_coordinates"
    fov = _number(q.get("fov", str(DEFAULT_FOV)))
    if fov is None or fov <= 0:
        return "invalid_parameters"
    if fov > config.FOV_MAX_ARCSEC:
        return "fov_too_large"
    det_raw = q.get("detector", "all")
    if det_raw == "all":
        detector: int | str = "all"
    elif det_raw in ("1", "2", "3", "4", "5", "6"):
        detector = int(det_raw)
    else:
        return "invalid_parameters"
    mode = q.get("mode", "frames")
    if mode not in MODES:
        return "invalid_parameters"
    name = (q.get("name") or "").strip()[:MAX_NAME_LEN] or None
    return ra, dec, round(fov, 1), detector, mode, name


@require_GET
def blink_view(request):
    parsed = _parse(request.GET)
    if isinstance(parsed, str):
        return _error(parsed, 400)
    ra, dec, fov, detector, mode, name = parsed

    # A request near a preset target is computed exactly like the preset: catalog coordinates
    # plus proper motion, so the star stays in the frame and the rings are drawn.
    preset = store.match_preset(ra, dec)
    pm = None
    if preset:
        cached = store.preset_response(preset, fov, detector, mode)
        if cached:
            return JsonResponse(cached)
        ra, dec, pm, name = preset.ra, preset.dec, preset.pm, name or preset.name

    key = store.request_key(ra, dec, fov, detector, mode)
    cached = store.load_result(key)
    if cached:
        return JsonResponse(cached)

    if request.GET.get("only_cached") == "1":   # thumbnails: answer from the cache or not at all
        return HttpResponse(status=204)          # "nothing yet" is not an error (keeps the browser console clean)

    def work(progress):
        response, frames = blink.build_blink(ra, dec, fov, detector, mode, name=name, pm=pm, progress=progress)
        store.save_result(key, response, frames)
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
def status_view(request, job_id: str):
    job = jobs.get(job_id)
    if job is None:
        return _error("not_found", 404)
    return JsonResponse(job.payload())


@require_GET
def frame_view(request, fid: str):
    try:
        path = store.frame_file(fid)
    except blink.BlinkError:
        return _error("not_found", 404)
    resp = FileResponse(path.open("rb"), content_type="image/png")
    resp["Cache-Control"] = "public, max-age=86400, immutable"  # the id is a hash of the frame's inputs
    return resp
