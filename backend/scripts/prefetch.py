"""
Прогрев кэша 5 пресетов: считает blink на реальных данных IRSA и кладёт готовые JSON + PNG в
backend/viewer/static_cache/ (это коммитим — диск бесплатного Render стирается; FITS НЕ коммитим).

Запуск (из папки backend):
    set SKYBLINK_CACHE=C:\\skyblink_cache          (Windows; вне OneDrive)
    python scripts/prefetch.py                     все 5 пресетов
    python scripts/prefetch.py wise-0855 barnards-star   выбранные

IRSA во время хакатона отвечает 503 — скрипт можно перезапускать: скачанное берётся из кэша.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import blink  # noqa: E402
from core.targets import PRESET_PM  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

OUT = Path(__file__).resolve().parent.parent / "viewer" / "static_cache"

# slug: (имя для SIMBAD, запасные ra/dec J2000, detector, mode, fov, max_per_epoch, wl_auto)
# wl_auto = width (µm) of the common wavelength window: every diff preset compares epochs only inside it (LVF)
# max_per_epoch = 8: IRSA answered ~1 cutout/min on 15 Nov; more images per visit did not finish in time
PRESETS = {
    "wise-0855": ("WISE J085510.83-071442.5", 133.79513, -7.24515, 6, "diff", 300, 16, 0.1),
    "barnards-star": ("Barnard's Star", 269.452083, 4.693364, 2, "diff", 300, 8, 0.1),
    "epsilon-indi-b": ("eps Ind B", 331.04383, -56.78269, 6, "diff", 300, 8, 0.1),
    "rw-aurigae": ("RW Aur", 76.95642, 30.40141, 2, "frames", 300, 8, 0.05),
    "r-draconis": ("R Dra", 248.16738, 66.75489, 2, "frames", 300, 8, 0.05),
}

# Extra cached views: (mode, detector, max_per_epoch). "sum" over all six bands powers the wavelength slider:
# WISE 0855 is invisible at 1 µm and bright at 4.6 µm. Run them with:  python scripts/prefetch.py --extra wise-0855
EXTRA = {
    "wise-0855": [("sum", "all", 6)],
    "epsilon-indi-b": [("sum", "all", 6)],
}


def resolve(name: str, ra: float, dec: float) -> tuple[float, float]:
    try:
        from astropy.coordinates import SkyCoord
        c = SkyCoord.from_name(name)
        # 6 decimals (0.004″): the API works with the same rounded values, so cutouts are shared with it
        return round(float(c.ra.deg), 6), round(float(c.dec.deg), 6)
    except Exception as e:  # noqa: BLE001
        print(f"  ! SIMBAD недоступен ({e.__class__.__name__}) — запасные координаты")
        return ra, dec


def cached_coords(slug: str) -> tuple[float, float] | None:
    """Catalogue coordinates used by the last run of this preset. Reusing them keeps the cutout URLs (and so the
    downloaded cutouts in CACHE_DIR) identical; asking SIMBAD again changes the last digits and re-downloads all."""
    for j in sorted((OUT / slug).glob("blink_*.json")):
        try:
            t = json.loads(j.read_text(encoding="utf-8"))["target"]
        except (OSError, ValueError, KeyError):
            continue
        ra, dec = t.get("catalog_ra") or t.get("ra"), t.get("catalog_dec") or t.get("dec")
        if ra is not None and dec is not None:
            return float(ra), float(dec)
    return None


def coords(slug: str, name: str, ra0: float, dec0: float) -> tuple[float, float]:
    """
    Catalogue coordinates for the preset.
    With a proper motion, the coordinates MUST be at the motion's reference epoch, so the listed ones are used:
    SIMBAD answers at epoch J2000, and for WISE 0855 (listed at 2010.5) that mistake put the centre 85″ off.
    A previous run's coordinates are reused only when they agree with the listed ones within 1″ (keeps the
    downloaded cutouts usable); without a proper motion, SIMBAD is fine.
    """
    cached = cached_coords(slug)
    if slug in PRESET_PM:
        if cached and abs(cached[0] - ra0) * 3600 < 1.0 and abs(cached[1] - dec0) * 3600 < 1.0:
            return cached
        return ra0, dec0
    return cached or resolve(name, ra0, dec0)


def run(slug: str) -> None:
    name, ra0, dec0, det, mode, fov, mpe, wla = PRESETS[slug]
    ra, dec = coords(slug, name, ra0, dec0)
    t0 = time.time()
    print(f"\n▶ {slug}: D{det} {mode}, FOV {fov}″")
    for m in ("frames", mode) if mode != "frames" else ("frames",):  # пресетам нужны и кадры, и diff
        resp, frames = blink.build_blink(ra, dec, fov, det, m, name=name, pm=PRESET_PM.get(slug),
                                         max_per_epoch=mpe, wl_auto=wla,
                                         progress=lambda s, p: print(f"  {p:4.0%} {s}", flush=True))
        d = OUT / slug
        (d / "frames").mkdir(parents=True, exist_ok=True)
        for fid, png in frames.items():
            (d / "frames" / f"{fid}.png").write_bytes(png)
        (d / f"blink_{m}_d{det}.json").write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        blink.save_frames(frames)
        warn = ", ".join(w["code"] for w in resp["warnings"]) or "—"
        print(f"  ✓ {m}: {len(resp['frames'])} кадров, предупреждения: {warn}")
    print(f"  готово за {time.time() - t0:.0f} с → {d}")


def run_extra(slug: str) -> None:
    name, ra0, dec0, _det, _mode, fov, _mpe, _wla = PRESETS[slug]
    ra, dec = coords(slug, name, ra0, dec0)
    for mode, det, mpe in EXTRA.get(slug, []):
        t0 = time.time()
        print(f"\n▶ {slug}: {mode}, detector={det}, FOV {fov}″")
        resp, frames = blink.build_blink(ra, dec, fov, det, mode, name=name, pm=PRESET_PM.get(slug),
                                         max_per_epoch=mpe,
                                         progress=lambda s, p: print(f"  {p:4.0%} {s}", flush=True))
        d = OUT / slug
        (d / "frames").mkdir(parents=True, exist_ok=True)
        for fid, png in frames.items():
            (d / "frames" / f"{fid}.png").write_bytes(png)
        tag = f"d{det}" if det != "all" else "dall"
        (d / f"blink_{mode}_{tag}.json").write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        blink.save_frames(frames)
        bands = sorted({f["detector"] for f in resp["frames"]})
        warn = ", ".join(w["code"] for w in resp["warnings"]) or "—"
        print(f"  ✓ {mode}/{det}: bands {bands}, warnings: {warn}, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s %(message)s")
    args = sys.argv[1:]
    extra = "--extra" in args
    slugs = [a for a in args if a != "--extra"] or list(PRESETS)
    for s in slugs:
        try:
            run_extra(s) if extra else run(s)
        except blink.BlinkError as e:
            print(f"  ✗ {s}: {e.code} {e.detail}")
