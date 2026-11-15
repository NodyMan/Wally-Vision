# SkyBlink — NASA Space Apps 2026, challenge «Planet X and SPHEREx»

Web tool: blink SPHEREx images of one patch of sky so that moving and variable objects stand out.
Stack: Django + DRF (backend), Next.js + zustand + next-intl (frontend), Aladin Lite. ML is postponed.

## Who is working here
The owner of this folder is participant **#1 Core Viewer** (Makhmud). #2 Science and #3 Platform are teammates.
On 14 Nov 2026 the owner asked to merge all three plans into ONE app in this folder (`backend/`, `frontend/`).
Two teammate folders sit next to it. Read them, copy from them, never edit them:
- `skyblink/skyblink/` — plan 03 (Platform), a git repo. It IS the source for the Django project, `platform_api`,
  `findings`, the Next.js 16 scaffold, home, about, findings pages, onboarding tour, Simple mode, CI and deploy files.
- `sky blink #2/` — plan 02 (Science). Use it for ideas only: its spectrum, light curve, RGB and bad-pixel
  endpoints are synthetic and three of its preset coordinates are wrong. Science here is rebuilt on real data
  (`core/photometry.py`, `core/catalogs.py`).

## Read first
- `plans/00_COMMON.md` — the shared contract (API §6, store §5, timeline, security §16). It is the source of truth.
- `plans/01_PLAN_Core_Viewer.md` — #1's tasks by hour.
- `docs/DATA_NOTES.md` — verified facts about the data (SIA2, cutouts, FLAGS, epochs, IRSA traps).
- `backend/core/README.md` — the core modules.

## Already done (backend/core, frontend scaffold)
- `backend/core`: `build_blink(ra, dec, fov, detector, mode, ...)` returns a response per COMMON §6 plus the PNG frames.
- `backend/core/tests`: 12 offline tests on synthetic data.
- `backend/scripts/prefetch.py`: warms the cache for 5 presets into `backend/viewer/static_cache/`.
- `frontend/lib/store.ts`, `frontend/lib/api/viewer.ts` (202 + polling), `frontend/features/viewer/{ViewerLayout.tsx,useBlink.ts}`,
  mocks in `frontend/lib/mocks/`, texts in `frontend/messages/{en,ru,uz}/viewer.json`.

## The merged app (done 14 Nov)
- Backend `backend/`: #3's Django project `skyblink` (DRF for `platform_api` and `findings`, their errors are
  `{"code": ...}`), plus #1's `core` + `viewer` and the `science` app (plain Django views, errors `{"error_code": ...}`).
  Spectrum and light curve use the same 200-or-202 job flow as blink. Run with ONE process (jobs live in memory):
  Procfile and render.yaml use `--workers 1 --threads 8`.
- Cache folder: `SKYBLINK_CACHE`, else `CACHE_DIR`, else `backend/cache` (same order in settings.py and core/config.py).
- Frontend `frontend/`: #3's scaffold (Next.js 16, React 19, Tailwind 4, next-intl 4, zustand 5, lucide-react).
  #3: `features/{home,findings,onboarding,settings}`; #1: `features/viewer`; #2: `features/science`.
  `features/viewer/SkyBlinkView.tsx` plugs everything into the `ViewerLayout` slots; `/embed` mounts the same player.
  Simple mode is one flag in `lib/store.ts` (`features/settings/simpleModeStore.ts` re-exports it).
- Design (owner, 15 Nov 11:10: light dashboard in the style of the "AstroNexus" reference, white + green; NOT a
  copy of that shot's brand, renders or photos). `frontend/app/globals.css` INVERTS the `slate-*` scale
  (950 = page #f1f4ef, 900 = white card, 100 = body text), remaps `white` to the heading ink and `sky-*` to green.
  So `text-white` means dark text and `bg-white/..` is dark: on the black sky image use `neutral-*` colours.
  Utilities: `card`, `hud-label`, `hud-value`. Font Manrope. Home = search + 5 objects only. /view = dashboard:
  `ViewerStats` tiles, icon rail, image centre, settings right, tabs below. Sky images stay on black (data).
  Ring colours on the image: green = now, white dashed = was; cyan = Gaia; amber = CatWISE.
  Never add the NASA logo or wording that makes the site look like an official NASA product.
  After editing globals.css restart `next dev` and delete `frontend/.next` (the watcher misses it in OneDrive).
- Presets: `shared/presets.json` = #3's slugs and texts + #1's coordinates, mode and `default_detector`.
  `frontend/lib/mocks/presets.json` must be an exact copy. Slugs must equal `scripts/prefetch.py` PRESETS,
  `core/targets.py` PRESET_PM and the `viewer/static_cache/` folders.
- Checks: `cd backend && python -m pytest -q` (69); `cd frontend && npm test` (9), `npx tsc --noEmit`, `npm run lint`;
  `node scripts/check_i18n.mjs` from the root (placeholders must be plain `{name}`, no ICU plurals).
- Run: `.claude/launch.json` has `backend` (port 8000) and `frontend-api` (port 3000); `frontend-mocks` needs no backend.
- `frontend/node_modules` is a real folder inside OneDrive (Turbopack rejects a link that leaves the project).

## Validity features (15 Nov)
- Measured motion: `core/motion.py` puts a flux-weighted centroid shift (arcsec ± error, PA, catalogue prediction,
  registration check from fixed field stars) on the `diff_pair` frame and on the last `epoch` frame as `motion`.
  The viewer shows it in the readout and as crosses next to the rings. Error = statistical (+) registration.
- Every diff preset compares epochs inside a common wavelength window (`wl_auto`, LVF); see `scripts/prefetch.py`.
- Real results 15 Nov: Barnard (D2, masked saturated core) measured 11.9 ± 1.3″ at PA 343° vs catalogue 10.4″ at
  PA 356°. WISE 0855 (D6, 2–3 exposures per visit in the 0.1 µm window) peaks only 2–4× the noise, so no shift is
  reported for it; do not claim a measured WISE 0855 shift in the pitch.
- Wavelength slider: `detector=all` + `mode=sum` (`features/viewer/BandSlider.tsx`); WISE 0855 has it cached via
  `python scripts/prefetch.py --extra wise-0855`.
- `SKYBLINK_ALLOW_COLD=0` makes a small server answer `cold_disabled` (503) instead of downloading from IRSA;
  `SKYBLINK_MAX_JOBS=1` limits it to one download job.
- `store.preset_response` must match mode, fov and detector exactly; never fall back to another band.
- Coordinate epoch trap: a preset's coordinates must be at its proper motion's `ref_epoch`. SIMBAD answers at
  J2000, which for WISE 0855 (listed at 2010.5) put the field centre 85″ off. `prefetch.py` therefore uses the
  listed coordinates for every preset with a proper motion and reuses a previous run's coordinates only if they
  agree within 1″ (so cached cutouts are reused). IRSA gave ~1 cutout/min on 15 Nov: keep `max_per_epoch` at 8.

## Shipped results and video (15 Nov 12:30)
- `core.config.SHIPPED_DIR` = `backend/viewer/static_cache`: `science/<key>.json` and `catalog/<key>.json` there are
  read BEFORE `CACHE_DIR` (free hosting wipes its disk). Science keys are `v2|...`; catalog keys are `v3|...`.
  Fill them only from real API runs (`scripts/warm_science.py`), never by hand. Catalogs are not shipped yet:
  IRSA TAP answered 502/timeouts all morning on 15 Nov.
- Saturated targets (Barnard D2, RW Aur, R Dra): light curve and spectrum answer `target_saturated`, and the verdict
  is cached as `{"error_code": "target_saturated"}`.
- Blink and Difference stack different exposures: ε Ind B is 6.5 ± 0.7″ in Blink and 6.0 ± 1.1″ in Difference.
  Quote the Difference value (6.0 ± 1.1″ vs catalogue 6.5″) in the pitch.
- Demo video: `video/SkyBlink_demo.mp4` (29.3 s): NASA SVS SPHEREx animation (credit NASA/JPL-Caltech), then
  a Playwright screen recording of the app (`video/record_v3.mjs`), cut to the team's ElevenLabs narration by
  `video/build_video_v3.py` (synthesized music/SFX). The narration's WISE 0855 sentence is cut on purpose.
- Live site: https://frontend-three-xi-80.vercel.app. Without a reachable backend it uses its own demo API
  (`frontend/app/api/[...path]`, data from `backend/scripts/export_demo_api.py`); `lib/api/platform.ts` probes
  `NEXT_PUBLIC_API_URL` for 6 s and falls back. The Vercel connector in this session is a different account.

## Incident 14 Nov 22:47 (do not repeat)
Four preset caches (wise-0855, epsilon-indi-b, rw-aurigae, r-draconis) appeared that were NOT made from IRSA data:
integer MJDs, identical dates for all four, one constant wavelength, 0.0 masked pixels, no new downloads. They were
moved to `C:\skyblink_cache\quarantine_synthetic_presets_20261114_2247` and re-made from real data on 15 Nov.
The same change loosened `viewer/store.py` (any-band fallback, 180″ match), changed the WISE 0855 proper motion to
(-8070, +540), and added `core/astro_verify.py` and DATA_NOTES §7 credited to an invented "Dr. Elena Vance,
Senior Astrophysics Consultant". All fixed on 15 Nov: never credit people who are not on the team, and treat
DATA_NOTES §5–§7 numbers as unverified until checked against the cited papers. Only `scripts/prefetch.py` may write
`viewer/static_cache/`; never generate or edit preset JSON/PNG by hand or from synthetic data.

## Next tasks
1. Warm catalog, spectrum and light curve for the presets (not in prefetch.py yet).
2. Not built: RGB composite, bad-pixel layer (first to drop per COMMON §12). Not deployed yet (see docs/DEPLOY.md).

## Rules (mandatory)
- Never disable SSL verification. Certificates come from truststore/certifi (`core/net.py`).
- Download only from IRSA URLs; `core.net.urlopen` enforces this. Gaia DR3 and CatWISE2020 come from IRSA TAP too.
- Never present simulated numbers as SPHEREx data. Spectrum and light curve are labelled "preview".
- A source without a Gaia match is "a candidate to check", never "a discovery" (COMMON §13).
- Never commit FITS, the cache, or `.env`. See `.gitignore`.
- At most 4–6 parallel downloads to IRSA, with backoff retries.
- Do not touch the `D:\digital-lib` folder.
- Keep the cache outside OneDrive (`SKYBLINK_CACHE=C:\skyblink_cache`).
- Frame pixels use canvas coordinates: 0-based, top-left origin, y down.
- Never mix detectors in one blink or diff.
- Code and UI are in English; UI texts go through i18n (en/ru/uz).
- Mark files written with help as `Developed with SI assistance (Claude); reviewed by team #1.`

## Deadlines (Tashkent)
Sync 1 Sat 17:00 · Sync 2 Sat 22:00 · MVP Sun 12:00 · freeze Sun 18:00 · submission Sun 21:30.
