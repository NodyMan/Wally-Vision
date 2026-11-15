"""
Where finished blinks come from:

1. presets — JSON + PNG committed to viewer/static_cache/<slug>/ (written by scripts/prefetch.py from real IRSA data);
   they survive a wiped disk on the free hosting tier and always answer 200;
2. the file cache — CACHE_DIR/blink/<key>.json + CACHE_DIR/frames/<id>.png, written by finished jobs.

Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path

from core import blink, config
from core.targets import PRESET_PM, ProperMotion

log = logging.getLogger(__name__)

STATIC_CACHE = Path(__file__).resolve().parent / "static_cache"
PRESET_MATCH_ARCSEC = 20.0    # a request this close to a preset target is that preset
_HEX = set("0123456789abcdef")


@dataclass(frozen=True)
class Preset:
    slug: str
    name: str | None
    ra: float                # coordinates to pass to build_blink (catalog ones when there is proper motion)
    dec: float
    pm: ProperMotion | None
    centers: tuple[tuple[float, float], ...]   # every position that should match this preset
    responses: tuple[dict, ...]


_lock = threading.Lock()
_presets: list[Preset] | None = None
_signature: tuple = ()
_preset_frames: dict[str, Path] = {}


def _sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    dra = (ra1 - ra2 + 180.0) % 360.0 - 180.0
    return 3600.0 * math.hypot(dra * math.cos(math.radians((dec1 + dec2) / 2)), dec1 - dec2)


def _files_signature() -> tuple:
    """Names and modification times of the preset JSON files: a re-run of prefetch.py changes it."""
    if not STATIC_CACHE.is_dir():
        return ()
    return tuple(sorted((str(p), p.stat().st_mtime_ns) for p in STATIC_CACHE.glob("*/blink_*.json")))


def _load() -> list[Preset]:
    global _presets, _signature
    with _lock:
        sig = _files_signature()
        if _presets is not None and sig == _signature:
            return _presets
        _signature = sig
        found: list[Preset] = []
        frames: dict[str, Path] = {}
        for d in sorted(STATIC_CACHE.iterdir()) if STATIC_CACHE.is_dir() else []:
            responses = []
            for p in sorted(d.glob("blink_*.json")):
                try:
                    responses.append(json.loads(p.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    log.warning("skipping unreadable preset file %s", p.name)
            if not responses:
                continue
            for png in (d / "frames").glob("*.png"):
                if set(png.stem) <= _HEX:
                    frames[png.stem] = png
            t = responses[0]["target"]
            centers = [(t["ra"], t["dec"])]
            ra, dec = t["ra"], t["dec"]
            pm = PRESET_PM.get(d.name)
            if pm and t.get("catalog_ra") is not None:
                ra, dec = t["catalog_ra"], t["catalog_dec"]
                centers.append((ra, dec))
            else:
                pm = None
            found.append(Preset(d.name, t.get("name"), ra, dec, pm, tuple(centers), tuple(responses)))
        _preset_frames.clear()
        _preset_frames.update(frames)
        _presets = found
        return found


def reload() -> None:
    """Forget loaded presets (tests, or after prefetch.py has written new ones)."""
    global _presets
    with _lock:
        _presets = None


def match_preset(ra: float, dec: float) -> Preset | None:
    """The preset whose target (catalogue or SPHEREx-epoch position) is within PRESET_MATCH_ARCSEC."""
    for p in _load():
        if any(_sep_arcsec(ra, dec, cra, cdec) <= PRESET_MATCH_ARCSEC for cra, cdec in p.centers):
            return p
    return None


def preset_response(preset: Preset, fov: float, detector: int | str, mode: str) -> dict | None:
    """
    A cached preset response for exactly this request, or None (then the request is computed as usual).
    Never substitutes another band or field of view: different detectors must not be mixed (COMMON §13).
    `detector="all"` matches only a response that holds several bands.
    """
    for r in preset.responses:
        if r.get("mode") != mode or r.get("fov_arcsec") != fov:
            continue
        dets = {f["detector"] for f in r["frames"]}
        if (detector == "all" and len(dets) > 1) or dets == {detector}:
            return r
    return None


def request_key(ra: float, dec: float, fov: float, detector: int | str, mode: str) -> str:
    return hashlib.sha1(f"{ra:.5f}|{dec:.5f}|{fov:g}|{detector}|{mode}".encode()).hexdigest()[:24]


def _result_path(key: str) -> Path:
    return config.CACHE_DIR / "blink" / f"{key}.json"


def load_result(key: str) -> dict | None:
    """A cached response, but only if every frame it points to is still on disk."""
    try:
        resp = json.loads(_result_path(key).read_text(encoding="utf-8"))
        for f in resp["frames"]:
            blink.frame_path(f["id"])
        return resp
    except (OSError, ValueError, KeyError, blink.BlinkError):
        return None


def save_result(key: str, response: dict, frames: dict[str, bytes]) -> None:
    p = _result_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    blink.save_frames(frames)                     # frames first: a result must never point at missing PNGs
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def frame_file(fid: str) -> Path:
    """First look in committed preset frames, then in the local runtime cache."""
    _load()
    if fid in _preset_frames:
        return _preset_frames[fid]
    return blink.frame_path(fid)
