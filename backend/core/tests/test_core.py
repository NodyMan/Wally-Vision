"""
Тесты core без сети:  cd backend && python -m pytest core/tests -q
"""
from __future__ import annotations

import io
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from core import blink, config, epochs, grid, imaging, spherex
from core.tests import synth


# ───────── grid: центр, углы, стороны света ─────────

def test_grid_center_and_corners():
    w, (h, wd) = grid.make_grid(10.0, -20.0, 300)
    assert h == wd and h % 2 == 1
    cx, cy = grid.sky_to_pix(w, 10.0, -20.0)
    assert cx == pytest.approx((wd - 1) / 2) and cy == pytest.approx((h - 1) / 2)
    for x, y in [(0, 0), (wd - 1, 0), (0, h - 1), (wd - 1, h - 1), (12.3, 7.8)]:
        ra, dec = grid.pix_to_sky(w, x, y)
        x2, y2 = grid.sky_to_pix(w, ra, dec)
        assert (x2, y2) == pytest.approx((x, y), abs=1e-6)


def test_grid_north_up_east_left():
    w, _ = grid.make_grid(10.0, 0.0, 300)
    cx, cy = grid.sky_to_pix(w, 10.0, 0.0)
    _, ny = grid.sky_to_pix(w, 10.0, 0.01)      # севернее → выше (y меньше)
    ex, _ = grid.sky_to_pix(w, 10.01, 0.0)      # восточнее → левее (x меньше)
    assert ny < cy and ex < cx


def test_grid_fov_limit_and_payload():
    with pytest.raises(ValueError):
        grid.make_grid(0, 0, config.FOV_MAX_ARCSEC + 1)
    w, shape = grid.make_grid(0, 0, 300)
    p = grid.grid_payload(w, shape)
    assert p["wcs_header"]["CTYPE1"].startswith("RA---TAN") and p["width"] == shape[1] and len(p["id"]) == 12


# ───────── эпохи ─────────

def _m(d):
    return SimpleNamespace(date_mjd=float(d))


def test_group_epochs_gap_and_fallback():
    ms = [_m(d) for d in (0, 5, 10, 200, 210, 400)]
    assert [len(e) for e in epochs.group_epochs(ms)] == [3, 2, 1]
    cont = [_m(d) for d in range(0, 120, 10)]           # непрерывно, как R Dra
    assert len(epochs.group_epochs(cont)) == 4           # бины по 30 дней


def test_limit_and_diff_pair():
    assert len(epochs.limit_per_epoch([_m(i) for i in range(20)], 8)) == 8
    assert epochs.choose_diff_pair([3, 20, 18]) == (1, 2)   # эпоха из 3 снимков пропущена
    assert epochs.choose_diff_pair([10, 12]) == (0, 1)


def test_auto_wl_window():
    assert epochs.auto_wl_window([[1.20, 1.30, 1.45], [1.31, 1.50], [1.29, 1.60]], 0.05) == pytest.approx((1.29, 1.34))
    assert epochs.auto_wl_window([[1.1], [1.6]], 0.05) is None


# ───────── маска FLAGS ─────────

def test_source_flag_is_not_masked():
    h = synth.make_loader()(synth.make_metas()[0])
    _, _, frac = imaging.display_prepare(h)
    assert frac < 0.01                                   # SOURCE на 100% пикселей не съедает картинку
    assert imaging.flag_stats(h["FLAGS"].data)["SOURCE"] == 1.0


# ───────── безопасность ─────────

def test_untrusted_urls_and_frame_ids():
    m = synth.make_metas()[0]
    m.access_url = "https://evil.example/x.fits"
    with pytest.raises(ValueError):
        spherex.cutout_url(m, 0, 0, 10)
    for bad in ("../etc/passwd", "ABC", ""):
        with pytest.raises(blink.BlinkError):
            blink.frame_path(bad)


# ───────── полный конвейер на синтетике ─────────

def _run(mode, detector=6, **kw):
    return blink.build_blink(synth.RA0, synth.DEC0, 300, detector, mode, name="syn", pm=synth.PM,
                             metas=synth.make_metas(), loader=synth.make_loader(), wl_func=synth.make_wl(), **kw)


def _png(b):
    return np.asarray(Image.open(io.BytesIO(b)))


def test_blink_frames():
    resp, frames = _run("frames")
    assert len(resp["frames"]) == 3 and len(frames) == 3
    f0 = resp["frames"][0]
    assert f0["url"] == f"/api/frame/{f0['id']}.png" and f0["detector"] == 6 and f0["kind"] == "epoch"
    assert _png(frames[f0["id"]]).shape == (resp["grid"]["height"], resp["grid"]["width"])
    ys = [f["target_xy"][1] for f in resp["frames"]]
    assert ys[0] > ys[1] > ys[2]                         # цель уходит на север = вверх по canvas
    assert resp["target"]["coordinate_epoch"] == config.SPHEREX_MID_EPOCH


def test_blink_diff_dipole_matches_motion():
    resp, frames = _run("diff")
    kinds = [f["kind"] for f in resp["frames"]]
    assert kinds.count("diff_vs_median") == 3 and kinds.count("diff_pair") == 1
    pair = next(f for f in resp["frames"] if f["kind"] == "diff_pair")
    img = _png(frames[pair["id"]]).astype(float)
    (wy, wx), (by, _bx) = np.unravel_index(img.argmax(), img.shape), np.unravel_index(img.argmin(), img.shape)
    assert wy < by                                       # белое («стало») севернее чёрного («было»)
    tx, ty = pair["target_xy"]
    assert abs(wx - tx) <= 2 and abs(wy - ty) <= 2       # белое пятно — в кольце предсказанного положения


def test_blink_sum_and_all_detectors():
    resp, frames = _run("sum")
    assert len(resp["frames"]) == 1 and resp["frames"][0]["kind"] == "sum"
    resp, _ = _run("frames", detector="all")             # данные есть только у D6
    assert {f["detector"] for f in resp["frames"]} == {6}
    assert sum(w["code"] == "few_epochs" for w in resp["warnings"]) == 5


def test_blink_wl_auto_and_errors():
    resp, _ = _run("frames", wl_auto=0.2)
    assert all(4.45 <= f["target_wavelength_um"] <= 4.95 for f in resp["frames"])
    with pytest.raises(blink.BlinkError) as e:
        blink.build_blink(400, 0, 300, metas=[])
    assert e.value.code == "invalid_coordinates"
    with pytest.raises(blink.BlinkError) as e:
        blink.build_blink(10, 0, 300, metas=[])
    assert e.value.code == "no_data"


# ───────── measured motion (centroids) ─────────

def test_measured_shift_matches_the_true_motion_within_its_error():
    for mode in ("diff", "frames"):
        r, _ = _run(mode)
        m = [f["motion"] for f in r["frames"] if "motion" in f]
        assert len(m) == 1, mode
        m = m[0]
        # the synthetic star moves 10.4"/yr due north; the measurement must agree within 3 sigma
        assert abs(m["shift_arcsec"] - m["expected_shift_arcsec"]) <= 3 * m["shift_err_arcsec"] + 0.2
        assert min(abs(m["pa_deg"]), abs(m["pa_deg"] - 360)) < 5
        assert m["reference_shift_arcsec"] is not None and m["reference_shift_arcsec"] < 1.0
        assert m["shift_err_arcsec"] >= m["stat_err_arcsec"]


def test_no_motion_is_reported_without_proper_motion():
    r, _ = blink.build_blink(synth.RA0, synth.DEC0, 300, 6, "diff", name="syn", metas=synth.make_metas(),
                             loader=synth.make_loader(), wl_func=synth.make_wl())
    assert not any("motion" in f for f in r["frames"])


def test_saturated_core_is_measured_by_its_masked_blob():
    from core import motion
    yy, xx = np.mgrid[0:49, 0:49]
    def frame(cx, cy):
        img = 50 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / 18.0) + np.random.default_rng(1).normal(0, 0.2, (49, 49))
        img[np.hypot(xx - cx, yy - cy) <= 3.2] = np.nan       # saturated core, masked like real SPHEREx data
        return img
    # canvas y is down; the arrays are FITS order (row = 48 - y). Star moves 1.6 px "north" (up on the canvas)
    early, late = frame(24.0, 48 - 24.4), frame(24.0, 48 - 22.8)
    m = motion.measure_shift(early, late, [24.0, 24.4], [24.0, 22.8], 6.15, 1.0)
    assert m["centroid_on"] == "masked_core" and m["core_masked"] and m["snr"] is None
    assert m["shift_arcsec"] == pytest.approx(1.6 * 6.15, abs=0.5) and min(m["pa_deg"], 360 - m["pa_deg"]) < 10
