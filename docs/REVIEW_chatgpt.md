# SkyBlink — review and recommendations
**Review date:** 14 November 2026  
**Reviewed files:** `PLAN_SPHEREx_SkyBlink.md`, `00_COMMON.md`, `01_PLAN_Core_Viewer.md`

## Executive summary
The original plans have a good product direction and a sensible data-first workflow, but they were not safe to hand to several coding agents simultaneously. The documents contradicted each other on repository layout, work ownership, API field names and response shapes. More importantly, the original data-processing plan did not sufficiently account for the wavelength variation across SPHEREx's linear variable filters (LVFs).

The revised files now designate `00_COMMON.md` as the single technical source of truth. The main plan owns product goals and phases; `01_PLAN_Core_Viewer.md` owns only participant #1's tasks.

## Critical fixes made

1. **One repository structure:** aligned all plans on `backend/{skyblink,core,viewer,science,platform_api,findings}`, `frontend/{app,features,lib,messages}`, `research/`, `shared/`, and `docs/`. Removed the competing `backend/sky/services` and route-tree descriptions.
2. **One team model:** aligned all documents on three full-stack vertical roles: Core Viewer, Science Layers, Platform & People.
3. **One API contract:** standardized `/api/health` as `{"status":"ok"}`, `detector` for API requests, `det` only as an optional page URL alias, and `grid.wcs_header` as the full WCS payload. Added frame semantics and error codes.
4. **Detector sequences are separate:** do not average six detectors into one grayscale image. Each detector covers a different wavelength band; `detector=all` returns independent sequences.
5. **LVF wavelength matching:** even within one detector, wavelength varies with detector-pixel position. Two observations of the same sky position can therefore sample different wavelengths. The revised plan requires wavelength metadata at the target position and wavelength-matched epochs for photometric diff/variability claims.
6. **Current data releases:** updated the old QR-only assumptions to DR1 + QR3 for new searches. QR2 is no longer searchable via SIA2 and should not be casually mixed with DR1/QR3.
7. **FITS details:** documented DR1/QR3 MEF extensions (`IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `EPSF`, `WCS-WAVE`), the QR2 `PSF` difference, the units, and the fact that `ZODI` is not subtracted from `IMAGE`.
8. **Two product types:** separated Level 2 Spectral Image MEFs (time-domain blink) from the DR1 All-Sky Cube (102-channel spectral context, not temporal epochs; about 12.9 arcsec pixels).
9. **WCS correctness:** required full WCS serialization and explicit handling of FITS 1-based `CRPIX` versus 0-based canvas pixels.
10. **Science claims:** removed the implication that a source absent from Gaia is a discovery. It is only a candidate requiring validation.
11. **Photometry and spectra:** added caveats for PSF/ePSF, quality flags, consistent detector band, LVF sampling and calibration. A single clicked pixel is not automatically a scientifically valid spectrum.
12. **Hosting/security:** clarified persistent-cache assumptions, trusted IRSA URLs only, opaque frame cache keys, validation, timeouts, bounded retries, rate limits and CORS.
13. **Competition claims:** relabeled the five targets as the team's test set, not confirmed NASA-mandated targets; removed unverified judging-rubric assumptions.
14. **Submission schedule:** added the official 2026 submission window note; the internal 48-hour plan is not a guarantee of 48 hours before the portal closes.

## Scientific facts verified against official sources

- SPHEREx DR1 was released in November 2026; QR3 releases began in September 2026. DR1 + QR3 supersede QR2 for new work.
- SIA2 collections include `spherex_dr1`, `spherex_dr1_deep`, `spherex_qr3`, `spherex_qr3_deep`, and `spherex_dr1_cube`.
- The SIA2 result supplies `access_url`; use that returned URL rather than constructing FITS paths.
- DR1/QR3 Level 2 MEFs use `EPSF`; QR2 uses `PSF`.
- `WCS-WAVE` contains a lookup table for wavelength and bandwidth. It is intended for visualization; use `CWAVE`/`CBAND` from the Spectral WCS calibration product for science analysis.
- DR1 All-Sky Cube has 102 channels, 12,288 HEALPix tiles, 512×512×102 data per tile, and approximately 12.9 arcsec pixels. Channels 51 and 52 are blank.
- Level 2 Spectral Images have approximately 6.2 arcsec pixels and are the appropriate product for time-domain blink.

## Recommendations before coding

### P0 — do these first
- Run the IRSA spike for both `spherex_dr1` and `spherex_qr3`; save the actual SIA2 table rows and one real cutout FITS file.
- For each of the five project test targets, produce a coverage report: available detector(s), number of observations, unique dates, usable epochs, target-pixel wavelengths, and data-quality summary.
- Confirm the cutout service's `center` and `size` units with the official notebook and one real request. Do not infer units from a URL example.
- Decode `FLAGS` from the current Explanatory Supplement; write the selected mask policy and release version in `DATA_NOTES.md`.
- Implement and test WCS reprojection on a synthetic image and a real cutout. Verify the target lands at the same output pixel across epochs.
- Determine an empirical wavelength-match tolerance for LVF observations. If there are too few matched epochs, disable photometric `diff`/variability claims rather than showing a misleading result.
- Agree on the `BlinkResponse` TypeScript/Python schema before the frontend and backend agents work in parallel.

### P1 — strongly recommended
- Propagate high-proper-motion target coordinates to each observation epoch where proper-motion data and reference epoch are available.
- Keep per-detector sequences separate in the player. Make the selected band visible in the UI.
- Treat all-sky cube spectrum as a separate, non-time-resolved feature.
- Keep a clear distinction between image display stretch and calibrated flux values. Never use display-normalized PNG pixel values for scientific photometry.
- Use persistent disk or object storage only after confirming the hosting configuration; otherwise use small precomputed demo fixtures in a deliberate storage location.
- Add deterministic tests for no-data, missing detector, few-epoch, mismatched wavelength, invalid WCS, and upstream timeout cases.

### P2 — defer if time is short
- Accounts, ML classification, public social features, complex RGB controls, and automated candidate discovery.
- Prioritize a reliable one-detector blink flow, clear uncertainty labels, a stable demo cache, and a clean submission.

## Remaining items that must be checked in the live data spike
These are deliberately not asserted as settled facts in the revised plans:
- Actual coverage and usable epoch counts for the five test targets.
- Whether each target has enough observations with matching detector and target-pixel wavelength for temporal differencing.
- Exact cutout-service parameter units and behavior for the chosen request sizes.
- Exact flag-bit policy to mask for the intended visual/science use.
- Empirical detector/wavelength mapping and target-pixel wavelength metadata in the actual DR1/QR3 files.
- Whether the proposed 25-second API timeout and chosen hosting plan are sufficient in production.

## Official sources consulted
- IRSA Data Releases: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/
- IRSA Data Products: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/
- IRSA Data Access / SIA2: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- SPHEREx Instrument: https://spherex.caltech.edu/page/instrument
- NASA Space Apps 2026: https://www.spaceappschallenge.org/2026/
- Challenge brief: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/
