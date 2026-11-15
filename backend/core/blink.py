"""
Полный конвейер /api/blink без Django: поиск → эпохи → вырезки → длина волны → стек → PNG + JSON по COMMON §6.
Вьюха (backend/viewer) только валидирует параметры, вызывает build_blink в фоне и отдаёт результат.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import logging
import threading
from typing import Callable, Iterable

import numpy as np

from . import config, epochs, grid as gridmod, imaging, motion as motionmod, spherex
from .targets import ProperMotion, mjd_to_year, propagate

log = logging.getLogger(__name__)

Progress = Callable[[str, float], None]


class BlinkError(Exception):
    """code — машинный код ошибки из COMMON §6 (no_data, few_epochs, fov_too_large, …)."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def _fid(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:20]


def save_frames(frames: dict[str, bytes]) -> None:
    d = config.CACHE_DIR / "frames"
    d.mkdir(parents=True, exist_ok=True)
    for fid, png in frames.items():
        (d / f"{fid}.png").write_bytes(png)


def frame_path(fid: str):
    """Путь к PNG по непрозрачному id (только [0-9a-f], только внутри CACHE_DIR/frames)."""
    if not fid or any(c not in "0123456789abcdef" for c in fid):
        raise BlinkError("not_found")
    p = config.CACHE_DIR / "frames" / f"{fid}.png"
    if not p.exists():
        raise BlinkError("not_found")
    return p


def _one_detector(det: int, metas, ra, dec, ra_cat, dec_cat, pm, fov, mode, max_per_epoch,
                  wl_auto, wl_tol, loader, wl_func, progress, p0, p1):
    sel = [m for m in metas if m.detector == det]
    eps = [epochs.limit_per_epoch(e, max_per_epoch) for e in epochs.group_epochs(sel)]
    if len(eps) < 2:
        return None, [{"code": "few_epochs", "severity": "warning", "detector": det}], 0.0

    flat = [m for e in eps for m in e]
    progress(f"download:{len(flat)}", p0)
    done, done_lock = [0], threading.Lock()

    def load(m):
        # downloads are the slow part (minutes when IRSA is busy): report each one so the bar keeps moving
        try:
            return loader(m)
        finally:
            with done_lock:
                done[0] += 1
                progress(f"download:{len(flat)}", p0 + (p1 - p0) * 0.7 * done[0] / len(flat))

    with cf.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as ex:
        hd = dict(zip([id(m) for m in flat], ex.map(load, flat)))
    n_fail = sum(v is None for v in hd.values())
    progress("stack", p0 + (p1 - p0) * 0.7)

    wl = {id(m): wl_func(hd[id(m)]) for m in flat if hd[id(m)] is not None}
    warnings = []
    if n_fail:
        warnings.append({"code": "partial_download", "severity": "info", "detector": det, "failed": n_fail})
    window = None
    if wl_auto:
        per = [[wl[id(m)][0] for m in e if wl.get(id(m))] for e in eps]
        window = epochs.auto_wl_window(per, wl_auto)
        if window is None:
            warnings.append({"code": "wavelength_mismatch", "severity": "warning", "detector": det,
                             "detail": "no common wavelength window"})

    wcs, shape = gridmod.make_grid(ra, dec, fov)
    stacks, metas_out, bad_fracs = [], [], []
    for e in eps:
        pairs = [(hd[id(m)], wl.get(id(m))) for m in e if hd[id(m)] is not None]
        if window:
            pairs = [(h, w) for h, w in pairs if w and window[0] <= w[0] <= window[1]]
        if not pairs:
            continue
        hs = [h for h, _ in pairs]
        wls = [w[0] for _, w in pairs if w]
        bws = [w[1] for _, w in pairs if w]
        bad_fracs += [imaging.display_prepare(h)[2] for h in hs[:1]]
        stacks.append(imaging.stack(hs, wcs, shape))
        mjd0 = e[0].date_mjd
        tx = ty = None
        if pm:
            tra, tdec = propagate(ra_cat, dec_cat, pm, mjd_to_year(float(np.mean([m.date_mjd for m in e]))))
            tx, ty = gridmod.sky_to_pix(wcs, tra, tdec)
        metas_out.append({
            "date_iso": e[0].date_iso, "date_end_iso": e[-1].date_iso, "date_mjd": round(mjd0, 4),
            "n_images": len(hs), "detector": det,
            "wavelength_range_um": list(config.DETECTOR_UM[det]),
            "target_wavelength_um": round(float(np.median(wls)), 4) if wls else None,
            "target_wavelength_span_um": [round(min(wls), 4), round(max(wls), 4)] if wls else None,
            "target_bandwidth_um": round(float(np.median(bws)), 4) if bws else None,
            "target_xy": [round(tx, 2), round(ty, 2)] if pm else None,  # где цель должна быть (кольцо в UI)
        })
    if len(stacks) < 2:
        warnings.append({"code": "few_epochs", "severity": "warning", "detector": det})
        return None, warnings, 0.0

    meds = [f["target_wavelength_um"] for f in metas_out if f["target_wavelength_um"]]
    if len(meds) < len(metas_out):
        warnings.append({"code": "wavelength_unknown", "severity": "info", "detector": det})
    elif max(meds) - min(meds) > wl_tol:
        warnings.append({"code": "wavelength_mismatch", "severity": "warning", "detector": det,
                         "spread_um": round(max(meds) - min(meds), 4)})

    # measured shift of the target between the earliest and latest full epochs (only when a motion is expected)
    i0, i1 = epochs.choose_diff_pair([f["n_images"] for f in metas_out])
    measured = None
    # Only for targets expected to move at least MIN_MOTION_ARCSEC: for stationary variable stars a centroid
    # "shift" is pure systematics (RW Aur, 15 Nov: 3.3 ± 0.8″ measured for a star that does not move).
    expected = 0.0
    if pm and metas_out[i0]["target_xy"] and metas_out[i1]["target_xy"]:
        (x0, y0), (x1, y1) = metas_out[i0]["target_xy"], metas_out[i1]["target_xy"]
        expected = float(np.hypot(x1 - x0, y1 - y0)) * config.PIXSCALE_ARCSEC
    if expected >= config.MIN_MOTION_ARCSEC:
        years = (metas_out[i1]["date_mjd"] - metas_out[i0]["date_mjd"]) / 365.25
        measured = motionmod.measure_shift(stacks[i0], stacks[i1], metas_out[i0]["target_xy"],
                                           metas_out[i1]["target_xy"], config.PIXSCALE_ARCSEC, years)
        if measured:
            measured["pair"] = [metas_out[i0]["date_iso"], metas_out[i1]["date_iso"]]

    key = (round(ra, 5), round(dec, 5), fov, det, mode, max_per_epoch, wl_auto)
    frames: dict[str, bytes] = {}
    out: list[dict] = []
    if mode == "frames":
        for fm, png in zip(metas_out, imaging.render_png(stacks)):
            fid = _fid(*key, fm["date_mjd"])
            frames[fid] = png
            out.append({**fm, "id": fid, "kind": "epoch"})
        if measured:
            out[i1]["motion"] = measured
    elif mode == "diff":
        # кадр минус медиана всех эпох (COMMON) + отдельный кадр «поздняя − ранняя» по полным эпохам
        med = np.nanmedian(np.stack(stacks), axis=0)
        diffs = [s - med for s in stacks]
        diffs.append(stacks[i1] - stacks[i0])
        pngs = imaging.render_png(diffs, symmetric=True)
        for fm, png in zip(metas_out, pngs[:-1]):
            fid = _fid(*key, fm["date_mjd"])
            frames[fid] = png
            out.append({**fm, "id": fid, "kind": "diff_vs_median"})
        fid = _fid(*key, "pair", i0, i1)
        frames[fid] = pngs[-1]
        out.append({**metas_out[i1], "id": fid, "kind": "diff_pair",
                    "pair": [metas_out[i0]["date_iso"], metas_out[i1]["date_iso"]],
                    "target_xy_from": metas_out[i0]["target_xy"],
                    **({"motion": measured} if measured else {})})
    elif mode == "sum":
        total = np.nanmean(np.stack(stacks), axis=0)
        fid = _fid(*key, "sum")
        frames[fid] = imaging.render_png([total])[0]
        out.append({**metas_out[-1], "id": fid, "kind": "sum",
                    "date_iso": metas_out[0]["date_iso"], "date_end_iso": metas_out[-1]["date_end_iso"],
                    "n_images": sum(f["n_images"] for f in metas_out)})
    return (out, frames, (wcs, shape)), warnings, float(np.mean(bad_fracs)) if bad_fracs else 0.0


def build_blink(ra: float, dec: float, fov: float = 300, detector: int | str = 6, mode: str = "frames",
                name: str | None = None, pm: ProperMotion | None = None,
                max_per_epoch: int = config.MAX_PER_EPOCH, wl_auto: float | None = None,
                wl_tol: float = config.DEFAULT_WL_TOL_UM, progress: Progress | None = None,
                metas: list | None = None, loader=None, wl_func=None) -> tuple[dict, dict[str, bytes]]:
    """
    Возвращает (ответ /api/blink по COMMON §6, {frame_id: png_bytes}).
    detector=all — независимые последовательности по детекторам (никогда не смешиваются).
    Для движущейся цели (pm) центр сетки — положение на SPHEREX_MID_EPOCH, а в кадрах — target_xy по эпохам.
    """
    progress = progress or (lambda s, p: None)
    if mode not in ("frames", "diff", "sum"):
        raise BlinkError("invalid_parameters", "mode")
    if not (0 <= ra < 360 and -90 <= dec <= 90) or not (np.isfinite(ra) and np.isfinite(dec)):
        raise BlinkError("invalid_coordinates")
    if not (0 < fov <= config.FOV_MAX_ARCSEC):
        raise BlinkError("fov_too_large")
    dets: Iterable[int] = range(1, 7) if detector == "all" else [int(detector)]

    ra_cat, dec_cat = ra, dec
    if pm:
        ra, dec = propagate(ra, dec, pm, config.SPHEREX_MID_EPOCH)

    progress("search", 0.02)
    if metas is None:
        try:
            metas = spherex.find_images(ra, dec)
        except Exception as e:  # noqa: BLE001
            raise BlinkError("irsa_timeout", str(e)) from e
    if not metas:
        raise BlinkError("no_data")

    size = fov * config.CUTOUT_MARGIN
    loader = loader or (lambda m: spherex.fetch_cutout(m, ra, dec, size))
    wl_func = wl_func or (lambda h: imaging.target_wavelength(h, ra, dec))

    frames_all, out_all, warnings, bads, grid_info = {}, [], [], [], None
    dets = list(dets)
    for k, det in enumerate(dets):
        p0, p1 = 0.05 + 0.9 * k / len(dets), 0.05 + 0.9 * (k + 1) / len(dets)
        res, w, bad = _one_detector(det, metas, ra, dec, ra_cat, dec_cat, pm, fov, mode, max_per_epoch,
                                    wl_auto, wl_tol, loader, wl_func, progress, p0, p1)
        warnings += w
        if res:
            out, frames, grid_info = res
            out_all += out
            frames_all.update(frames)
            bads.append(bad)
    if not out_all:
        codes = {w["code"] for w in warnings}
        raise BlinkError("few_epochs" if "few_epochs" in codes else "no_data")

    wcs, shape = grid_info
    for f in out_all:
        f["url"] = f"/api/frame/{f['id']}.png"
    response = {
        "target": {"ra": round(ra, 6), "dec": round(dec, 6), "name": name,
                   "coordinate_epoch": config.SPHEREX_MID_EPOCH if pm else None,
                   "catalog_ra": ra_cat if pm else None, "catalog_dec": dec_cat if pm else None,
                   "pm_mas_yr": [pm.pmra_mas_yr, pm.pmdec_mas_yr] if pm else None},
        "fov_arcsec": fov,
        "mode": mode,
        "grid": gridmod.grid_payload(wcs, shape),
        "frames": sorted(out_all, key=lambda f: (f["detector"], f["date_mjd"], f["kind"])),
        "warnings": warnings,
        "flags_summary": {"bad_pixel_fraction": round(float(np.mean(bads)), 4) if bads else None,
                          "policy": config.DISPLAY_FLAG_POLICY["name"]},
    }
    progress("done", 1.0)
    return response, frames_all


def to_json(response: dict) -> str:
    return json.dumps(response, ensure_ascii=False, indent=2)
