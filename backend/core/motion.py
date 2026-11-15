"""
Measured motion of the target between two epochs: where the light actually is, not where we expect it.

Astronomy note. A SPHEREx pixel is 6.15″, and even the fastest nearby objects move only 1–2 pixels during
the mission. Blinking alone cannot prove a sub-pixel shift; a centroid can. The centroid is the
"centre of gravity" of the light: with a good signal it is accurate to a small fraction of a pixel.

Method (preview, documented in the API response):
  1. look near the position predicted from the catalogue proper motion, in the stacked image of each epoch;
  2. flux-weighted centroid inside r = 3.5 px, background = median of a ring at 5–8 px, five iterations;
  3. error = statistical error (image noise) and registration error (step 4) added in quadrature;
  4. the same measurement on the brightest other stars of the field. Their apparent shift is NOT motion
     (they are nearly stationary): it is our registration error, and it is reported next to the result.
Stacks are arrays in FITS order (row 0 at the bottom); everything returned is in canvas pixels (y down).
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import math

import numpy as np

R_APER = 3.5          # px, centroid aperture (2.5 px clips the PSF widened by reprojection: 8% bias in tests)
R_SKY = (5.0, 8.0)    # px, background ring
MIN_SNR = 5.0         # below this the target is "not detected" and no shift is reported
N_REF = 6             # reference stars used to estimate the registration error
REF_MIN_SNR = 15.0
REF_EXCLUDE_PX = 6.0  # reference stars must be this far from the target


def _noise(img: np.ndarray) -> float:
    v = img[np.isfinite(img)]
    if v.size < 20:
        return float("nan")
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


def centroid(img: np.ndarray, col: float, row: float, sigma: float) -> dict | None:
    """Flux-weighted centroid near (col, row) in array coordinates; None if too faint or off the image."""
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w]
    c, r = col, row
    for _ in range(5):
        d = np.hypot(xx - c, yy - r)
        ring = img[(d >= R_SKY[0]) & (d <= R_SKY[1]) & np.isfinite(img)]
        if ring.size < 8:
            return None
        sky = float(np.median(ring))
        sel = (d <= R_APER) & np.isfinite(img)
        if sel.sum() < 6:
            return None
        f = np.clip(img[sel] - sky, 0, None)
        total = float(f.sum())
        if total <= 0:
            return None
        nc = float((f * xx[sel]).sum() / total)
        nr = float((f * yy[sel]).sum() / total)
        if math.hypot(nc - col, nr - row) > 3.0:      # wandered off to another source
            return None
        c, r = nc, nr
    snr = total / (sigma * math.sqrt(sel.sum())) if sigma > 0 else 0.0
    if snr < MIN_SNR:
        return None
    ec = sigma * math.sqrt(float(((xx[sel] - c) ** 2).sum())) / total
    er = sigma * math.sqrt(float(((yy[sel] - r) ** 2).sum())) / total
    masked = bool(np.any(~np.isfinite(img[np.hypot(xx - c, yy - r) <= 1.5])))
    return {"col": c, "row": r, "err_col": ec, "err_row": er, "snr": snr, "core_masked": masked}


def masked_core_centre(img: np.ndarray, col: float, row: float) -> dict | None:
    """
    Saturated star: its core is masked (NaN) in every exposure, so there is no light to weigh. The masked blob
    itself follows the star, so its centre is measured instead: the NaN pixels connected to the predicted
    position within 5 px. Error per axis = pixel quantisation, 1/sqrt(12) px / sqrt(number of edge pixels).
    """
    h, w = img.shape
    c0, r0 = int(round(col)), int(round(row))
    if not (0 <= c0 < w and 0 <= r0 < h):
        return None
    nan = ~np.isfinite(img)
    seed = None
    for dr in range(-2, 3):           # nearest NaN pixel to the prediction
        for dc in range(-2, 3):
            r, c = r0 + dr, c0 + dc
            if 0 <= r < h and 0 <= c < w and nan[r, c] and (seed is None or abs(dr) + abs(dc) < seed[2]):
                seed = (r, c, abs(dr) + abs(dc))
    if seed is None:
        return None
    blob, todo = set(), [(seed[0], seed[1])]
    while todo:
        r, c = todo.pop()
        if (r, c) in blob or not (0 <= r < h and 0 <= c < w) or not nan[r, c] or math.hypot(c - col, r - row) > 5:
            continue
        blob.add((r, c))
        todo += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    if len(blob) < 5:
        return None
    rows = np.array([r for r, _ in blob], float)
    cols = np.array([c for _, c in blob], float)
    edge = sum(1 for r, c in blob if any((r + a, c + b) not in blob for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    err = (1 / math.sqrt(12)) / math.sqrt(max(edge, 1))
    return {"col": float(cols.mean()), "row": float(rows.mean()), "err_col": err, "err_row": err,
            "snr": float("nan"), "core_masked": True, "masked_pixels": len(blob)}


def _reference_peaks(img: np.ndarray, sigma: float, avoid: tuple[float, float]) -> list[tuple[int, int]]:
    """Brightest isolated local maxima, away from the target and the edges."""
    h, w = img.shape
    a = np.where(np.isfinite(img), img, -np.inf)
    peaks = []
    for r in range(8, h - 8):
        for c in range(8, w - 8):
            v = a[r, c]
            if v < REF_MIN_SNR * sigma or v < a[r - 1:r + 2, c - 1:c + 2].max():
                continue
            if math.hypot(c - avoid[0], r - avoid[1]) < REF_EXCLUDE_PX:
                continue
            peaks.append((v, c, r))
    peaks.sort(reverse=True)
    out: list[tuple[int, int]] = []
    for _, c, r in peaks:
        if all(math.hypot(c - c2, r - r2) > 5 for c2, r2 in out):
            out.append((c, r))
        if len(out) == N_REF:
            break
    return out


def measure_shift(early: np.ndarray, late: np.ndarray, xy_early: list[float], xy_late: list[float],
                  pixscale: float, years: float) -> dict | None:
    """
    Target shift between two epoch stacks of one detector, in arcsec, with the registration check.
    xy_* are the predicted canvas positions (target_xy). Returns None if the target is not detected.
    """
    h = early.shape[0]
    to_row = lambda y: h - 1 - y       # canvas y (down) → array row (up)
    s0, s1 = _noise(early), _noise(late)
    a = centroid(early, xy_early[0], to_row(xy_early[1]), s0)
    b = centroid(late, xy_late[0], to_row(xy_late[1]), s1)
    method = "light"
    if a is None or b is None:        # saturated core in either epoch: measure the masked core in both
        a = masked_core_centre(early, xy_early[0], to_row(xy_early[1]))
        b = masked_core_centre(late, xy_late[0], to_row(xy_late[1]))
        method = "masked_core"
    if a is None or b is None:
        return None

    dx = b["col"] - a["col"]                 # canvas x: same direction as columns
    dy = -(b["row"] - a["row"])              # canvas y is flipped
    shift_px = math.hypot(dx, dy)
    ex = math.hypot(a["err_col"], b["err_col"])
    ey = math.hypot(a["err_row"], b["err_row"])
    err_px = math.hypot(dx * ex, dy * ey) / shift_px if shift_px > 1e-6 else math.hypot(ex, ey)

    refs = []
    for c, r in _reference_peaks(early, s0, (a["col"], a["row"])):
        ra_ = centroid(early, c, r, s0)
        rb_ = centroid(late, c, r, s1)
        if ra_ and rb_ and not ra_["core_masked"] and not rb_["core_masked"]:
            refs.append(math.hypot(rb_["col"] - ra_["col"], rb_["row"] - ra_["row"]))
    ref_px = float(np.median(refs)) if refs else None
    total_err_px = math.hypot(err_px, ref_px or 0.0)

    edx, edy = xy_late[0] - xy_early[0], xy_late[1] - xy_early[1]
    # position angle, degrees east of north; on the canvas north is up (−y) and east is LEFT (−x)
    pa = lambda x, y: round(math.degrees(math.atan2(-x, -y)) % 360.0, 1)
    return {
        "from_xy": [round(a["col"], 2), round(h - 1 - a["row"], 2)],
        "to_xy": [round(b["col"], 2), round(h - 1 - b["row"], 2)],
        "shift_arcsec": round(shift_px * pixscale, 2),
        "shift_err_arcsec": round(total_err_px * pixscale, 2),
        "stat_err_arcsec": round(err_px * pixscale, 2),
        "pa_deg": pa(dx, dy),
        "expected_shift_arcsec": round(math.hypot(edx, edy) * pixscale, 2),
        "expected_pa_deg": pa(edx, edy),
        "years": round(years, 3),
        "snr": None if method == "masked_core" else [round(a["snr"], 1), round(b["snr"], 1)],
        "centroid_on": method,          # "light" or "masked_core" (saturated star)
        "core_masked": a["core_masked"] or b["core_masked"],
        "reference_shift_arcsec": None if ref_px is None else round(ref_px * pixscale, 2),
        "n_reference_stars": len(refs),
        "method": "flux-weighted centroid r=3.5 px, ring 5-8 px; error = statistical (+) registration, "
                  "registration = median apparent shift of bright field stars; preview",
    }
