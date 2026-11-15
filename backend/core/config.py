"""
Константы SPHEREx и настройки core. Все числа проверены живыми запросами (docs/DATA_NOTES.md).
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import os
from pathlib import Path

# Кэш: вне OneDrive/Git. На Render/Railway задаётся переменной окружения.
CACHE_DIR = Path(os.environ.get("SKYBLINK_CACHE") or os.environ.get("CACHE_DIR")
                 or Path(__file__).resolve().parent.parent / "cache")   # same order as skyblink/settings.py

IRSA = "https://irsa.ipac.caltech.edu/"
SIA2_URL = "https://irsa.ipac.caltech.edu/SIA"
RELEASE_COLLECTIONS = {"dr1": "spherex_dr1", "qr3": "spherex_qr3"}
DEEP_COLLECTIONS = {"dr1": "spherex_dr1_deep", "qr3": "spherex_qr3_deep"}

PIXSCALE_ARCSEC = 6.15  # SIA2 s_pixel_scale + документация IRSA

# Диапазоны детекторов, мкм (SIA2 em_min/em_max). Пары D1+D4, D2+D5, D3+D6 снимаются одновременно.
DETECTOR_UM = {1: (0.746, 1.117), 2: (1.103, 1.650), 3: (1.630, 2.435),
               4: (2.403, 3.847), 5: (3.811, 4.430), 6: (4.412, 5.010)}

# Эпохи: реальный cadence 5 целей — 3–4 прохода за ~1.4 года; R Dra (у полюса эклиптики) — непрерывно.
EPOCH_GAP_DAYS = 60.0
FALLBACK_BIN_DAYS = 30.0
MAX_PER_EPOCH = 8

# Сеть: IRSA под нагрузкой хакатона отвечает 503 и «Server busy» (с кодом 200).
MAX_WORKERS = 4
RETRIES = 6
HTTP_TIMEOUT = 120

FOV_MAX_ARCSEC = 1800.0
CUTOUT_MARGIN = 1.15  # запас под поворот снимка при репроекции

# FLAGS — Table 16 SPHEREx Explanatory Supplement v1.6
FLAG_BITS = {0: "TRANSIENT", 1: "OVERFLOW", 2: "SUR_ERROR", 6: "NONFUNC", 7: "DICHROIC", 9: "MISSING_DATA",
             10: "HOT", 11: "COLD", 12: "FULLSAMPLE", 14: "PHANMISS", 15: "NONLINEAR", 17: "PERSIST",
             19: "OUTLIER", 20: "CROSSTALK", 21: "SOURCE", 22: "GHOST", 23: "GHOST_FPA", 24: "GHOST_EXT",
             25: "STREAK", 26: "BLOOM", 27: "SNOWBALL", 28: "HALO", 29: "SATELLITE_HALO"}
# Картинка: прячем только дефекты. SOURCE (бит 21) стоит почти на 100% пикселей у ярких звёзд — НЕ прятать.
DISPLAY_FLAG_POLICY = {"name": "display_v1", "bits": (0, 2, 6, 7, 9, 10, 11, 14, 25, 27, 28, 29)}
# Фотометрия (#2): строже — плюс OVERFLOW, NONLINEAR, PERSIST, OUTLIER, BLOOM.
PHOTOMETRY_FLAG_POLICY = {"name": "photometry_v1",
                          "bits": DISPLAY_FLAG_POLICY["bits"] + (1, 15, 17, 19, 26)}

# Отображение
DEFAULT_WL_TOL_UM = 0.05
SPHEREX_MID_EPOCH = 2025.9  # середина данных (май 2025 – окт 2026); сюда переносим координаты движущихся целей

# Measured motion (core/motion.py) only for targets expected to move at least this much over the baseline
MIN_MOTION_ARCSEC = 2.0
