"""
Обработка вырезок: маска FLAGS, длина волны в точке (LVF), репроекция, стек, рендер PNG.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import io
import logging

import numpy as np
from astropy.wcs import WCS

from . import config

log = logging.getLogger(__name__)


def _mask_from_policy(fl: np.ndarray, policy: dict) -> np.ndarray:
    m = sum(1 << b for b in policy["bits"])
    return (fl.astype(np.int64) & m) != 0


def flag_stats(fl: np.ndarray) -> dict[str, float]:
    """Доля пикселей с каждым установленным битом (диагностика, DATA_NOTES)."""
    fl = fl.astype(np.int64)
    return {config.FLAG_BITS.get(b, f"bit{b}"): round(float(np.mean((fl >> b) & 1)), 4)
            for b in range(32) if np.any((fl >> b) & 1)}


def masked_image(hdul, flag_policy: dict = config.DISPLAY_FLAG_POLICY) -> np.ma.MaskedArray:
    """IMAGE (MJy/sr) с маской по выбранной политике FLAGS и нечисловым пикселям. Единицы не меняются."""
    img = hdul["IMAGE"].data.astype("float64")
    bad = ~np.isfinite(img)
    if "FLAGS" in hdul:
        bad |= _mask_from_policy(hdul["FLAGS"].data, flag_policy)
    return np.ma.MaskedArray(img, mask=bad)


def display_prepare(hdul, flag_policy: dict = config.DISPLAY_FLAG_POLICY) -> tuple[np.ndarray, np.ndarray, float]:
    """
    ТОЛЬКО ДЛЯ КАРТИНКИ: IMAGE − ZODI (ZODI не вычтен в данных), маска, дисперсия.
    Защита: если маска съедает > 50% пикселей — не маскируем (значит, политику надо пересмотреть).
    Возвращает (img, var, доля замаскированных).
    """
    img = hdul["IMAGE"].data.astype("float64")
    if "ZODI" in hdul and hdul["ZODI"].data is not None:
        img = img - hdul["ZODI"].data
    var = hdul["VARIANCE"].data.astype("float64") if "VARIANCE" in hdul else np.ones_like(img)
    bad = ~np.isfinite(img) | ~np.isfinite(var) | (var <= 0)
    frac = 0.0
    if "FLAGS" in hdul:
        fm = _mask_from_policy(hdul["FLAGS"].data, flag_policy)
        frac = float(np.mean(fm))
        if frac < 0.5:
            bad |= fm
        else:
            log.warning("flag mask would remove %.0f%% — skipped; bits=%s", frac * 100,
                        flag_stats(hdul["FLAGS"].data))
    img[bad] = np.nan
    var[bad] = np.inf
    return img, var, frac


def pixel_wavelength(hdul, x: float, y: float) -> tuple[float, float] | None:
    """
    (λ, Δλ) мкм в пикселе (x, y; 0-based FITS) вырезки, по WCS-WAVE как в туториале IRSA.
    Только для визуализации; для науки — CWAVE/CBAND из Spectral WCS. None, если читатель не справился.
    """
    try:
        import astropy.units as u
        sw = WCS(hdul["IMAGE"].header, fobj=hdul, key="W")
        sw.sip = None
        wl, bw = sw.pixel_to_world(x, y)
        return float(wl.to(u.um).value), float(bw.to(u.um).value)
    except Exception:  # noqa: BLE001 — разные версии astropy падают по-разному
        return None


def target_wavelength(hdul, ra: float, dec: float) -> tuple[float, float] | None:
    """(λ, Δλ) мкм в точке цели на этой вырезке (LVF: у разных снимков разная)."""
    try:
        x, y = WCS(hdul["IMAGE"].header).world_to_pixel_values(ra, dec)
    except Exception:  # noqa: BLE001
        return None
    return pixel_wavelength(hdul, float(x), float(y))


def reproject_to(hdul, wcs: WCS, shape: tuple[int, int],
                 flag_policy: dict = config.DISPLAY_FLAG_POLICY) -> tuple[np.ndarray, np.ndarray]:
    """Вырезка → общая сетка. Возвращает (image, weight=1/variance) на сетке; где данных нет — weight=0."""
    from reproject import reproject_interp
    img, var, _ = display_prepare(hdul, flag_policy)
    w_in = WCS(hdul["IMAGE"].header)
    r_img, fp = reproject_interp((img, w_in), wcs, shape_out=shape)
    r_var, _ = reproject_interp((var, w_in), wcs, shape_out=shape)
    ok = np.isfinite(r_img) & np.isfinite(r_var) & (r_var > 0) & (fp > 0)
    weight = np.zeros(shape)
    weight[ok] = 1.0 / r_var[ok]
    r_img = np.where(ok, r_img, 0.0)
    return r_img, weight


def stack(hduls, wcs: WCS, shape: tuple[int, int]) -> np.ndarray:
    """Взвешенное (1/VARIANCE) среднее снимков ОДНОГО детектора на общей сетке, минус медиана кадра."""
    num, den = np.zeros(shape), np.zeros(shape)
    for h in hduls:
        im, w = reproject_to(h, wcs, shape)
        num += im * w
        den += w
    out = np.full(shape, np.nan)
    good = den > 0
    out[good] = num[good] / den[good]
    if np.any(good):
        out -= np.nanmedian(out)
    return out


def render_png(arrays: list[np.ndarray], stretch: str = "zscale_asinh", symmetric: bool = False) -> list[bytes]:
    """
    Одна общая шкала яркости по всем кадрам последовательности (иначе мерцает фон, а не объект).
    symmetric=True — для diff: серый = 0, чёрное = «было», белое = «стало».
    PNG без апсемплинга: размер = сетка; увеличивает фронтенд (imageSmoothingEnabled=false). y вниз.
    """
    from astropy.visualization import AsinhStretch, ImageNormalize, LinearStretch, ZScaleInterval
    from PIL import Image

    vals = [a[np.isfinite(a)].ravel() for a in arrays]
    allpix = np.concatenate(vals) if any(v.size for v in vals) else np.zeros(1)
    if symmetric:
        lim = float(np.nanpercentile(np.abs(allpix), 99.5)) or 1.0
        norm = ImageNormalize(vmin=-lim, vmax=lim, stretch=LinearStretch())
        empty = 0.5
    else:
        vmin, _ = ZScaleInterval().get_limits(allpix)
        vmax = float(np.nanpercentile(allpix, 99.9))
        if vmax <= vmin:
            vmax = vmin + 1.0
        norm = ImageNormalize(vmin=vmin, vmax=vmax,
                              stretch=AsinhStretch(0.05) if stretch == "zscale_asinh" else LinearStretch())
        empty = 0.0
    out = []
    for a in arrays:
        g = np.ma.filled(norm(a), np.nan).astype("float64")
        g = np.nan_to_num(np.clip(g, 0, 1), nan=empty)
        buf = io.BytesIO()
        Image.fromarray((np.flipud(g) * 255).astype(np.uint8)).save(buf, format="PNG", optimize=True)
        out.append(buf.getvalue())
    return out
