"""
Preview photometry on single SPHEREx exposures: one brightness measurement per image at a sky position.

Astronomy note. SPHEREx has no fixed filters: a linear variable filter (LVF) sits over each detector, so the
wavelength a source is seen at depends on where it falls on the detector. Each exposure therefore gives ONE
point of the source's spectrum (brightness at one wavelength, on one date). Many exposures → a spectrum.
The same list sorted by date is a light curve, but only points at similar wavelengths can be compared.

This is a PREVIEW (COMMON §13): the mean surface brightness in a 3×3 pixel box minus the local background,
with no PSF fitting and no aperture correction. Units stay MJy/sr. Responses are marked quality="preview".
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import concurrent.futures as cf
import threading
from typing import Callable, Sequence

import numpy as np
from astropy.wcs import WCS

from . import config, epochs, imaging
from .targets import ProperMotion, mjd_to_year, propagate

BOX_HALF = 1                 # 3×3 pixel box (18.45″ on a side; the SPHEREx PSF is about one pixel wide)
SKY_INNER, SKY_OUTER = 4, 7  # background ring, pixels from the centre
SATURATION_BITS = (1 << 1) | (1 << 26)   # OVERFLOW, BLOOM (Explanatory Supplement Table 16)
SATURATED_SHARE = 0.8        # this share of saturated or flagged points makes the series meaningless

Progress = Callable[[str, float], None]


def measure(hdul, ra: float, dec: float) -> dict | None:
    """
    Brightness at (ra, dec) on one cutout: {flux, err, wavelength_um, bandwidth_um, flagged}, or None when
    the position is off the image or has no valid pixels. flux/err are MJy/sr (box mean above background).
    """
    try:
        x, y = WCS(hdul["IMAGE"].header).world_to_pixel_values(ra, dec)
    except Exception:  # noqa: BLE001
        return None
    x, y = float(x), float(y)
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    ix, iy = int(round(x)), int(round(y))
    img = hdul["IMAGE"].data.astype("float64")
    ny, nx = img.shape
    if not (SKY_OUTER <= ix < nx - SKY_OUTER and SKY_OUTER <= iy < ny - SKY_OUTER):
        return None
    if "ZODI" in hdul and hdul["ZODI"].data is not None:
        img = img - hdul["ZODI"].data          # zodiacal light model is not subtracted in the archive images
    var = hdul["VARIANCE"].data.astype("float64") if "VARIANCE" in hdul else np.full_like(img, np.nan)

    box = (slice(iy - BOX_HALF, iy + BOX_HALF + 1), slice(ix - BOX_HALF, ix + BOX_HALF + 1))
    vals, vvar = img[box], var[box]
    ok = np.isfinite(vals)
    if ok.sum() < 5:
        # a bright star's core is blanked by the pipeline (OVERFLOW / BLOOM): say so instead of "no data"
        if "FLAGS" in hdul and np.any(hdul["FLAGS"].data[box].astype(np.int64) & SATURATION_BITS):
            return {"saturated": True}
        return None
    yy, xx = np.ogrid[:ny, :nx]
    r = np.hypot(xx - ix, yy - iy)
    ring = img[(r >= SKY_INNER) & (r <= SKY_OUTER)]
    ring = ring[np.isfinite(ring)]
    if ring.size < 10:
        return None
    sky = float(np.median(ring))
    flux = float(np.mean(vals[ok])) - sky
    good_var = vvar[ok & np.isfinite(vvar) & (vvar > 0)]
    # error of the box mean; if VARIANCE is unusable, fall back to the scatter of the background ring
    err = float(np.sqrt(good_var.sum()) / ok.sum()) if good_var.size == ok.sum() \
        else float(1.4826 * np.median(np.abs(ring - sky)) / np.sqrt(ok.sum()))
    flagged = False
    if "FLAGS" in hdul:
        mask = sum(1 << b for b in config.PHOTOMETRY_FLAG_POLICY["bits"])
        flagged = bool(np.any(hdul["FLAGS"].data[box].astype(np.int64) & mask))
    wl = imaging.pixel_wavelength(hdul, x, y)
    return {"flux": round(flux, 4), "err": round(err, 4),
            "wavelength_um": round(wl[0], 4) if wl else None,
            "bandwidth_um": round(wl[1], 4) if wl else None,
            "flagged": flagged}


def pick_images(metas: Sequence, detector: int, per_epoch: int) -> list:
    """Up to per_epoch images of one detector from every epoch, spread evenly in time (as the blink does)."""
    sel = [m for m in metas if m.detector == detector]
    return [m for e in epochs.group_epochs(sel) for m in epochs.limit_per_epoch(e, per_epoch)]


def series(metas: Sequence, ra: float, dec: float, loader: Callable, pm: ProperMotion | None = None,
           progress: Progress | None = None) -> list[dict]:
    """
    One measurement per image, sorted by date. `loader(meta)` returns the cutout (or None).
    With `pm`, (ra, dec) are catalog coordinates and the position is moved to the date of each image.
    """
    progress = progress or (lambda s, p: None)
    done, lock = [0], threading.Lock()
    total = max(len(metas), 1)

    def one(m):
        try:
            hdul = loader(m)
            if hdul is None:
                return None
            pra, pdec = propagate(ra, dec, pm, mjd_to_year(m.date_mjd)) if pm else (ra, dec)
            res = measure(hdul, pra, pdec)
            if res is None:
                return None
            if res.get("saturated"):
                return {"date_iso": m.date_iso, "date_mjd": round(m.date_mjd, 4), "detector": m.detector,
                        "obs_id": m.obs_id, "saturated": True}
            return {"date_iso": m.date_iso, "date_mjd": round(m.date_mjd, 4), "detector": m.detector,
                    "obs_id": m.obs_id, **res}
        finally:
            with lock:
                done[0] += 1
                progress(f"download:{len(metas)}", 0.05 + 0.9 * done[0] / total)

    progress(f"download:{len(metas)}", 0.05)
    with cf.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as ex:
        points = [p for p in ex.map(one, metas) if p]
    return sorted(points, key=lambda p: p["date_mjd"])
