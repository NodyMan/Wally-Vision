// API участника #1: /api/blink (асинхронно: 200 из кэша или 202 → опрос статуса), /api/frame/<id>.png.
// Типы строго по 00_COMMON.md §6. Developed with SI assistance (Claude); reviewed by team #1.

export type Detector = 1 | 2 | 3 | 4 | 5 | 6;
export type DetectorParam = Detector | 'all';
export type BlinkMode = 'frames' | 'diff' | 'sum';
export type FrameKind = 'epoch' | 'diff_vs_median' | 'diff_pair' | 'sum';

export interface BlinkFrame {
  id: string;
  url: string;                                   // /api/frame/<id>.png (в моках — /mock/frames/<id>.png)
  kind: FrameKind;
  detector: Detector;
  date_iso: string;
  date_end_iso: string;
  date_mjd: number;
  n_images: number;
  wavelength_range_um: [number, number];         // справочная полоса детектора
  target_wavelength_um: number | null;           // LVF: длина волны в точке цели (медиана по эпохе)
  target_wavelength_span_um: [number, number] | null;
  target_bandwidth_um: number | null;
  target_xy: [number, number] | null;            // где цель должна быть в эту эпоху (canvas px, 0-based) — кольцо
  target_xy_from?: [number, number] | null;      // только diff_pair: где цель была в ранней эпохе
  pair?: [string, string];                       // только diff_pair: даты пары
  motion?: MeasuredMotion;                       // measured target shift between the first and last full visit
}

/** Centroid measurement of the target (backend/core/motion.py). Positions are canvas pixels. */
export interface MeasuredMotion {
  pair: [string, string];
  from_xy: [number, number];
  to_xy: [number, number];
  shift_arcsec: number;
  shift_err_arcsec: number;            // statistical and registration errors combined
  stat_err_arcsec: number;
  pa_deg: number;                      // position angle, degrees east of north
  expected_shift_arcsec: number;       // from the catalogue proper motion over the same dates
  expected_pa_deg: number;
  years: number;
  snr: [number, number] | null;       // null when measured on the masked core
  core_masked: boolean;                // saturated core
  centroid_on: 'light' | 'masked_core';
  reference_shift_arcsec: number | null;   // apparent shift of bright field stars = registration error
  n_reference_stars: number;
  method: string;
}

export interface BlinkWarning {
  code: 'few_epochs' | 'wavelength_mismatch' | 'wavelength_unknown' | 'partial_download' | string;
  severity: 'info' | 'warning';
  detector?: Detector;
  [k: string]: unknown;
}

export interface BlinkGrid {
  id: string;
  width: number;
  height: number;
  pixel_scale_arcsec: number;
  pixel_origin: string;
  wcs_header: Record<string, string | number | boolean>;
}

export interface BlinkResponse {
  target: {
    ra: number; dec: number; name: string | null;
    coordinate_epoch: number | null;              // эпоха центра (поправка за собственное движение)
    catalog_ra: number | null; catalog_dec: number | null;
    pm_mas_yr: [number, number] | null;
  };
  fov_arcsec: number;
  mode: BlinkMode;
  grid: BlinkGrid;
  frames: BlinkFrame[];                          // отсортированы по detector, затем по времени
  warnings: BlinkWarning[];
  flags_summary: { bad_pixel_fraction: number | null; policy: string };
}

export type JobStatus = 'queued' | 'running' | 'done' | 'error';

export interface BlinkJob {
  job_id: string;
  status: JobStatus;
  progress: number;                              // 0..1
  stage?: string;                                // search | download:24 | stack | done → i18n viewer.stage.*
  result?: BlinkResponse;
  error_code?: string;                           // перевод: errors.<code> (#3)
}

export interface BlinkParams {
  ra: number;
  dec: number;
  fov?: number;
  detector?: DetectorParam;
  mode?: BlinkMode;
  name?: string;
}

import { API_BASE_URL } from './platform';

const API = API_BASE_URL;   // one base URL for the whole app (default http://localhost:8000)
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === '1';

export class ApiError extends Error {
  constructor(public code: string, public status?: number) {
    super(code);
  }
}

function qs(p: BlinkParams): string {
  const s = new URLSearchParams({
    ra: String(p.ra), dec: String(p.dec),
    fov: String(p.fov ?? 300), detector: String(p.detector ?? 6), mode: p.mode ?? 'frames',
  });
  if (p.name) s.set('name', p.name);
  return s.toString();
}

/** Абсолютный URL кадра (бэкенд на другом домене, моки — из /public). */
export function frameSrc(frame: BlinkFrame): string {
  return frame.url.startsWith('/api/') ? `${API}${frame.url}` : frame.url;
}

async function mockBlink(p: BlinkParams): Promise<BlinkResponse> {
  const data = p.mode === 'diff'
    ? (await import('../mocks/blink_diff.json')).default
    : (await import('../mocks/blink_frames.json')).default;
  return data as unknown as BlinkResponse;
}

/** A background job as reported by /api/blink/status/<job_id> (blink, spectrum and light curve share it). */
export interface Job<T> {
  job_id: string;
  status: JobStatus;
  progress: number;
  stage?: string;
  result?: T;
  error_code?: string;
}

export const API_BASE = API;

/**
 * GET an endpoint that answers 200 with the result or 202 with a job; in the second case poll the job
 * every 1.5 s, calling onProgress. Cancel with an AbortSignal (the target changed while loading).
 * A cold request took over 6 minutes when IRSA was busy (measured 14.11), so there is no short fixed limit:
 * give up only if the job has not advanced for STALL_MS, or after HARD_MS in total.
 */
export async function getWithJob<T>(
  url: string,
  onProgress?: (job: Job<T>) => void,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(url, { signal });
  if (res.status === 200) return (await res.json()) as T;
  if (res.status !== 202) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError((body as { error_code?: string }).error_code ?? 'server_error', res.status);
  }
  let job = (await res.json()) as Job<T>;
  onProgress?.(job);
  const STALL_MS = 4 * 60_000;
  const HARD_MS = 15 * 60_000;
  const started = Date.now();
  let lastProgress = job.progress;
  let lastAdvance = started;
  while (job.status === 'queued' || job.status === 'running') {
    if (job.progress > lastProgress || job.status === 'queued') {
      lastProgress = job.progress;
      lastAdvance = Date.now();
    }
    if (Date.now() - lastAdvance > STALL_MS || Date.now() - started > HARD_MS) throw new ApiError('irsa_timeout');
    await new Promise((r) => setTimeout(r, 1500));
    if (signal?.aborted) throw new ApiError('aborted');
    const r = await fetch(`${API}/api/blink/status/${job.job_id}`, { signal });
    if (!r.ok) throw new ApiError('server_error', r.status);
    job = (await r.json()) as Job<T>;
    onProgress?.(job);
  }
  if (job.status === 'error' || !job.result) throw new ApiError(job.error_code ?? 'server_error');
  return job.result;
}

/** Requests a blink: 200 from the cache, or 202 and polling (see getWithJob). */
export async function fetchBlink(
  p: BlinkParams,
  onProgress?: (job: BlinkJob) => void,
  signal?: AbortSignal,
): Promise<BlinkResponse> {
  if (USE_MOCKS) return mockBlink(p);
  return getWithJob<BlinkResponse>(`${API}/api/blink?${qs(p)}`, onProgress, signal);
}

/** Кадры одной последовательности (один детектор). Разные детекторы НИКОГДА не проигрываются вместе. */
export function framesFor(resp: BlinkResponse | null, detector: Detector, kinds?: FrameKind[]): BlinkFrame[] {
  if (!resp) return [];
  return resp.frames.filter((f) => f.detector === detector && (!kinds || kinds.includes(f.kind)));
}
