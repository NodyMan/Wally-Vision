// The /view link: ?ra=&dec=&name=&fov=&mode=&det=&t=  ↔  viewer state. Invalid values fall back to defaults.
// The page URL says `det`; the API call says `detector` (COMMON §6).
// Developed with SI assistance (Claude); reviewed by team #1.
import type { BlinkMode, DetectorParam } from '@/lib/api/viewer';
import type { Target } from '@/lib/store';

const FOV_MAX = 1800;
const MODES: BlinkMode[] = ['frames', 'diff', 'sum'];

interface UrlView { target: Target | null; fov: number; mode: BlinkMode; detector: DetectorParam; t: number | null }

function finite(raw: string | null): number | null {
  if (raw === null || raw.trim() === '') return null;
  const v = Number(raw);
  return Number.isFinite(v) ? v : null;
}

export function parseView(q: URLSearchParams): UrlView {
  const ra = finite(q.get('ra'));
  const dec = finite(q.get('dec'));
  const ok = ra !== null && dec !== null && ra >= 0 && ra < 360 && dec >= -90 && dec <= 90;
  const name = q.get('name')?.trim().slice(0, 80) || undefined;
  const fov = finite(q.get('fov'));
  const mode = MODES.find((m) => m === q.get('mode')) ?? 'frames';
  const det = q.get('det');
  let detector: DetectorParam = det === 'all' ? 'all' : (['1', '2', '3', '4', '5', '6'].includes(det ?? '') ? (Number(det) as DetectorParam) : 6);
  if (mode === 'diff' && detector === 'all') detector = 6;   // bands are never mixed in a difference
  const t = finite(q.get('t'));
  return {
    target: ok ? { ra: ra as number, dec: dec as number, name } : null,
    fov: fov !== null && fov > 0 && fov <= FOV_MAX ? fov : 300,
    mode, detector,
    t: t !== null && t >= 0 ? Math.floor(t) : null,
  };
}

export function buildQuery(v: { target: Target; fov: number; mode: BlinkMode; detector: DetectorParam; t: number | null }): string {
  const q = new URLSearchParams({ ra: String(v.target.ra), dec: String(v.target.dec) });
  if (v.target.name) q.set('name', v.target.name);
  q.set('fov', String(v.fov));
  q.set('mode', v.mode);
  q.set('det', String(v.detector));
  if (v.t !== null) q.set('t', String(v.t));
  return q.toString();
}
