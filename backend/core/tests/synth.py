"""
Синтетические «вырезки SPHEREx» для тестов без сети: звезда с собственным движением + неподвижный фон,
снимки слегка повёрнуты/сдвинуты, FLAGS как в реальности (SOURCE почти везде + один HOT).
"""
from __future__ import annotations

import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS

from core import config
from core.spherex import ImageMeta
from core.targets import ProperMotion, mjd_to_year, propagate

RA0, DEC0 = 269.452083, 4.693364
PM = ProperMotion(0.0, 10400.0, mjd_to_year(60900.0))  # 10.4″/год на север от эпохи MJD 60900


def make_metas(detector: int = 6) -> list[ImageMeta]:
    days = [60902 + d for d in range(0, 40, 4)] + [61110 + d for d in range(0, 40, 4)] + \
           [61270 + d for d in range(0, 36, 4)]
    return [ImageMeta(obs_id=f"syn{i}", date_mjd=float(t), date_iso=Time(t, format="mjd").iso[:10],
                      detector=detector, release="dr1", collection="spherex_dr1",
                      access_url=config.IRSA + f"syn{i}.fits",
                      wl_min_um=config.DETECTOR_UM[detector][0], wl_max_um=config.DETECTOR_UM[detector][1])
            for i, t in enumerate(days)]


def make_loader(seed: int = 42):
    rng = np.random.default_rng(seed)
    stars = [(RA0 + dx / 3600, DEC0 + dy / 3600, f) for dx, dy, f in
             [(60, 40, 300), (-80, -30, 500), (20, -90, 200), (-40, 70, 250), (100, -60, 400)]]

    def load(meta: ImageMeta):
        n = 60
        w = WCS(naxis=2)
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        w.wcs.crval = [RA0 + rng.normal(0, 2) / 3600, DEC0 + rng.normal(0, 2) / 3600]
        w.wcs.crpix = [n / 2, n / 2]
        th = np.deg2rad(rng.uniform(-30, 30))
        s = config.PIXSCALE_ARCSEC / 3600
        w.wcs.cd = [[-s * np.cos(th), s * np.sin(th)], [s * np.sin(th), s * np.cos(th)]]
        yy, xx = np.mgrid[0:n, 0:n]
        img = rng.normal(0, 1.0, (n, n))
        ra_t, dec_t = propagate(RA0, DEC0, PM, mjd_to_year(meta.date_mjd))
        for ra, dec, f in stars + [(ra_t, dec_t, 800)]:
            x, y = w.world_to_pixel_values(ra, dec)
            img += f / (2 * np.pi * 1.44) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.44))
        fl = np.full((n, n), 1 << 21, "int32")  # SOURCE почти везде, как у Barnard
        fl[5, 5] |= 1 << 10                      # один HOT
        hdr = w.to_header()
        return fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(img, hdr, name="IMAGE"),
                             fits.ImageHDU(fl, hdr, name="FLAGS"),
                             fits.ImageHDU(np.ones((n, n)), hdr, name="VARIANCE"),
                             fits.ImageHDU(np.zeros((n, n)), hdr, name="ZODI")])
    return load


def make_wl(seed: int = 7):
    rng = np.random.default_rng(seed)
    return lambda h: (float(rng.uniform(4.45, 4.95)), 0.04)
