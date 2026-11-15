"""
Общая сетка (TAN) и перевод координат небо ↔ пиксели PNG.

Соглашение (COMMON §6): пиксели PNG/canvas — 0-based, (0,0) в ЛЕВОМ ВЕРХНЕМ углу, y вниз.
FITS/WCS: y вверх, CRPIX 1-based. Здесь единственное место, где это переводится.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import hashlib

import numpy as np
from astropy.wcs import WCS

from . import config


def make_grid(ra: float, dec: float, fov_arcsec: float,
              pixscale_arcsec: float = config.PIXSCALE_ARCSEC) -> tuple[WCS, tuple[int, int]]:
    """Сетка с центром в цели. Север вверх, восток влево. Нечётный размер → цель в центре пикселя."""
    if not (0 < fov_arcsec <= config.FOV_MAX_ARCSEC):
        raise ValueError("fov_too_large")
    n = int(np.ceil(fov_arcsec / pixscale_arcsec)) | 1
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    w.wcs.cdelt = [-pixscale_arcsec / 3600, pixscale_arcsec / 3600]
    w.wcs.cunit = ["deg", "deg"]
    w.wcs.radesys = "ICRS"
    return w, (n, n)


def sky_to_pix(wcs: WCS, ra: float, dec: float) -> tuple[float, float]:
    """Небо → пиксель canvas (0-based, y вниз)."""
    x, y = wcs.world_to_pixel_values(ra, dec)  # 0-based, y вверх
    h = int(round(wcs.wcs.crpix[1] * 2 - 1))
    return float(x), float(h - 1 - y)


def pix_to_sky(wcs: WCS, x: float, y: float) -> tuple[float, float]:
    """Пиксель canvas (0-based, y вниз) → небо (ra, dec в градусах)."""
    h = int(round(wcs.wcs.crpix[1] * 2 - 1))
    ra, dec = wcs.pixel_to_world_values(x, h - 1 - y)
    return float(ra) % 360.0, float(dec)


def grid_payload(wcs: WCS, shape: tuple[int, int]) -> dict:
    """Объект `grid` для API: полный WCS-заголовок + id для сверки с /api/catalog."""
    hdr = {k: (v if isinstance(v, (int, float, str, bool)) else str(v))
           for k, v in wcs.to_header().items()}
    gid = hashlib.sha1(repr(sorted(hdr.items())).encode()).hexdigest()[:12]
    return {"id": gid, "width": shape[1], "height": shape[0],
            "pixel_scale_arcsec": round(abs(wcs.wcs.cdelt[1]) * 3600, 4),
            "pixel_origin": "top-left, 0-based (canvas); wcs_header is FITS (y up, CRPIX 1-based)",
            "wcs_header": hdr}
