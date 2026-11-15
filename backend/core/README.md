# backend/core — SkyBlink pipeline (role #1)

Pure-Python core with no Django inside. The `viewer` Django app (async `/api/blink`) wraps it.
Source: research/core/spike.py, validated on real data (the Barnard and Eps Ind B dipoles land inside the proper-motion rings).

| Module | What it does |
|---|---|
| `config.py` | Constants: IRSA URLs, 6.15″/px, detector ranges, FLAGS policies, `SKYBLINK_CACHE` |
| `net.py` | HTTPS with a proper certificate store (truststore/certifi). Only IRSA URLs are allowed |
| `targets.py` | `ProperMotion`, `propagate()` from J2000 to the observation epoch, PM values for the presets |
| `spherex.py` | `find_images()` (SIA2, cached), `fetch_cutout()` (retries on 503, checks the `SIMPLE` header, cached) |
| `epochs.py` | `group_epochs` (gap > 60 days; 30-day bins as fallback), `auto_wl_window`, `choose_diff_pair` |
| `grid.py` | Shared TAN grid, `sky_to_pix`/`pix_to_sky` in **canvas** coordinates (0-based, y down) |
| `imaging.py` | FLAGS mask (SOURCE is not masked), reprojection, stacking, PNG (shared stretch) |
| `blink.py` | `build_blink(ra, dec, fov, detector, mode, …)` → (response per COMMON §6, {frame_id: png}) |

```bash
cd backend
pip install astropy reproject numpy pillow truststore pytest
python -m pytest core/tests -q            # 12 tests, no network (synthetic data)
set SKYBLINK_CACHE=C:\skyblink_cache      # cache outside OneDrive
python scripts/prefetch.py barnard        # real data → viewer/static_cache/<slug>/ (commit the PNG + JSON)
```

For the Django view (H8+), `build_blink` already accepts:

- `progress(stage, fraction)` — feeds `job.progress`/`job.stage`;
- `BlinkError.code` — maps to the HTTP error codes;
- `frame_path(fid)` + `save_frames()` — serve `/api/frame/<id>.png`.

FITS files are never committed. Only the small PNG/JSON for the presets are.

Developed with SI assistance (Claude); reviewed by team #1.
