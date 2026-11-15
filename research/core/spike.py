"""
SkyBlink spike: SPHEREx (SIA2 DR1+QR3) → эпохи → стек → общая сетка → blink-GIF + diff.

Это стартовый скрипт для участника #1 (Core Viewer). Логику отсюда потом переносим
в backend/core (spherex.py, epochs.py, grid.py, imaging.py) почти один в один.
Все факты о данных — в docs/DATA_NOTES.md (проверено живыми запросами к IRSA 2026-11-14).

Запуск:
    pip install astropy astroquery reproject numpy pillow truststore certifi
    python research/core/spike.py --target wise0855 --detector 6
    python research/core/spike.py --target barnard --detector 2 --fov 240
    python research/core/spike.py --ra 133.79513 --dec -7.24515 --detector 6
    python research/core/spike.py --target wise0855 --detector 6 --wl-min 4.6 --wl-max 4.8   # одна длина волны
    python research/core/spike.py --target rdra --detector 2 --wl-auto 0.05 --max-per-epoch 20  # переменные звёзды
    python research/core/spike.py --selftest          # офлайн, на синтетике (без интернета)

Результат в research/core/out/:
    <name>_d<N>.gif            blink-анимация по эпохам
    <name>_d<N>_diff.png       последняя эпоха минус первая (чёрное+белое = движение)
    <name>_d<N>_frames/*.png   отдельные кадры (крупные, nearest)
    <name>_d<N>.json           сводка в формате, близком к /api/blink

Астрономия коротко (для не-астрономов):
- SPHEREx снимает всё небо примерно раз в 6 месяцев. Одна «эпоха» = один такой проход.
  Внутри прохода точку снимают много раз за несколько недель, каждый раз на ДРУГОЙ длине
  волны (фильтр LVF: длина волны меняется вдоль детектора). Поэтому эпоху определяем по
  большому разрыву во времени (> 60 дней), а не по суткам.
- 6 детекторов = 6 диапазонов длин волн. Сравнивать эпохи можно только внутри ОДНОГО детектора,
  иначе яркость «меняется» из-за разных длин волн, а не из-за движения.
- Пиксель 6.15″. Ближайшие быстрые объекты сдвигаются на ~8–11″ в год → всего 1–2 пикселя
  за всю базу. Поэтому: общая сетка, общая шкала яркости, крупный зум, diff.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import http.client
import json
import logging
import os
import sys
import time
import urllib.error
from dataclasses import asdict, dataclass
from pathlib import Path

import astropy  # noqa: F401  — импортировать ДО getLogger, иначе логгер astropy ломается
import numpy as np

logging.getLogger("astropy").setLevel(logging.ERROR)  # глушим предупреждения про альтернативные WCS

# Windows: при выводе через `| findstr` или в файл консоль переходит на cp1251, и символы λ, ″, ✓, ▶
# роняют скрипт (UnicodeEncodeError). Принудительно пишем в UTF-8, непечатаемое заменяем на «?».
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "out"
CACHE_DIR = Path(os.environ.get("SKYBLINK_CACHE", HERE / "cache"))

def _ssl_context():
    """
    SSL с правильными корневыми сертификатами. Частая ошибка на Windows/macOS:
    CERTIFICATE_VERIFY_FAILED (Python не видит сертификаты системы, или антивирус вроде
    Kaspersky/ESET подменяет HTTPS своим сертификатом). Проверку НЕ отключаем, а берём:
      1) truststore — хранилище сертификатов самой ОС (видит и сертификат антивируса);
      2) certifi — актуальный набор Mozilla;
      3) стандартный контекст Python.
    pip install truststore certifi
    """
    import ssl
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _urlopen(url: str, timeout: float = 120):
    import urllib.request
    return urllib.request.urlopen(url, timeout=timeout, context=_ssl_context())


try:  # чтобы и astropy/astroquery (SIMBAD, Irsa) ходили через системные сертификаты
    import truststore as _ts
    _ts.inject_into_ssl()
except ImportError:
    pass

PIXSCALE_ARCSEC = 6.15  # проверено: spherex.plane.position_samplesize
IRSA = "https://irsa.ipac.caltech.edu/"

# Диапазоны детекторов, мкм (проверено: energy_bounds_lower/upper в spherex.plane)
DETECTOR_UM = {1: (0.746, 1.117), 2: (1.103, 1.650), 3: (1.630, 2.435),
               4: (2.403, 3.847), 5: (3.811, 4.430), 6: (4.412, 5.010)}

# Тестовые объекты челленджа. Имя для SIMBAD + запасные координаты (ICRS, градусы).
TARGETS = {
    "wise0855": ("WISE J085510.83-071442.5", 133.79513, -7.24515),   # из текста челленджа
    "barnard":  ("Barnard's Star", 269.452083, 4.693364),
    "epsindib": ("eps Ind B", 331.0461, -56.7836),                   # ⚠️ запасные примерные
    "rwaur":    ("RW Aur", 76.956311, 30.401178),
    "rdra":     ("R Dra", 248.16958, 66.75397),                      # ⚠️ запасные примерные
}

# Собственное движение (pmRA·cosδ, pmDec в мас/год) и эпоха, на которую даны координаты.
# ВАЖНО (проверено 14.11 на реальных кадрах): SIMBAD отдаёт координаты на J2000. Barnard за 26 лет ушёл
# на 268″ к северу — при FOV 300″ он ВНЕ кадра, если не пересчитать. У ε Ind B предсказанное по PM место
# совпало с парой «белое+чёрное» на diff с точностью ~1 px. Источники PM (приблизительно, уточнит #2 по Gaia/CatWISE):
# Barnard — Gaia DR3; ε Ind B — McCaughrean+2004 (~4.7″/год); WISE 0855 — Luhman & Esplin 2016,
# координаты из названия AllWISE (эпоха ≈ 2010.5, ⚠️ проверить).
TARGET_PM = {
    "wise0855": (-8118.0, 680.0, 2010.5),
    "barnard":  (-801.6, 10362.4, 2000.0),
    "epsindib": (3980.0, -2470.0, 2000.0),
}
SPHEREX_MID_EPOCH = 2025.9  # середина данных SPHEREx (май 2025 – окт 2026)


def propagate(ra: float, dec: float, pmra_mas: float, pmdec_mas: float, from_year: float, to_year: float):
    """Линейный перенос координат на другую эпоху (для лет-десятилетий хватает). pmra уже умножен на cosδ."""
    dt = to_year - from_year
    dec2 = dec + pmdec_mas / 3.6e6 * dt
    ra2 = ra + pmra_mas / 3.6e6 * dt / np.cos(np.deg2rad((dec + dec2) / 2))
    return ra2 % 360.0, dec2


def mjd_to_year(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


# ───────────────────────────── данные ─────────────────────────────

@dataclass
class ImageMeta:
    obs_id: str
    date_mjd: float
    detector: int          # 1..6
    access_url: str        # полный URL FITS из SIA2 (не собираем вручную)
    wl_min_um: float       # диапазон ДЕТЕКТОРА, а не длина волны в точке цели (её даёт WCS-WAVE)
    wl_max_um: float
    collection: str = ""   # spherex_dr1 | spherex_qr3


def resolve(name_or_key: str) -> tuple[float, float, str]:
    """Ключ из TARGETS или любое имя → (ra, dec, name) на эпоху каталога (обычно J2000). Сначала SIMBAD."""
    from astropy.coordinates import SkyCoord
    key = name_or_key.lower()
    simbad_name, ra0, dec0 = TARGETS.get(key, (name_or_key, None, None))
    try:
        c = SkyCoord.from_name(simbad_name)
        return float(c.ra.deg), float(c.dec.deg), simbad_name
    except Exception as e:  # нет сети к CDS или имя не найдено
        if ra0 is None:
            raise SystemExit(f"Не удалось найти '{name_or_key}': {e}")
        print(f"  ! SIMBAD недоступен ({e.__class__.__name__}), беру запасные координаты")
        return ra0, dec0, simbad_name


SIA2 = "https://irsa.ipac.caltech.edu/SIA"
COLLECTIONS = ("spherex_dr1", "spherex_qr3")  # DR1 + QR3 заменяют QR2 (QR2 через SIA2 не ищется)


def find_images(ra: float, dec: float, use_cache: bool = True,
                collections: tuple[str, ...] = COLLECTIONS) -> list[ImageMeta]:
    """
    Все снимки SPHEREx, покрывающие точку, через SIA2 (проверено 14.11.2026: WISE 0855 → DR1 258 снимков
    за ~9 с, QR3 0). TAP по spherex.plane даёт то же, но в 3–6 раз медленнее. Метаданные кэшируем.
    """
    import csv
    import io
    import urllib.parse

    path = CACHE_DIR / f"sia_{ra:.4f}_{dec:.4f}.json"
    if use_cache and path.exists():
        return [ImageMeta(**d) for d in json.loads(path.read_text())]

    metas, seen = [], set()
    for col in collections:
        q = urllib.parse.urlencode({"COLLECTION": col, "POS": f"circle {ra} {dec} 0.001",
                                    "RESPONSEFORMAT": "CSV"})
        t0 = time.time()
        with _urlopen(f"{SIA2}?{q}") as r:
            body = r.read().decode()
        tab = list(csv.DictReader(io.StringIO(body)))  # csv, а не astropy: в cloud_access лежит JSON в кавычках
        print(f"  SIA2 {col}: {len(tab)} снимков за {time.time() - t0:.1f} с")
        for row in tab:
            det = int(str(row["energy_bandpassname"])[-1])
            k = (str(row["obs_id"]), det)
            if k in seen:  # дедупликация на случай повторных публикаций
                continue
            seen.add(k)
            metas.append(ImageMeta(
                obs_id=str(row["obs_id"]), date_mjd=float(row["t_min"]), detector=det,
                access_url=str(row["access_url"]),
                wl_min_um=float(row["em_min"]) * 1e6, wl_max_um=float(row["em_max"]) * 1e6,
                collection=col,
            ))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(m) for m in metas]))
    return metas


def group_epochs(metas: list[ImageMeta], gap_days: float = 60.0,
                 fallback_bin_days: float = 30.0) -> list[list[ImageMeta]]:
    """
    Эпоха = кластер снимков с разрывом > gap_days (один 6-месячный проход SPHEREx).
    Если получилось < 2 эпох (объект у полюса эклиптики снимается непрерывно, напр. R Dra),
    режем на бины по fallback_bin_days.
    """
    ms = sorted(metas, key=lambda m: m.date_mjd)
    if not ms:
        return []
    epochs = [[ms[0]]]
    for m in ms[1:]:
        if m.date_mjd - epochs[-1][-1].date_mjd > gap_days:
            epochs.append([m])
        else:
            epochs[-1].append(m)
    if len(epochs) >= 2:
        return epochs
    t0 = ms[0].date_mjd
    bins: dict[int, list[ImageMeta]] = {}
    for m in ms:
        bins.setdefault(int((m.date_mjd - t0) // fallback_bin_days), []).append(m)
    return [bins[k] for k in sorted(bins)]


def limit_per_epoch(epoch: list[ImageMeta], max_n: int) -> list[ImageMeta]:
    """Не больше max_n снимков, равномерно по времени (у R Dra их сотни)."""
    if len(epoch) <= max_n:
        return epoch
    idx = np.linspace(0, len(epoch) - 1, max_n).round().astype(int)
    return [epoch[i] for i in sorted(set(idx))]


def cutout_url(meta: ImageMeta, ra: float, dec: float, size_arcsec: float) -> str:
    # size в ГРАДУСАХ (проверено живой загрузкой: 0.0958° → 56×56 px при 6.15″/px).
    # Берём только access_url из SIA2 и только с хоста IRSA — никаких URL от пользователя.
    if not meta.access_url.startswith(IRSA):
        raise ValueError(f"недоверенный access_url: {meta.access_url[:60]}")
    return f"{meta.access_url}?center={ra},{dec}d&size={size_arcsec / 3600:.6f}"


KEEP_HDUS = ("IMAGE", "FLAGS", "VARIANCE", "ZODI", "WCS-WAVE")  # EPSF (PSF-куб) весит ~4 МБ — в кэш не кладём


def fetch_cutout(meta: ImageMeta, ra: float, dec: float, size_arcsec: float, retries: int = 6):
    """
    Скачивает вырезку (с файловым кэшем). Возвращает HDUList или None.

    ⚠️ Проверено 2026-11-14: под нагрузкой IRSA отвечает HTTP 200 c Content-Type application/fits,
    но в теле текст "Server busy, retry later." (25 байт). Поэтому проверяем, что тело начинается
    с b"SIMPLE", и ретраим с паузой. Одна вырезка 345″ ≈ 4 МБ и ≈ 12 с (из них ~4 МБ — EPSF).
    """
    import io
    from astropy.io import fits

    url = cutout_url(meta, ra, dec, size_arcsec)
    path = CACHE_DIR / "cutouts" / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".fits")
    if path.exists():
        return fits.open(path)
    for attempt in range(retries + 1):
        try:
            with _urlopen(url) as r:
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
                print(f"  ! не скачалось {meta.obs_id} D{meta.detector}: {e}")
                return None
            # 5, 10, 20, 30, 30, 30 с. Проверено 14.11: в часы хакатона IRSA отдаёт и «Server busy» (200),
            # и HTTP 503 Service Unavailable — нужны длинные паузы, а не частые повторы.
            time.sleep(min(5 * 2 ** attempt, 30))


# ───────────────────────────── обработка ─────────────────────────────

def make_grid(ra: float, dec: float, fov_arcsec: float, pixscale: float = PIXSCALE_ARCSEC):
    """Общая TAN-сетка с центром в цели. Север вверх, восток влево (стандарт)."""
    from astropy.wcs import WCS
    n = int(np.ceil(fov_arcsec / pixscale)) | 1  # нечётное → цель ровно в центральном пикселе
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    w.wcs.cdelt = [-pixscale / 3600, pixscale / 3600]
    return w, (n, n)


def central_wavelength(hdul, ra: float, dec: float) -> tuple[float, float] | None:
    """
    (λ, Δλ) в мкм в точке цели из спектрального WCS (LVF), как в официальном туториале IRSA.
    Документация предупреждает, что не все FITS-читатели понимают WAVE-TAB → при ошибке None
    (фолбэк на будущее: билинейная интерполяция по 4 узлам таблицы WCS-WAVE, точность ~1 нм).
    Это значение для визуализации; для науки — CWAVE/CBAND из калибровочного продукта Spectral WCS.
    """
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astropy.wcs import WCS
        hdr = hdul["IMAGE"].header
        x, y = WCS(hdr).world_to_pixel(SkyCoord(ra * u.deg, dec * u.deg))
        sw = WCS(hdr, fobj=hdul, key="W")
        sw.sip = None
        wl, bw = sw.pixel_to_world(x, y)
        return float(wl.to(u.um).value), float(bw.to(u.um).value)
    except Exception:
        return None


# Биты FLAGS — официальная Table 16 SPHEREx Explanatory Supplement (v1.6, 2026-05-06).
FLAG_BITS = {0: "TRANSIENT", 1: "OVERFLOW", 2: "SUR_ERROR", 6: "NONFUNC", 7: "DICHROIC", 9: "MISSING_DATA",
             10: "HOT", 11: "COLD", 12: "FULLSAMPLE", 14: "PHANMISS", 15: "NONLINEAR", 17: "PERSIST",
             19: "OUTLIER", 20: "CROSSTALK", 21: "SOURCE", 22: "GHOST", 23: "GHOST_FPA", 24: "GHOST_EXT",
             25: "STREAK", 26: "BLOOM", 27: "SNOWBALL", 28: "HALO", 29: "SATELLITE_HALO"}
# Для КАРТИНКИ прячем только дефекты. НЕ прячем: SOURCE (просто «рядом звезда», стоит почти везде),
# OVERFLOW/NONLINEAR/BLOOM (центры ярких звёзд — иначе у Barnard будет дыра), FULLSAMPLE (информационный),
# PERSIST/GHOST/CROSSTALK/OUTLIER (решать после просмотра реальных кадров).
# Для ФОТОМЕТРИИ (#2) маску строже: добавить OVERFLOW, NONLINEAR, BLOOM, PERSIST, OUTLIER.
DISPLAY_BAD_BITS = (0, 2, 6, 7, 9, 10, 11, 14, 25, 27, 28, 29)
DISPLAY_BAD_MASK = sum(1 << b for b in DISPLAY_BAD_BITS)


def flag_stats(fl: np.ndarray) -> dict[str, float]:
    """Доля пикселей с каждым установленным битом — для диагностики и DATA_NOTES."""
    fl = fl.astype(np.int64)
    return {FLAG_BITS.get(b, f"bit{b}"): round(float(np.mean((fl >> b) & 1)), 3)
            for b in range(32) if np.any((fl >> b) & 1)}


def prepare(hdul, flag_mask: bool):
    """
    IMAGE − ZODI, маска по FLAGS, веса 1/VARIANCE. ТОЛЬКО ДЛЯ ОТОБРАЖЕНИЯ: по документации ZODI не вычтен
    из IMAGE, и для картинки мы его убираем (плюс медиану кадра в stack_epoch). Для фотометрии так не делать —
    там IMAGE в MJy/sr и локальный фон вокруг апертуры.
    Маска — только биты DISPLAY_BAD_BITS (дефекты), см. выше. Защита: если маска съедает > 50% пикселей,
    её отключаем и печатаем статистику битов — значит, политику надо пересмотреть.
    """
    img = hdul["IMAGE"].data.astype("float64")
    if "ZODI" in hdul and hdul["ZODI"].data is not None:
        img = img - hdul["ZODI"].data
    var = hdul["VARIANCE"].data.astype("float64") if "VARIANCE" in hdul else np.ones_like(img)
    bad = ~np.isfinite(img) | ~np.isfinite(var) | (var <= 0)
    if flag_mask and "FLAGS" in hdul:
        fl = hdul["FLAGS"].data.astype(np.int64)
        fmask = (fl & DISPLAY_BAD_MASK) != 0
        frac = float(np.mean(fmask))
        if frac < 0.5:
            bad |= fmask
        else:
            print(f"  ! маска FLAGS съела бы {frac:.0%} пикселей — пропускаю. Биты: {flag_stats(fl)}")
    img[bad] = np.nan
    var[bad] = np.inf
    return img, var


def stack_epoch(hduls, grid_wcs, shape, flag_mask: bool) -> np.ndarray:
    """Репроекция всех снимков эпохи на общую сетку + взвешенное среднее (веса 1/VARIANCE)."""
    from astropy.wcs import WCS
    from reproject import reproject_interp
    num = np.zeros(shape)
    den = np.zeros(shape)
    for h in hduls:
        img, var = prepare(h, flag_mask)
        w_in = WCS(h["IMAGE"].header)
        r_img, fp = reproject_interp((img, w_in), grid_wcs, shape_out=shape)
        r_var, _ = reproject_interp((var, w_in), grid_wcs, shape_out=shape)
        ok = np.isfinite(r_img) & np.isfinite(r_var) & (r_var > 0) & (fp > 0)
        w = np.zeros(shape)
        w[ok] = 1.0 / r_var[ok]
        num[ok] += r_img[ok] * w[ok]
        den += w
    out = np.full(shape, np.nan)
    good = den > 0
    out[good] = num[good] / den[good]
    # вычитаем фон кадра (медиана), чтобы эпохи были сравнимы
    return out - np.nanmedian(out)


def render(frames: list[np.ndarray], symmetric: bool = False) -> list[np.ndarray]:
    """Общая шкала яркости по ВСЕМ кадрам (иначе мерцает фон). Возвращает uint8."""
    from astropy.visualization import AsinhStretch, ImageNormalize, LinearStretch, ZScaleInterval
    allpix = np.concatenate([f[np.isfinite(f)].ravel() for f in frames])
    if symmetric:  # для diff: серый = 0, чёрное = было, белое = стало
        lim = np.nanpercentile(np.abs(allpix), 99.5) or 1.0
        norm = ImageNormalize(vmin=-lim, vmax=lim, stretch=LinearStretch())
    else:
        vmin, _ = ZScaleInterval().get_limits(allpix)      # низ — по фону (zscale)
        vmax = float(np.nanpercentile(allpix, 99.9))       # верх — по ярким звёздам, чтобы не пересвечивать
        norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch(0.05))
    out = []
    empty = 0.5 if symmetric else 0.0  # пиксели без данных: серый для diff, чёрный для кадров
    for f in frames:
        g = np.ma.filled(norm(f), np.nan).astype("float64")
        g = np.nan_to_num(np.clip(g, 0, 1), nan=empty)
        out.append((np.flipud(g) * 255).astype(np.uint8))  # flipud: в FITS y растёт вверх, в PNG — вниз
    return out


def to_rgb_with_overlay(gray: np.ndarray, label: str, zoom: int, marks=None):
    """Апсемплинг nearest (пиксель SPHEREx = чёткий квадрат) + перекрестие у цели + подпись даты.
    marks: [(x, y, k)] в пикселях сетки — k=0 первая эпоха (синее кольцо), k=1 последняя (жёлтое кольцо)."""
    from PIL import Image, ImageDraw
    im = Image.fromarray(gray).resize((gray.shape[1] * zoom, gray.shape[0] * zoom), Image.NEAREST).convert("RGB")
    d = ImageDraw.Draw(im)
    cx, cy = im.width // 2, im.height // 2
    gap, ln = zoom * 3, zoom * 3  # перекрестие с пустым центром, чтобы не закрывать объект
    for (x0, y0, x1, y1) in [(cx - gap - ln, cy, cx - gap, cy), (cx + gap, cy, cx + gap + ln, cy),
                             (cx, cy - gap - ln, cx, cy - gap), (cx, cy + gap, cx, cy + gap + ln)]:
        d.line([(x0, y0), (x1, y1)], fill=(255, 80, 80), width=2)
    for x, y, k in marks or []:
        px, py, r = (x + 0.5) * zoom, (y + 0.5) * zoom, zoom * 2.2
        d.ellipse([px - r, py - r, px + r, py + r], outline=(80, 160, 255) if k == 0 else (255, 210, 0), width=2)
    d.rectangle([0, 0, 8 * len(label) + 10, 18], fill=(0, 0, 0))
    d.text((5, 3), label, fill=(255, 255, 255))
    return im


def auto_wl_window(per_epoch_wls: list[list[float]], width: float) -> tuple[float, float] | None:
    """
    Подбирает окно длины волны [a, a+width], в которое попадает хотя бы по одному снимку из КАЖДОЙ эпохи,
    и максимизирует минимальное число снимков на эпоху. Так эпохи сравниваются на одной длине волны (LVF).
    None — если общего окна нет (тогда сравнение эпох по яркости нечестно; движение по-прежнему видно).
    """
    allw = sorted(w for ws in per_epoch_wls for w in ws)
    best, best_score = None, 0
    for a in allw:
        counts = [sum(a <= w <= a + width for w in ws) for ws in per_epoch_wls]
        score = min(counts)
        if score > best_score or (score == best_score and best and sum(counts) > best[1]):
            best, best_score = ((a, a + width), sum(counts)), score
    return best[0] if best and best_score >= 1 else None


# ───────────────────────────── конвейер ─────────────────────────────

def run(ra: float, dec: float, name: str, detector: int, fov: float, max_per_epoch: int,
        zoom: int, flag_mask: bool, metas: list[ImageMeta] | None = None,
        loader=None, wl_window: tuple[float, float] | None = None, wl_tol: float = 0.05,
        wl_func=None, wl_auto: float | None = None,
        pm: tuple[float, float, float] | None = None) -> dict:
    from astropy.time import Time

    slug = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")[:40]
    t_start = time.time()
    ra_cat, dec_cat = ra, dec
    if pm:  # центр кадра — где цель находится СЕЙЧАС, а не в 2000 году
        ra, dec = propagate(ra, dec, pm[0], pm[1], pm[2], SPHEREX_MID_EPOCH)
        print(f"  поправка за собственное движение: {pm[2]} → {SPHEREX_MID_EPOCH}, "
              f"сдвиг {(ra - ra_cat) * 3600 * np.cos(np.deg2rad(dec)):+.0f}″ по RA, {(dec - dec_cat) * 3600:+.0f}″ по Dec")
    print(f"\n▶ {name}  RA={ra:.5f} Dec={dec:.5f}  D{detector} {DETECTOR_UM[detector]} мкм  FOV={fov}″")

    if metas is None:
        metas = find_images(ra, dec)
    print(f"  всего снимков: {len(metas)}; по детекторам: "
          + ", ".join(f"D{d}={sum(m.detector == d for m in metas)}" for d in range(1, 7)))
    sel = [m for m in metas if m.detector == detector]
    epochs = [limit_per_epoch(e, max_per_epoch) for e in group_epochs(sel)]
    if len(epochs) < 2:
        raise SystemExit(f"  ✗ few_epochs: в D{detector} всего {len(epochs)} эпох(и)")
    for i, e in enumerate(epochs):
        print(f"  эпоха {i + 1}: {Time(e[0].date_mjd, format='mjd').iso[:10]} … "
              f"{Time(e[-1].date_mjd, format='mjd').iso[:10]}  ({len(e)} сн.)")

    # Скачиваем вырезки параллельно. В туториале 10 потоков, но IRSA под нагрузкой отвечает «Server busy»,
    # поэтому 6 потоков + ретраи с паузой надёжнее.
    load = loader or (lambda m: fetch_cutout(m, ra, dec, fov * 1.15))  # +15%: запас под поворот при репроекции
    flat = [m for e in epochs for m in e]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=4) as ex:  # 4, а не 6: IRSA под нагрузкой отвечает 503
        hd = dict(zip([id(m) for m in flat], ex.map(load, flat)))
    n_fail = sum(v is None for v in hd.values())
    print(f"  вырезки: {len(flat) - n_fail}/{len(flat)} за {time.time() - t0:.1f} с")
    first = next((h for h in hd.values() if h is not None and "FLAGS" in h), None)
    if first is not None:  # статистика битов по первой вырезке — записать в DATA_NOTES
        print(f"  FLAGS (доля пикселей по битам, 1-я вырезка): {flag_stats(first['FLAGS'].data)}")

    # LVF: внутри одного детектора длина волны в точке цели у разных снимков разная.
    # Считаем (λ, Δλ) для каждого снимка; если задано окно --wl-min/--wl-max — оставляем только попавшие в него.
    wlf = wl_func or (lambda h: central_wavelength(h, ra, dec))
    grid, shape = make_grid(ra, dec, fov)
    stacks, frames_meta, warnings = [], [], []
    wl_cache = {id(m): wlf(hd[id(m)]) for e in epochs for m in e if hd[id(m)] is not None}
    if wl_auto and not wl_window:
        per_epoch = [[wl_cache[id(m)][0] for m in e if wl_cache.get(id(m))] for e in epochs]
        wl_window = auto_wl_window(per_epoch, wl_auto)
        if wl_window:
            print(f"  авто-окно длины волны: {wl_window[0]:.3f}–{wl_window[1]:.3f} мкм "
                  f"(снимков по эпохам: {[sum(wl_window[0] <= w <= wl_window[1] for w in ws) for ws in per_epoch]})")
        else:
            print("  ! общего окна длины волны для всех эпох нет — сравнивать яркость между эпохами нельзя")
    for e in epochs:
        pairs = [(hd[id(m)], wl_cache[id(m)]) for m in e if hd[id(m)] is not None]
        if wl_window:
            pairs = [(h, w) for h, w in pairs if w and wl_window[0] <= w[0] <= wl_window[1]]
        if not pairs:
            continue
        hs = [h for h, _ in pairs]
        wls = [w[0] for _, w in pairs if w]
        bws = [w[1] for _, w in pairs if w]
        stacks.append(stack_epoch(hs, grid, shape, flag_mask))
        frames_meta.append({
            "date_iso": Time(e[0].date_mjd, format="mjd").iso[:10],
            "date_end_iso": Time(e[-1].date_mjd, format="mjd").iso[:10],
            "date_mjd": round(e[0].date_mjd, 4),
            "n_images": len(hs),
            "detector": detector,
            "target_wavelength_um": round(float(np.median(wls)), 4) if wls else None,
            "target_wavelength_range_um": [round(min(wls), 4), round(max(wls), 4)] if wls else None,
            "target_bandwidth_um": round(float(np.median(bws)), 4) if bws else None,
        })
    if len(stacks) < 2:
        raise SystemExit("  ✗ few_epochs: после фильтра по длине волны осталось < 2 эпох "
                         "(расширьте --wl-min/--wl-max или уберите их)")
    meds = [f["target_wavelength_um"] for f in frames_meta if f["target_wavelength_um"]]
    if len(meds) < len(frames_meta):
        warnings.append({"code": "wavelength_unknown", "severity": "warning"})
        print("  ! длину волны не удалось вычислить для части кадров (WCS-WAVE) — сравнение эпох не проверено")
    elif max(meds) - min(meds) > wl_tol:
        warnings.append({"code": "wavelength_mismatch", "severity": "warning",
                         "spread_um": round(max(meds) - min(meds), 4)})
        print(f"  ! эпохи сняты на разной длине волны: разброс медиан {max(meds) - min(meds):.3f} мкм > {wl_tol}. "
              "Изменение яркости может быть спектральным, а не временным. Попробуйте --wl-min/--wl-max.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fdir = OUT_DIR / f"{slug}_d{detector}_frames"
    fdir.mkdir(exist_ok=True)
    imgs = []
    for g, fm in zip(render(stacks), frames_meta):
        im = to_rgb_with_overlay(g, f"{fm['date_iso']}  D{detector}", zoom)
        im.save(fdir / f"{fm['date_iso']}.png")
        imgs.append(im)
    gif = OUT_DIR / f"{slug}_d{detector}.gif"
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=700, loop=0)

    # diff: самая поздняя минус самая ранняя эпоха (максимальная база → максимальный сдвиг), но только среди
    # «полных» эпох: у WISE 0855 первая эпоха D6 — всего 3 снимка, и diff с ней тонет в шуме.
    ns = [fm["n_images"] for fm in frames_meta]
    good = [i for i, n in enumerate(ns) if n >= max(3, 0.5 * max(ns))]
    i0, i1 = (good[0], good[-1]) if len(good) >= 2 else (0, len(stacks) - 1)
    if (i0, i1) != (0, len(stacks) - 1):
        print(f"  diff по эпохам {i0 + 1} и {i1 + 1} (в остальных мало снимков: {ns})")
    diff = stacks[i1] - stacks[i0]
    marks = []
    if pm:  # где цель должна быть в первой (кольцо) и последней (кружок) эпохе — проверка глазами
        for k, fm in ((0, frames_meta[i0]), (1, frames_meta[i1])):
            r2, d2 = propagate(ra_cat, dec_cat, pm[0], pm[1], pm[2], mjd_to_year(fm["date_mjd"]))
            x, y = grid.world_to_pixel_values(r2, d2)
            marks.append((float(x), float(shape[0] - 1 - y), k))  # flipud, как в render()
    dimg = to_rgb_with_overlay(render([diff], symmetric=True)[0],
                               f"{frames_meta[i1]['date_iso']} - {frames_meta[i0]['date_iso']}", zoom, marks)
    dpath = OUT_DIR / f"{slug}_d{detector}_diff.png"
    dimg.save(dpath)

    days = frames_meta[-1]["date_mjd"] - frames_meta[0]["date_mjd"]
    summary = {
        "target": {"ra": ra, "dec": dec, "name": name, "coordinate_epoch": SPHEREX_MID_EPOCH if pm else None,
                   "catalog_ra": ra_cat, "catalog_dec": dec_cat, "pm_mas_yr": list(pm[:2]) if pm else None},
        "fov_arcsec": fov, "pixel_scale_arcsec": PIXSCALE_ARCSEC, "size_px": list(shape),
        "grid": {"crval": [ra, dec], "crpix": [shape[0] // 2, shape[1] // 2], "cdelt_arcsec": PIXSCALE_ARCSEC},
        "detector": detector, "wavelength_range_um": list(DETECTOR_UM[detector]),
        "frames": frames_meta,
        "warnings": warnings,
        "baseline_days": round(days, 1),
        "failed_cutouts": n_fail,
        "elapsed_sec": round(time.time() - t_start, 1),
    }
    (OUT_DIR / f"{slug}_d{detector}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"  ✓ {gif.name}, {dpath.name}  (база {days:.0f} дн., {summary['elapsed_sec']} с)")
    return summary


# ───────────────────────────── офлайн-самотест ─────────────────────────────

def selftest(zoom: int):
    """
    Синтетика без интернета: звезда, которая движется на ~10″/год (как Barnard), + неподвижные звёзды.
    Проверяет весь конвейер: эпохи, стек, репроекцию (входные снимки слегка повёрнуты и сдвинуты),
    общую шкалу, GIF, diff. Если на *_diff.png видна пара «чёрное+белое» в центре — всё работает.
    """
    from astropy.io import fits
    from astropy.wcs import WCS

    ra0, dec0 = 269.452083, 4.693364
    rng = np.random.default_rng(42)
    pm_deg_per_day = (10.4 / 3600) / 365.25  # 10.4″/год на север
    stars = [(ra0 + dx / 3600, dec0 + dy / 3600, f) for dx, dy, f in
             [(60, 40, 300), (-80, -30, 500), (20, -90, 200), (-40, 70, 250), (100, -60, 400)]]

    def _fake_flags(n):  # как в реальности: SOURCE (бит 21) почти везде + один HOT-пиксель (бит 10)
        fl = np.full((n, n), 1 << 21, "int32")
        fl[5, 5] |= 1 << 10
        return fl

    def fake(meta: ImageMeta):
        n = 60
        w = WCS(naxis=2)
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        w.wcs.crval = [ra0 + rng.normal(0, 2) / 3600, dec0 + rng.normal(0, 2) / 3600]
        w.wcs.crpix = [n / 2, n / 2]
        th = np.deg2rad(rng.uniform(-30, 30))  # снимки SPHEREx повёрнуты по-разному
        s = PIXSCALE_ARCSEC / 3600
        w.wcs.cd = [[-s * np.cos(th), s * np.sin(th)], [s * np.sin(th), s * np.cos(th)]]
        yy, xx = np.mgrid[0:n, 0:n]
        img = rng.normal(0, 1.0, (n, n))
        sig = 1.2
        dt = meta.date_mjd - 60900
        for ra, dec, f in stars + [(ra0, dec0 + pm_deg_per_day * dt, 800)]:
            x, y = w.world_to_pixel_values(ra, dec)
            img += f / (2 * np.pi * sig**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sig**2))
        hdr = w.to_header()
        return fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(img, hdr, name="IMAGE"),
                             fits.ImageHDU(_fake_flags(n), hdr, name="FLAGS"),
                             fits.ImageHDU(np.ones((n, n)), hdr, name="VARIANCE"),
                             fits.ImageHDU(np.zeros((n, n)), hdr, name="ZODI")])

    # Расписание как у Barnard в реальных данных: 3 эпохи с разрывом ~6 мес.
    days = [60902 + d for d in range(0, 40, 4)] + [61110 + d for d in range(0, 40, 4)] + \
           [61270 + d for d in range(0, 36, 4)]
    metas = [ImageMeta(f"syn{i}", float(t), 6, IRSA + "syn.fits", *DETECTOR_UM[6]) for i, t in enumerate(days)]
    # у синтетики нет WCS-WAVE — даём длину волны, равномерно разбросанную по детектору D6, как у LVF
    wl_rng = np.random.default_rng(7)
    fake_wl = lambda h: (float(wl_rng.uniform(4.45, 4.95)), 0.04)  # noqa: E731
    return run(ra0, dec0, "selftest_barnard_like", 6, 300, 8, zoom, True, metas=metas, loader=fake,
               wl_func=fake_wl, wl_tol=0.15, wl_auto=0.2, pm=(0.0, 10400.0, mjd_to_year(60900)))


# ───────────────────────────── CLI ─────────────────────────────

def main():
    p = argparse.ArgumentParser(description="SkyBlink spike: SPHEREx blink GIF")
    p.add_argument("--target", help="ключ (" + ", ".join(TARGETS) + ") или любое имя для SIMBAD")
    p.add_argument("--ra", type=float)
    p.add_argument("--dec", type=float)
    p.add_argument("--detector", type=int, default=6, choices=range(1, 7),
                   help="1..6; для коричневых карликов 6, для обычных звёзд 1–2")
    p.add_argument("--fov", type=float, default=300, help="поле зрения, угловые секунды")
    p.add_argument("--max-per-epoch", type=int, default=8)
    p.add_argument("--zoom", type=int, default=8, help="апсемплинг кадров (nearest)")
    p.add_argument("--no-flag-mask", action="store_true")
    p.add_argument("--wl-min", type=float, help="брать только снимки, где λ в точке цели ≥ этого, мкм")
    p.add_argument("--wl-max", type=float, help="… и ≤ этого, мкм (сравнение эпох на одной длине волны)")
    p.add_argument("--wl-tol", type=float, default=0.05, help="допуск разброса λ между эпохами, мкм")
    p.add_argument("--wl-auto", type=float, metavar="WIDTH",
                   help="подобрать общее для всех эпох окно λ такой ширины, мкм (напр. 0.05). "
                        "Для переменных звёзд — обязательно; вместе с --max-per-epoch 20")
    p.add_argument("--pm", type=float, nargs=3, metavar=("PMRA", "PMDEC", "EPOCH"),
                   help="собственное движение цели (мас/год, pmRA·cosδ) и эпоха координат, напр. -801.6 10362.4 2000")
    p.add_argument("--no-pm", action="store_true", help="не поправлять координаты за собственное движение")
    p.add_argument("--selftest", action="store_true", help="офлайн-проверка на синтетике")
    a = p.parse_args()

    if a.selftest:
        selftest(a.zoom)
        return
    if a.ra is not None and a.dec is not None:
        ra, dec, name = a.ra, a.dec, f"ra{a.ra:.3f}_dec{a.dec:.3f}"
    elif a.target:
        ra, dec, name = resolve(a.target)
    else:
        p.error("нужен --target или --ra/--dec (или --selftest)")
    win = (a.wl_min, a.wl_max) if a.wl_min is not None and a.wl_max is not None else None
    pm = tuple(a.pm) if a.pm else (TARGET_PM.get((a.target or "").lower()) if not a.no_pm else None)
    if a.no_pm:
        pm = None
    run(ra, dec, name, a.detector, a.fov, a.max_per_epoch, a.zoom, not a.no_flag_mask,
        wl_window=win, wl_tol=a.wl_tol, wl_auto=a.wl_auto, pm=pm)


if __name__ == "__main__":
    sys.exit(main())
