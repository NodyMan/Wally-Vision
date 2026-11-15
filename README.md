# SkyBlink

**Blink NASA SPHEREx infrared images of one patch of sky and see what moved.**

Built for **NASA Space Apps Challenge 2026** — *Planet X and SPHEREx*.

---

## Problem
NASA's **SPHEREx** space telescope maps the entire sky roughly every 6 months across **102 near-infrared spectral bands** (0.75–5.0 µm). Finding fast-moving nearby objects (brown dwarfs, high-proper-motion stars, asteroids, or a hypothetical Planet X) and variable stars in raw multi-extension FITS cutouts requires aligning images from different epochs, normalizing brightness scales, and cross-matching catalogs — a workflow far too technical for the general public.

## Solution
**SkyBlink** makes SPHEREx exploration effortless for everyone:
- Enter any astronomical name (`WISE 0855`, `Barnard's Star`) or sky coordinates (`08h55m10.8s -07d14m42s`, `133.795 -7.245`, `08:55:10.8 -07:14:42`), or pick one of **5 featured benchmark targets**.
- Watch multi-epoch SPHEREx cutouts aligned to a common sky grid and animated smoothly (`frames`, `diff`, `sum` modes).
- Explore in **Simple Mode** (for beginners) or **Expert Mode** (Gaia DR3 proper-motion vectors, CatWISE2020 overlays, click-to-spectrum and light-curve previews measured on real exposures).
- Available in **3 languages**: English (`en`), Russian (`ru`), and Uzbek Latin (`uz`), with mobile-first design, keyboard navigation, and `prefers-reduced-motion` support.
- Flag interesting candidates with **"I found something!"**, share direct URLs, or embed the viewer anywhere with `<iframe>`.

**Live demo:** https://frontend-three-xi-80.vercel.app (the five featured fields on real data; see `docs/DEPLOY_QUICK.md` §1c).

**Demo video (29.9 s):** [`video/SkyBlink_demo.mp4`](video/SkyBlink_demo.mp4) — opens with the NASA SVS SPHEREx
spacecraft animation (svs.gsfc.nasa.gov/14966, credit NASA/JPL-Caltech), then screen recordings of the running app on
real SPHEREx data: Epsilon Indi B blink and difference (measured 6.0 ± 1.1″ shift), the wavelength slider, spectrum and
light-curve previews, "I found something!", Uzbek and Russian. Script and shot list: [`video/narration_v4.txt`](video/narration_v4.txt).
**Explainer (1:52):** [`video/SkyBlink_explainer.mp4`](video/SkyBlink_explainer.mp4) — every feature, one scene per paragraph of
[`video/narration_long.txt`](video/narration_long.txt) (`python video/build_video_long.py <narration.mp3>`).
Rebuild: `node video/record_v3.mjs` and `node video/record_v4.mjs` (Playwright, run from a folder with `playwright-core`),
then `python video/build_video_v4.py <narration.mp3>`.
Deployment steps: [`docs/DEPLOY_QUICK.md`](docs/DEPLOY_QUICK.md).

### Results on real data (15 Nov 2026)
| Target | Detector, mode | What SkyBlink measures | Catalogue |
|---|---|---|---|
| Epsilon Indi Ba/Bb | D6, difference | shift **6.0 ± 1.1″** at PA 130° (2025-04-29 → 2026-09-22) | 6.5″ at PA 122° |
| Barnard's Star | D2, difference (saturated core masked) | shift **11.9 ± 1.3″** at PA 343° | 10.4″ at PA 356° |
| WISE 0855−0714 | D6, difference | no shift reported: peak only 2–4× the noise, next to a G = 16.3 background star | 8.1″/yr |
| RW Aurigae, R Draconis | D2, frames | too bright for SPHEREx in this band: light curve and spectrum answer `target_saturated` | — |

Errors are statistical (+) registration (apparent shift of fixed field stars). Blink mode and Difference mode stack
different exposures, so their numbers differ slightly (ε Ind B: 6.5 ± 0.7″ in Blink, 6.0 ± 1.1″ in Difference);
both agree with the catalogue.

### Known limits
- Shifts are not corrected for parallax; between two visits it can add up to twice the parallax (≤ 0.55″ for ε Ind B,
  ≤ 1.1″ for Barnard's Star), which is within the quoted errors.
- The registration check is the size of the apparent shift of 1–3 field stars, not a full astrometric solution.
- Spectrum and light curve are previews: 3×3-pixel photometry on single exposures, no aperture correction.
- Saturated targets (FLAGS bits 1 and 26 over the core) are reported as saturated, never measured.
- The catalog layer needs IRSA TAP; when IRSA is slow the layer reports that the catalog is unavailable instead of guessing.

---

## How to Use
1. **Search or pick a preset** on the home page (e.g. *WISE 0855−0714* or *Barnard's Star*).
2. **Press Play** in the viewer (or use `Space` / `←` / `→`) to blink across SPHEREx observation epochs.
3. **Toggle Diff mode** to highlight moving objects as bright-and-dark pairs, and compare against **Gaia DR3** arrows (an infrared source that clearly moves and has no Gaia match is a candidate worth checking, not a discovery).
4. **Practice first** on `/about` using the 3-case interactive trainer (real motion vs. variable star vs. detector artifact).
5. **Report candidates** using **"I found something!"** to save coordinates to `/findings` and your browser's local list.

---

## NASA & Scientific Data Sources
| What | Exact source | How SkyBlink uses it |
|---|---|---|
| SPHEREx spectral images (Level 2 MEF: IMAGE, FLAGS, VARIANCE, ZODI, WCS-WAVE) | NASA/IPAC IRSA **SIA v2** `https://irsa.ipac.caltech.edu/SIA`, collections **`spherex_dr1`**, **`spherex_qr3`**; IRSA cutout service on each `access_url` | blink, difference, deep sum, spectrum and light-curve previews |
| Gaia DR3 astrometry | IRSA **TAP** `https://irsa.ipac.caltech.edu/TAP`, table **`gaia_dr3_source`** | positions moved to the SPHEREx epoch with proper motion; overlay arrows |
| CatWISE2020 infrared motions | IRSA **TAP**, table **`catwise_2020`** | infrared sources and motions; "moving, no Gaia match" = candidate to check |
| Object names | CDS **Sesame** via `astropy.coordinates.SkyCoord.from_name` | search box |
| Sky context | **Aladin Lite v3** (CDS) with unWISE, 2MASS, DSS2 | "Sky map" tab |
| Software | **Astropy** (WCS, FITS, ZScale/Asinh), **reproject** (`reproject_interp`), NumPy, SciPy | processing pipeline |

What the pipeline does to be fair to the data:
- **Linear variable filters.** Every SPHEREx exposure sees a given star at a different wavelength. SkyBlink reads
  the wavelength at the target from `WCS-WAVE` for every exposure, compares epochs only inside a common
  wavelength window where possible, and warns when the visits were taken at different wavelengths.
- **Sub-pixel motion.** A pixel is 6.15″, so motion is *measured*, not just shown: flux-weighted centroids of the
  target in the first and last visit give the shift in arcseconds, with its error and with the apparent shift of
  bright field stars as a registration check.
- **Honest labels.** Spectrum and light curve are previews (3×3 px photometry on single exposures). An infrared
  source that moves and has no Gaia match is a *candidate to check*, never a discovery.

This project is not affiliated with or endorsed by NASA.

---

## Tech Stack
- **Backend:** Python 3.11, Django 5, Django REST Framework, Astropy, Gunicorn, WhiteNoise, SQLite/PostgreSQL.
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, `next-intl` (`en`, `ru`, `uz`), Zustand, Recharts, Lucide Icons, Aladin Lite v3.
- **Hosting & CI:** GitHub Actions CI (`manage.py check`, `pytest`, `check_i18n.mjs`, `npm run lint`, `npm run build`), Render/Railway (backend), Vercel (frontend).

---

## Local Setup

### Quick Start (Windows)
Double-click or run:
```bat
start_all.bat
```
- Frontend: `http://localhost:3000`
- Backend health check: `http://localhost:8000/api/health`
- Interactive API playground: open [check.html](check.html) directly in a browser

### CLI Tool
```bat
skyblink-cli.bat check
skyblink-cli.bat health
skyblink-cli.bat resolve "08h55m10.8s -07d14m42s"
skyblink-cli.bat presets --lang ru
skyblink-cli.bat findings
```

### Manual Setup
**Backend:**
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
python manage.py migrate
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```

---

## Team Ownership (all three slices merged into this repository)
1. **#1 Core Viewer** — `backend/core/`, `backend/viewer/`, `/view`, `/api/blink`, `BlinkPlayer`, `lib/store.ts`, measured motion
2. **#2 Science Layers** — `backend/science/`, `frontend/features/science/`, Gaia/CatWISE catalogs, spectrum and light-curve previews (RGB composite not built)
3. **#3 Platform & People** — `backend/skyblink/`, `backend/platform_api/`, `backend/findings/`, CI/deploy (`render.yaml`, GitHub Actions), home page, `en`/`ru`/`uz` i18n, `/about` onboarding + 3-case trainer, Simple/Expert mode toggle, `/findings`, `/embed`, CLI & playground

Checks: `cd backend && python -m pytest -q` (81 tests); `cd frontend && npx tsc --noEmit && npm run lint && npm test`;
`node scripts/check_i18n.mjs`.

---

## AI / Super Intelligence (SI) Usage Disclosure
In accordance with **NASA Space Apps Challenge 2026** guidelines, AI coding assistants were used to accelerate boilerplate scaffolding, coordinate-parsing unit tests, multilingual UI translation (`en`/`ru`/`uz`), and accessibility checks. All astronomical logic, API contracts, data validation, and final builds were reviewed and verified by the team. The narration of the demo video is an AI voice (ElevenLabs, voice "Jamie") reading the team's script; the picture is NASA's own SPHEREx animation plus a real screen recording of the app, with no generated imagery; the background music and sound effects are synthesized in `video/build_video_v4.py`.

---

## License
Released under the [MIT License](LICENSE).
