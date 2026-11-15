"""
Собственное движение и перенос координат на эпоху наблюдения.

Почему это обязательно (проверено 14.11 на реальных кадрах): SIMBAD отдаёт координаты на J2000.
Barnard за ~26 лет ушёл на 268″ к северу и без поправки оказывается ВНЕ кадра 300″.
С поправкой пары «белое+чёрное» у Barnard и ε Ind B точно попали в предсказанные места.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProperMotion:
    pmra_mas_yr: float      # μα·cosδ, мас/год (как в Gaia/SIMBAD)
    pmdec_mas_yr: float
    ref_epoch: float        # год, на который даны координаты


# Пресеты. Значения из литературы (не перепроверены командой отдельно; сверять перед питчем):
# Barnard: Gaia DR3 (-801.6, +10362.4 mas/yr, ref 2000.0)
# WISE 0855: Luhman & Esplin 2016 (-8118, +680 mas/yr); coordinates from the AllWISE name, epoch ≈ 2010.5
# ε Ind B: common proper motion with the host star ε Ind A (+3961, -2539 mas/yr, ref 2000.0)
# RW Aur & R Dra: стационарные объекты в масштабе SPHEREx (PM < 25 mas/yr, смещение < 0.03″ за миссию)
PRESET_PM = {
    "wise-0855": ProperMotion(-8118.0, 680.0, 2010.5),
    "barnards-star": ProperMotion(-801.6, 10362.4, 2000.0),
    "epsilon-indi-b": ProperMotion(3961.0, -2539.0, 2000.0),
    "rw-aurigae": ProperMotion(1.2, -22.3, 2016.0),
    "r-draconis": ProperMotion(-11.9, -11.6, 2016.0),
}


def mjd_to_year(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


def propagate(ra: float, dec: float, pm: ProperMotion, to_year: float) -> tuple[float, float]:
    """Линейный перенос (для десятилетий достаточно). pmra уже умножен на cosδ."""
    dt = to_year - pm.ref_epoch
    dec2 = dec + pm.pmdec_mas_yr / 3.6e6 * dt
    ra2 = ra + pm.pmra_mas_yr / 3.6e6 * dt / np.cos(np.deg2rad((dec + dec2) / 2))
    return float(ra2 % 360.0), float(dec2)
