// Science API (plan #2): catalog overlay, preview spectrum, preview light curve. Contract: 00_COMMON.md §6.
// Everything here is measured from real SPHEREx images and real catalogs; nothing is simulated.
// Developed with SI assistance (Claude); reviewed by team #1.
import { API_BASE, ApiError, getWithJob, type Detector, type Job } from './viewer';

export interface CatalogSource {
  id: string;
  catalog: 'gaia' | 'catwise';
  x: number;                       // frame pixels at the SPHEREx epoch (0-based, integer = pixel centre)
  y: number;
  ra: number;
  dec: number;
  mag: number | null;
  mag_band: 'G' | 'W2';
  pmra: number | null;             // mas/yr
  pmdec: number | null;
  dx_per_yr: number;               // frame pixels per year
  dy_per_yr: number;
  match_status: 'gaia' | 'gaia_match' | 'no_gaia_match';
  moving: boolean;                 // clearly moving: fast, and well above the measurement error
}

/** Infrared, clearly moving, and absent from Gaia: the kind of source this challenge is about. Still only a candidate. */
export function isCandidate(s: CatalogSource): boolean {
  return s.match_status === 'no_gaia_match' && s.moving;
}

export interface CatalogResponse {
  sources: CatalogSource[];
  grid_id: string;                 // must equal blink.grid.id, otherwise the overlay would be misplaced
  epoch: number;
  match_radius_arcsec: number;
  releases: { gaia: string; catwise: string };
}

export interface SeriesPoint {
  date_iso: string;
  date_mjd: number;
  detector: Detector;
  obs_id: string;
  flux: number;                    // MJy/sr, 3×3 px box mean above the local background
  err: number;
  wavelength_um: number | null;    // the wavelength this exposure saw the target at (LVF)
  bandwidth_um: number | null;
  flagged: boolean;                // a quality flag is set inside the box
}

interface SeriesBase {
  points: SeriesPoint[];
  quality: 'preview';
  target: { ra: number; dec: number; moving: boolean };
  n_requested: number;
}
export interface SpectrumResponse extends SeriesBase { features: { key: string; wavelength_um: number }[] }
export interface LightCurveResponse extends SeriesBase { detector: Detector; wavelength_span_um: [number, number] | null }

export interface SeriesRequest {
  ra: number; dec: number;         // the point to measure
  cra: number; cdec: number;       // centre of the field on screen (blink.target): reuses its cutouts
  fov: number;
}

function query(p: SeriesRequest, extra: Record<string, string> = {}): string {
  return new URLSearchParams({ ra: String(p.ra), dec: String(p.dec), cra: String(p.cra), cdec: String(p.cdec),
                               fov: String(p.fov), ...extra }).toString();
}

const catalogCache = new Map<string, Promise<CatalogResponse>>();

/** Gaia DR3 + CatWISE2020 around the field. Slow the first time (10–30 s), so it is cached per field. */
export function fetchCatalog(ra: number, dec: number, fov: number): Promise<CatalogResponse> {
  const key = `${ra}|${dec}|${fov}`;
  let hit = catalogCache.get(key);
  if (!hit) {
    hit = fetch(`${API_BASE}/api/catalog?ra=${ra}&dec=${dec}&fov=${fov}`).then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError((body as { error_code?: string }).error_code ?? 'server_error', res.status);
      }
      return (await res.json()) as CatalogResponse;
    }).catch((e) => {
      catalogCache.delete(key);
      throw e;
    });
    catalogCache.set(key, hit);
  }
  return hit;
}

export function fetchSpectrum(p: SeriesRequest, onProgress?: (j: Job<SpectrumResponse>) => void,
                              signal?: AbortSignal): Promise<SpectrumResponse> {
  return getWithJob<SpectrumResponse>(`${API_BASE}/api/spectrum?${query(p)}`, onProgress, signal);
}

export function fetchLightCurve(p: SeriesRequest, detector: Detector,
                                onProgress?: (j: Job<LightCurveResponse>) => void,
                                signal?: AbortSignal): Promise<LightCurveResponse> {
  return getWithJob<LightCurveResponse>(`${API_BASE}/api/lightcurve?${query(p, { detector: String(detector) })}`,
                                        onProgress, signal);
}

export function seriesCsv(points: SeriesPoint[]): string {
  const head = 'date_iso,date_mjd,detector,wavelength_um,bandwidth_um,flux_mjy_sr,err_mjy_sr,flagged,obs_id';
  return [head, ...points.map((p) => [p.date_iso, p.date_mjd, p.detector, p.wavelength_um ?? '', p.bandwidth_um ?? '',
                                      p.flux, p.err, p.flagged ? 1 : 0, p.obs_id].join(','))].join('\n');
}
