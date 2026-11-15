"""
Поиск снимков SPHEREx (SIA2) и загрузка вырезок (cutout) с файловым кэшем.
Факты: docs/DATA_NOTES.md §0–§2. Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import csv
import hashlib
import http.client
import io
import json
import logging
import time
import urllib.error
import urllib.parse
from dataclasses import asdict, dataclass, field

from astropy.time import Time

from . import config, net

log = logging.getLogger(__name__)


@dataclass
class ImageMeta:
    obs_id: str
    date_mjd: float
    date_iso: str
    detector: int                  # 1..6
    release: str                   # dr1 | qr3
    collection: str                # фактическая SIA2 collection
    access_url: str                # из SIA2, не собираем вручную
    wl_min_um: float               # диапазон ДЕТЕКТОРА; длина волны в точке цели — imaging.pixel_wavelength
    wl_max_um: float
    raw_metadata: dict = field(default_factory=dict)


def _sia2(collection: str, ra: float, dec: float, radius_deg: float) -> list[dict]:
    q = urllib.parse.urlencode({"COLLECTION": collection, "POS": f"circle {ra} {dec} {radius_deg}",
                                "RESPONSEFORMAT": "CSV"})
    # IRSA answers 502/503 under load (15.11: "502 Proxy Error" on SIA2): retry with a growing pause
    for attempt in range(4):
        try:
            with net.urlopen(f"{config.SIA2_URL}?{q}") as r:
                body = r.read().decode()
            return list(csv.DictReader(io.StringIO(body)))  # csv, не astropy: в cloud_access JSON в кавычках
        except (TimeoutError, urllib.error.URLError, http.client.IncompleteRead,
                http.client.RemoteDisconnected) as e:
            if attempt == 3:
                raise
            log.warning("SIA2 %s failed (%s), retrying", collection, e)
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError("unreachable")


def find_images(ra: float, dec: float, radius_arcsec: float = 3.6,
                releases: tuple[str, ...] = ("dr1", "qr3"), include_deep: bool = False,
                use_cache: bool = True) -> list[ImageMeta]:
    """Все снимки, покрывающие точку. SIA2 ~9 с на коллекцию (WISE 0855: DR1 258, QR3 0) → кэшируем."""
    cols = [(r, config.RELEASE_COLLECTIONS[r]) for r in releases]
    if include_deep:
        cols += [(r, config.DEEP_COLLECTIONS[r]) for r in releases]
    key = hashlib.sha1(f"{ra:.4f}|{dec:.4f}|{radius_arcsec}|{cols}".encode()).hexdigest()[:16]
    path = config.CACHE_DIR / "sia" / f"{key}.json"
    if use_cache and path.exists():
        return [ImageMeta(**d) for d in json.loads(path.read_text())]

    metas, seen = [], set()
    for rel, col in cols:
        t0 = time.time()
        rows = _sia2(col, ra, dec, radius_arcsec / 3600)
        log.info("SIA2 %s: %d rows in %.1fs", col, len(rows), time.time() - t0)
        for row in rows:
            det = int(str(row["energy_bandpassname"])[-1])
            k = (row["obs_id"], det)
            if k in seen:
                continue
            seen.add(k)
            mjd = float(row["t_min"])
            metas.append(ImageMeta(
                obs_id=row["obs_id"], date_mjd=mjd, date_iso=Time(mjd, format="mjd").iso[:10],
                detector=det, release=rel, collection=col, access_url=row["access_url"],
                wl_min_um=float(row["em_min"]) * 1e6, wl_max_um=float(row["em_max"]) * 1e6,
                raw_metadata={k2: row.get(k2) for k2 in ("obs_publisher_did", "obs_release_date",
                                                          "s_pixel_scale", "t_exptime")},
            ))
    metas.sort(key=lambda m: m.date_mjd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(m) for m in metas]))
    return metas


KEEP_HDUS = ("IMAGE", "FLAGS", "VARIANCE", "ZODI", "WCS-WAVE")  # EPSF (~4 МБ) в кэш не кладём


def cutout_url(meta: ImageMeta, ra: float, dec: float, size_arcsec: float) -> str:
    if not meta.access_url.startswith(config.IRSA):
        raise ValueError("untrusted_url")
    return f"{meta.access_url}?center={ra},{dec}d&size={size_arcsec / 3600:.6f}"  # size — в ГРАДУСАХ


def fetch_cutout(meta: ImageMeta, ra: float, dec: float, size_arcsec: float,
                 retries: int = config.RETRIES):
    """
    HDUList или None. Ловушки IRSA: «Server busy» с кодом 200 (тело не FITS) и 503 → повтор с паузой 5→30 с.
    """
    from astropy.io import fits

    url = cutout_url(meta, ra, dec, size_arcsec)
    path = config.CACHE_DIR / "cutouts" / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".fits")
    if path.exists():
        return fits.open(path)
    for attempt in range(retries + 1):
        try:
            with net.urlopen(url) as r:
                body = r.read()
            if not body.startswith(b"SIMPLE"):
                raise OSError(f"IRSA busy/not FITS: {body[:40]!r}")
            with fits.open(io.BytesIO(body)) as hdul:
                keep = [fits.PrimaryHDU(header=hdul[0].header)] + \
                       [hdul[n].copy() for n in KEEP_HDUS if n in hdul]
            out = fits.HDUList(keep)
            path.parent.mkdir(parents=True, exist_ok=True)
            out.writeto(path, overwrite=True)
            return out
        except (TimeoutError, urllib.error.URLError, http.client.IncompleteRead,
                http.client.RemoteDisconnected, OSError) as e:
            if attempt == retries:
                log.warning("cutout failed %s D%d: %s", meta.obs_id, meta.detector, e)
                return None
            time.sleep(min(5 * 2 ** attempt, 30))
