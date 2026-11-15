"""
Warm the spectrum and light-curve caches of the five presets through the running API, with exactly the
parameters the viewer sends (point = blink.target, field centre = preset coordinates, fov 300), so the
"Spectrum" and "Light curve" tabs answer at once during the demo.

    python scripts/warm_science.py [API base, default http://127.0.0.1:8010] [--spectrum-only|--lightcurve-only]

Jobs are submitted one at a time (IRSA limit) and polled until done.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRESETS = json.loads((ROOT.parent / "shared" / "presets.json").read_text(encoding="utf-8"))
# variable stars first for light curves, moving objects first for spectra (what the demo shows)
LC_ORDER = ["rw-aurigae", "r-draconis", "barnards-star", "epsilon-indi-b", "wise-0855"]
SP_ORDER = ["wise-0855", "epsilon-indi-b", "barnards-star", "rw-aurigae", "r-draconis"]


def get(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def run(api: str, path: str, q: dict, label: str) -> None:
    url = f"{api}{path}?{urllib.parse.urlencode(q)}"
    status, body = get(url)
    t0 = time.time()
    if status == 202:
        jid = body["job_id"]
        while True:
            time.sleep(5)
            _, body = get(f"{api}/api/blink/status/{jid}")
            if body.get("status") in ("done", "error"):
                break
        status = 200 if body.get("status") == "done" else 500
        body = body.get("result") or body
    n = len(body.get("points", [])) if isinstance(body, dict) else 0
    print(f"  {label}: HTTP {status}, {n} points, {time.time() - t0:.0f} s {body.get('error_code', '')}", flush=True)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    api = (args[0] if args else "http://127.0.0.1:8010").rstrip("/")
    by_slug = {p["slug"]: p for p in PRESETS}
    for kind, order in (("lightcurve", LC_ORDER), ("spectrum", SP_ORDER)):
        if f"--{'spectrum' if kind == 'lightcurve' else 'lightcurve'}-only" in sys.argv:
            continue
        for slug in order:
            p = by_slug[slug]
            status, blink = get(f"{api}/api/blink?ra={p['ra']}&dec={p['dec']}&fov={p['fov']}"
                                f"&detector={p['default_detector']}&mode={p['default_mode']}")
            if status != 200:
                print(f"  {slug}: blink not cached ({status}), skipped", flush=True)
                continue
            t = blink["target"]
            q = {"ra": t["ra"], "dec": t["dec"], "cra": p["ra"], "cdec": p["dec"], "fov": p["fov"]}
            if kind == "lightcurve":
                q["detector"] = p["default_detector"]
            print(f"▶ {kind} {slug}", flush=True)
            run(api, f"/api/{kind}", q, slug)


if __name__ == "__main__":
    main()
