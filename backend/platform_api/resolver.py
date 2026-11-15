"""Coordinate parser and CDS Sesame object-name resolver for SkyBlink."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.utils.data import conf as astropy_data_conf
from django.conf import settings
from django.core.cache import cache


class ResolveError(Exception):
    """Raised when an object name or coordinate string cannot be resolved."""

    def __init__(self, code: str = "not_found", message: str = "Target not found"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ResolvedTarget:
    ra: float
    dec: float
    name: str
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


# Decimal degrees: "133.795 -7.245", "133.795, +7.245", or "0° 0°"
_DECIMAL_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*(?:,|\s)\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*$"
)

# Sexagesimal HMS + DMS with h/m/s and d/m/s (or degree/arcmin/arcsec symbols)
_HMS_DMS_RE = re.compile(
    r"^\s*(\d{1,2})\s*h\s*(\d{1,2})\s*m\s*(\d{1,2}(?:\.\d+)?)?\s*s?"
    r"\s*(?:,|\s)\s*"
    r"([+-]?\d{1,2})\s*[d°]\s*(\d{1,2})\s*[m′']\s*(\d{1,2}(?:\.\d+)?)?\s*[s″\"]?\s*$",
    re.IGNORECASE,
)

# Colon-separated HMS + DMS: "08:55:10.8 -07:14:42" or "08:55 -07:14"
_COLON_RE = re.compile(
    r"^\s*(\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)"
    r"\s*(?:,|\s)\s*"
    r"([+-]?\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)\s*$"
)

# Heuristic to detect malformed coordinate strings so they do NOT leak into CDS Sesame
_LOOKS_LIKE_COORDS_RE = re.compile(
    r"^\s*(?:[+-]?\d+(?:\.\d+)?\s*[°dhms]?\s*[:,\s]\s*[+-]?\d+|\d+\s*h\s*\d+\s*m)",
    re.IGNORECASE,
)


def _normalize_query(raw: str) -> str:
    """Normalize unicode minus and whitespace."""
    text = raw.strip()
    text = text.replace("\u2212", "-").replace("\u2013", "-")
    text = re.sub(r"\s+", " ", text)
    return text


def _strip_coord_labels(text: str) -> str:
    """Strip optional 'RA' / 'Dec' prefixes so copied catalog strings parse cleanly."""
    cleaned = re.sub(r"\bRA\s*[:=]?\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bDec\s*[:=]?\s*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_ra_deg(ra_deg: float) -> float:
    rounded = round(float(ra_deg), 6)
    if rounded >= 360.0 or rounded < 0.0:
        rounded = round(rounded % 360.0, 6)
        if rounded >= 360.0:
            rounded = 0.0
    return rounded


def parse_coordinates(raw: str) -> Optional[ResolvedTarget]:
    """Parse RA/Dec strings in decimal degrees, HMS/DMS, or colon format."""
    display_text = _normalize_query(raw)
    text = _strip_coord_labels(display_text)
    if not text:
        return None

    m_dec = _DECIMAL_RE.match(text)
    if m_dec:
        ra = float(m_dec.group(1))
        dec = float(m_dec.group(2))
        if 0.0 <= ra <= 360.0 and -90.0 <= dec <= 90.0:
            coord = SkyCoord(ra=(ra % 360.0) * u.deg, dec=dec * u.deg, frame="icrs")
            return ResolvedTarget(
                ra=_normalize_ra_deg(coord.ra.deg),
                dec=round(float(coord.dec.deg), 6),
                name=display_text,
                source="coords_deg",
            )
        return None

    m_hms = _HMS_DMS_RE.match(text)
    if m_hms:
        rh, rm, rs, dd, dm, ds = m_hms.groups()
        ra_str = f"{int(rh)}h{int(rm)}m{float(rs or 0):.4f}s"
        dec_str = f"{dd}d{int(dm)}m{float(ds or 0):.4f}s"
        try:
            coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg), frame="icrs")
        except Exception:
            return None
        return ResolvedTarget(
            ra=_normalize_ra_deg(coord.ra.deg),
            dec=round(float(coord.dec.deg), 6),
            name=display_text,
            source="coords_hms",
        )

    m_col = _COLON_RE.match(text)
    if m_col:
        ra_str, dec_str = m_col.groups()
        try:
            coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg), frame="icrs")
        except Exception:
            return None
        return ResolvedTarget(
            ra=_normalize_ra_deg(coord.ra.deg),
            dec=round(float(coord.dec.deg), 6),
            name=display_text,
            source="coords_colon",
        )

    return None


def _looks_like_invalid_coordinates(raw: str) -> bool:
    stripped = _strip_coord_labels(_normalize_query(raw))
    return bool(_LOOKS_LIKE_COORDS_RE.match(stripped))


def _preset_fallback(query: str) -> Optional[ResolvedTarget]:
    """Match common short or localized names against shared/presets.json."""
    presets_file = Path(settings.SHARED_DIR) / "presets.json"
    if not presets_file.exists():
        return None
    try:
        presets = json.loads(presets_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    needle = _normalize_query(query).lower().replace("'", "").replace("’", "")
    aliases = {
        "wise 0855": "wise-0855",
        "wise 0855-0714": "wise-0855",
        "wise0855": "wise-0855",
        "barnards star": "barnards-star",
        "barnard star": "barnards-star",
        "epsilon indi b": "epsilon-indi-b",
        "eps indi b": "epsilon-indi-b",
        "rw aur": "rw-aurigae",
        "rw aurigae": "rw-aurigae",
        "r dra": "r-draconis",
        "r draconis": "r-draconis",
    }
    target_slug = aliases.get(needle)

    for item in presets:
        slug = item.get("slug", "")
        titles = [str(v).lower().replace("'", "") for v in item.get("title", {}).values()]
        if slug == target_slug or slug == needle or needle in titles:
            return ResolvedTarget(
                ra=float(item["ra"]),
                dec=float(item["dec"]),
                name=item["title"].get("en", query),
                source="preset",
            )
    return None


def _cache_file_for(digest: str) -> Path:
    cache_dir = Path(settings.CACHE_DIR) / "resolve"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{digest}.json"


def resolve_via_sesame(name: str) -> SkyCoord:
    """Resolve an astronomical object name using CDS Sesame via Astropy."""
    with astropy_data_conf.set_temp("remote_timeout", 3.0):
        return SkyCoord.from_name(name, frame="icrs", parse=False)


def resolve_target(raw_query: str) -> ResolvedTarget:
    """Resolve coordinates or an astronomical name into ICRS (ra, dec) degrees."""
    query = _normalize_query(raw_query)
    if not query:
        raise ResolveError("not_found", "Empty query")

    parsed = parse_coordinates(query)
    if parsed is not None:
        return parsed

    if _looks_like_invalid_coordinates(query):
        raise ResolveError("not_found", f"Invalid coordinates '{query}'")

    # Fast-path localized or shorthand preset names before hitting external Sesame
    preset_match = _preset_fallback(query)
    if preset_match is not None:
        return preset_match

    digest = hashlib.sha256(query.lower().encode("utf-8")).hexdigest()[:24]
    cache_key = f"resolve_{digest}"
    cached = cache.get(cache_key)
    if cached is not None:
        return ResolvedTarget(**cached)

    disk_file = _cache_file_for(digest)
    if disk_file.exists():
        try:
            data = json.loads(disk_file.read_text(encoding="utf-8"))
            cache.set(cache_key, data, timeout=86400)
            return ResolvedTarget(**data)
        except Exception:
            pass

    try:
        coord = resolve_via_sesame(query)
        result = ResolvedTarget(
            ra=_normalize_ra_deg(coord.ra.deg),
            dec=round(float(coord.dec.deg), 6),
            name=query,
            source="sesame",
        )
    except Exception:
        raise ResolveError("not_found", f"Could not resolve '{query}'")

    payload = result.to_dict()
    cache.set(cache_key, payload, timeout=86400)
    try:
        disk_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return result
