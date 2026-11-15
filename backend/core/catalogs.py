"""
Gaia DR3 and CatWISE2020 sources around a position, from the IRSA TAP service (both catalogs are hosted
by IRSA, so the "download only from IRSA" rule holds). Verified live on 14.11.2026:
  gaia_dr3_source: ra, dec at epoch 2016.0; pmra, pmdec in mas/yr.
  catwise_2020:    ra, dec at the source's own mean epoch `meanobsmjd`; pmra, pmdec in ARCSEC/yr with
                   errors sigpmra, sigpmdec; w2mpro_pm.
A cone query takes 10–25 s, so results are cached on disk.

CatWISE quirk seen on Barnard's Star and WISE 0855: a fast mover is listed several times, once per stretch
of its track. Moving every entry from its own mean epoch brings them to the same place, where they are merged.

Astronomy note. Gaia sees visible light, CatWISE sees infrared. A cold brown dwarf can be bright in the
infrared and absent from Gaia. "No Gaia match" is NOT a discovery: it only marks a source worth a look.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import urllib.parse

from . import config, grid as gridmod, net
from .targets import ProperMotion, mjd_to_year, propagate

TAP_SYNC = config.IRSA + "TAP/sync"
TAP_TIMEOUT_S = 30   # a hung TAP query must not hold a server thread for minutes
GAIA_EPOCH = 2016.0
FAST_PM_MAS = 500.0             # entries faster than this are checked for duplicates of one object
MERGE_RADIUS_ARCSEC = 8.0
MOVING_MIN_MAS = 150.0          # "clearly moving": at least this fast and at least 5 sigma
MOVING_MIN_SIGMA = 5.0
# Around a saturated star CatWISE lists dozens of false detections with large random motions
# (about 40 of them around Barnard's Star, G = 8.2). A fast, unmatched CatWISE entry this close to such a
# star is dropped; the star itself is still shown from Gaia.
BRIGHT_STAR_G_MAG = 9.5
BRIGHT_STAR_RADIUS_ARCSEC = 180.0
MATCH_RADIUS_ARCSEC = 3.0       # a CatWISE source with a Gaia source this close is "the same object"
PM_MARGIN_ARCSEC = 130.0        # fast stars (Barnard: 10″/yr) were this far away at the catalog epoch
MAX_ROWS = 300
RELEASES = {"gaia": "Gaia DR3", "catwise": "CatWISE2020"}


def _tap(query: str) -> list[dict]:
    url = TAP_SYNC + "?" + urllib.parse.urlencode({"QUERY": query, "FORMAT": "CSV"})
    with net.urlopen(url, timeout=TAP_TIMEOUT_S) as r:
        body = r.read().decode()
    if not body or body.lstrip().startswith("<"):   # errors come back as XML/HTML
        raise OSError("catalog service returned no table")
    return list(csv.DictReader(io.StringIO(body)))


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _cone(ra: float, dec: float, radius_deg: float) -> str:
    return f"CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, {radius_deg:.5f}))=1"


def query_gaia(ra: float, dec: float, radius_deg: float) -> list[dict]:
    rows = _tap(f"SELECT TOP {MAX_ROWS} source_id, ra, dec, pmra, pmdec, phot_g_mean_mag "
                f"FROM gaia_dr3_source WHERE {_cone(ra, dec, radius_deg)} ORDER BY phot_g_mean_mag")
    out = []
    for r in rows:
        sra, sdec = _num(r["ra"]), _num(r["dec"])
        if sra is None or sdec is None:
            continue
        pmra, pmdec = _num(r["pmra"]), _num(r["pmdec"])
        out.append({"id": f"gaia:{r['source_id']}", "catalog": "gaia", "ra": sra, "dec": sdec,
                    "epoch": GAIA_EPOCH, "pmra": pmra, "pmdec": pmdec, "pm_sigma": None,
                    "mag": _num(r["phot_g_mean_mag"]), "mag_band": "G"})
    return out


def query_catwise(ra: float, dec: float, radius_deg: float) -> list[dict]:
    rows = _tap(f"SELECT TOP {MAX_ROWS} source_name, ra, dec, meanobsmjd, pmra, pmdec, sigpmra, sigpmdec, "
                f"w2mpro_pm FROM catwise_2020 WHERE {_cone(ra, dec, radius_deg)} ORDER BY w2mpro_pm")
    out = []
    for r in rows:
        sra, sdec, mjd = _num(r["ra"]), _num(r["dec"]), _num(r["meanobsmjd"])
        if sra is None or sdec is None or mjd is None:
            continue
        pmra, pmdec = _num(r["pmra"]), _num(r["pmdec"])
        era, edec = _num(r["sigpmra"]), _num(r["sigpmdec"])
        sigma = None
        if pmra is not None and pmdec is not None and era and edec:
            sigma = math.hypot(pmra, pmdec) / math.hypot(era, edec)     # motion in units of its error
        out.append({"id": f"catwise:{r['source_name']}", "catalog": "catwise", "ra": sra, "dec": sdec,
                    "epoch": mjd_to_year(mjd),
                    "pmra": None if pmra is None else pmra * 1000.0,      # arcsec/yr → mas/yr
                    "pmdec": None if pmdec is None else pmdec * 1000.0,
                    "pm_sigma": sigma, "mag": _num(r["w2mpro_pm"]), "mag_band": "W2"})
    return out


def _sep_arcsec(a: tuple[float, float], b: tuple[float, float]) -> float:
    dra = (a[0] - b[0] + 180.0) % 360.0 - 180.0
    return 3600.0 * math.hypot(dra * math.cos(math.radians((a[1] + b[1]) / 2)), a[1] - b[1])


def project(raw: list[dict], ra: float, dec: float, fov: float, epoch: float = config.SPHEREX_MID_EPOCH) -> dict:
    """
    Catalog rows → sources on the blink grid centred on (ra, dec): where each source is at `epoch`
    (moved by its proper motion) and how many pixels it moves per year.
    """
    wcs, (ny, nx) = gridmod.make_grid(ra, dec, fov)
    placed = []
    for s in raw:
        pm = ProperMotion(s["pmra"] or 0.0, s["pmdec"] or 0.0, s["epoch"])
        now = propagate(s["ra"], s["dec"], pm, epoch)
        x, y = gridmod.sky_to_pix(wcs, *now)
        x1, y1 = gridmod.sky_to_pix(wcs, *propagate(s["ra"], s["dec"], pm, epoch + 1.0))
        placed.append((s, now, x, y, x1 - x, y1 - y))
    gaia_now = [now for s, now, *_ in placed if s["catalog"] == "gaia"]
    bright = [s for s in raw if s["catalog"] == "gaia" and s["mag"] is not None and s["mag"] < BRIGHT_STAR_G_MAG]

    def near_bright_star(c: dict) -> bool:
        for b in bright:   # compare where both were at the CatWISE entry's own epoch
            pos = propagate(b["ra"], b["dec"], ProperMotion(b["pmra"] or 0.0, b["pmdec"] or 0.0, b["epoch"]),
                            c["epoch"])
            if _sep_arcsec((c["ra"], c["dec"]), pos) <= BRIGHT_STAR_RADIUS_ARCSEC:
                return True
        return False

    sources, fast_kept, dropped = [], [], 0
    for s, now, x, y, dx, dy in placed:      # rows arrive brightest first, so the brightest duplicate is kept
        if not (-0.5 <= x <= nx - 0.5 and -0.5 <= y <= ny - 0.5):
            continue
        speed = math.hypot(s["pmra"] or 0.0, s["pmdec"] or 0.0)
        if s["catalog"] == "gaia":
            status = "gaia"
        else:
            status = "gaia_match" if any(_sep_arcsec(now, g) <= MATCH_RADIUS_ARCSEC for g in gaia_now) \
                else "no_gaia_match"
            if status == "no_gaia_match" and speed >= MOVING_MIN_MAS and near_bright_star(s):
                dropped += 1
                continue
        if s["catalog"] == "catwise" and speed >= FAST_PM_MAS:
            if any(_sep_arcsec(now, k) <= MERGE_RADIUS_ARCSEC for k in fast_kept):
                continue
            fast_kept.append(now)
        sources.append({
            "id": s["id"], "catalog": s["catalog"], "x": round(x, 2), "y": round(y, 2),
            "ra": round(now[0], 6), "dec": round(now[1], 6),
            "mag": None if s["mag"] is None else round(s["mag"], 2), "mag_band": s["mag_band"],
            "pmra": None if s["pmra"] is None else round(s["pmra"], 1),
            "pmdec": None if s["pmdec"] is None else round(s["pmdec"], 1),
            "dx_per_yr": round(dx, 4), "dy_per_yr": round(dy, 4), "match_status": status,
            # Gaia motions are precise; a CatWISE motion counts only when it is well above its error
            "moving": bool(speed >= MOVING_MIN_MAS and (s["catalog"] == "gaia" or
                                                        (s.get("pm_sigma") or 0.0) >= MOVING_MIN_SIGMA)),
        })
    return {"sources": sources, "grid_id": gridmod.grid_payload(wcs, (ny, nx))["id"],
            "epoch": epoch, "match_radius_arcsec": MATCH_RADIUS_ARCSEC, "releases": RELEASES,
            "dropped_near_bright_star": dropped}


def _looks_synthetic(row: dict) -> bool:
    """Real Gaia DR3 source_ids are 19 digits without long zero runs; CatWISE names carry two decimals in Dec.
    Hand-made placeholder rows (seen 14 Nov: gaia:6412760000000001, catwise:J220410.5-564658) fail this."""
    rid = str(row.get("id", ""))
    if rid.startswith("gaia:"):
        sid = rid[5:]
        return not (sid.isdigit() and 15 <= len(sid) <= 19) or "000000" in sid
    if rid.startswith("catwise:"):
        return re.fullmatch(r"J\d{6}\.\d{2}[+-]\d{6}\.\d", rid[8:]) is None
    return True


def fetch(ra: float, dec: float, fov: float, use_cache: bool = True, allow_download: bool = True) -> list[dict]:
    """Raw Gaia + CatWISE rows around the field (cached). Raises OSError if IRSA does not answer."""
    radius = (fov * 0.71 + PM_MARGIN_ARCSEC) / 3600.0
    # v3: every cache file written before 15 Nov is ignored (synthetic files were found under v2 keys)
    key = hashlib.sha1(f"v3|{ra:.5f}|{dec:.5f}|{radius:.5f}".encode()).hexdigest()[:16]
    path = config.CACHE_DIR / "catalog" / f"{key}.json"
    shipped = config.SHIPPED_DIR / "catalog" / f"{key}.json"
    if use_cache and shipped.exists():
        return json.loads(shipped.read_text(encoding="utf-8"))
    if not allow_download:
        raise OSError("catalog not cached and downloads are disabled")
    if use_cache and path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if not any(_looks_synthetic(r) for r in cached):
            return cached
    raw = query_gaia(ra, dec, radius) + query_catwise(ra, dec, radius)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw), encoding="utf-8")
    return raw
