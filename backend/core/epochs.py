"""
Группировка снимков по эпохам и подбор общей длины волны (LVF).
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

from typing import Sequence, TypeVar

import numpy as np

from . import config

T = TypeVar("T")  # любой объект с .date_mjd


def group_epochs(metas: Sequence[T], gap_days: float = config.EPOCH_GAP_DAYS,
                 fallback_bin_days: float = config.FALLBACK_BIN_DAYS) -> list[list[T]]:
    """
    Эпоха = кластер снимков с разрывом > gap_days (один ~6-месячный проход SPHEREx).
    < 2 эпох (цель у полюса эклиптики, напр. R Dra, снимается непрерывно) → бины по fallback_bin_days.
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
    bins: dict[int, list[T]] = {}
    for m in ms:
        bins.setdefault(int((m.date_mjd - t0) // fallback_bin_days), []).append(m)
    return [bins[k] for k in sorted(bins)]


def limit_per_epoch(epoch: Sequence[T], max_n: int = config.MAX_PER_EPOCH) -> list[T]:
    """Не больше max_n снимков, равномерно по времени (у R Dra их сотни)."""
    if len(epoch) <= max_n:
        return list(epoch)
    idx = np.linspace(0, len(epoch) - 1, max_n).round().astype(int)
    return [epoch[i] for i in sorted(set(idx))]


def auto_wl_window(per_epoch_wls: Sequence[Sequence[float]], width: float) -> tuple[float, float] | None:
    """
    Окно [a, a+width] мкм, в которое попадает ≥1 снимок КАЖДОЙ эпохи; максимизирует минимум снимков на эпоху.
    None — общего окна нет (сравнение яркости между эпохами нечестно; движение при этом видно).
    """
    allw = sorted(w for ws in per_epoch_wls for w in ws)
    best, best_min, best_sum = None, 0, 0
    for a in allw:
        counts = [sum(a <= w <= a + width for w in ws) for ws in per_epoch_wls]
        mn, sm = min(counts) if counts else 0, sum(counts)
        if mn > best_min or (mn == best_min and mn > 0 and sm > best_sum):
            best, best_min, best_sum = (a, a + width), mn, sm
    return best if best_min >= 1 else None


def choose_diff_pair(n_images: Sequence[int]) -> tuple[int, int]:
    """
    Пара эпох для diff: самая ранняя и самая поздняя среди «полных» (n ≥ max(3, 0.5·max)).
    У WISE 0855 первая эпоха D6 — 3 снимка; diff с ней тонет в шуме.
    """
    if len(n_images) < 2:
        raise ValueError("few_epochs")
    good = [i for i, n in enumerate(n_images) if n >= max(3, 0.5 * max(n_images))]
    return (good[0], good[-1]) if len(good) >= 2 else (0, len(n_images) - 1)
