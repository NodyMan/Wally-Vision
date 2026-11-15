"""
Export the preset answers of the running backend into the frontend, so the site works on Vercel alone
(no Python host): frontend/lib/demo/demo-data.json + frontend/public/api/frame/<id>.png.

Only real results are exported: the blink JSON written by scripts/prefetch.py (viewer/static_cache), and the
light-curve / spectrum answers the API gives for the presets (from viewer/static_cache/science). Nothing is
computed or invented here.

    python scripts/export_demo_api.py [API base, default http://127.0.0.1:8010]

Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FRONTEND = BACKEND.parent / "frontend"
STATIC = BACKEND / "viewer" / "static_cache"
OUT_JSON = FRONTEND / "lib" / "demo" / "demo-data.json"
OUT_FRAMES = FRONTEND / "public" / "api" / "frame"


def get(url: str) -> tuple[int, dict | list]:
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main() -> None:
    api = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
    status, presets = get(f"{api}/api/presets")
    assert status == 200 and len(presets) == 5, (status, presets)

    OUT_FRAMES.mkdir(parents=True, exist_ok=True)
    for old in OUT_FRAMES.glob("*.png"):
        old.unlink()
    out = {"presets": presets, "targets": []}
    for p in presets:
        slug = p["slug"]
        blinks = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((STATIC / slug).glob("blink_*.json"))]
        for png in (STATIC / slug / "frames").glob("*.png"):
            shutil.copy2(png, OUT_FRAMES / png.name)
        t = blinks[0]["target"]
        centers = [[p["ra"], p["dec"]], [t["ra"], t["dec"]]]
        if t.get("catalog_ra") is not None:
            centers.append([t["catalog_ra"], t["catalog_dec"]])
        science = {}
        # exactly the requests the viewer sends (same as scripts/warm_science.py)
        status, blink = get(f"{api}/api/blink?ra={p['ra']}&dec={p['dec']}&fov={p['fov']}"
                            f"&detector={p['default_detector']}&mode={p['default_mode']}")
        assert status == 200, (slug, status)
        bt = blink["target"]
        for kind in ("lightcurve", "spectrum"):
            q = {"ra": bt["ra"], "dec": bt["dec"], "cra": p["ra"], "cdec": p["dec"], "fov": p["fov"]}
            if kind == "lightcurve":
                q["detector"] = p["default_detector"]
            status, body = get(f"{api}/api/{kind}?{urllib.parse.urlencode(q)}")
            assert status in (200, 422), (slug, kind, status, body)
            science[kind] = {"status": status, "body": body,
                             "detector": p["default_detector"] if kind == "lightcurve" else None}
        out["targets"].append({"slug": slug, "centers": centers, "blinks": blinks, "science": science})
        print(f"{slug}: {len(blinks)} blink answers, lightcurve {science['lightcurve']['status']}, "
              f"spectrum {science['spectrum']['status']}")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size // 1024} KB), {len(list(OUT_FRAMES.glob('*.png')))} frames")


if __name__ == "__main__":
    main()
