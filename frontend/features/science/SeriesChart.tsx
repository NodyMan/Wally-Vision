'use client';
// A small scatter chart with error bars (SVG, no chart library): spectrum (x = wavelength) and light curve
// (x = date). Points are NOT joined by a line: each one is a separate exposure, and neighbours may differ
// in date (spectrum) or in wavelength (light curve).
// Developed with SI assistance (Claude); reviewed by team #1.
import type { ReactNode } from 'react';

export interface ChartPoint { x: number; y: number; err: number; color: string; faded?: boolean; title: string }
export interface ChartMark { x: number; label: string }

interface Props {
  points: ChartPoint[];
  marks?: ChartMark[];
  xLabel: string;
  yLabel: string;
  formatX: (x: number) => string;
  ariaLabel: string;
  children?: ReactNode;
}

const W = 640, H = 260, L = 56, R = 12, T = 18, B = 40;

function ticks(lo: number, hi: number, n = 5): number[] {
  const span = hi - lo || 1;
  const step = Math.pow(10, Math.floor(Math.log10(span / n)));
  const nice = [1, 2, 5, 10].map((m) => m * step).find((s) => span / s <= n) ?? step * 10;
  const out: number[] = [];
  for (let v = Math.ceil(lo / nice) * nice; v <= hi + 1e-9; v += nice) out.push(Number(v.toPrecision(12)));
  return out;
}

function compact(v: number): string {
  const a = Math.abs(v);
  return a >= 1000 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : a >= 0.1 || v === 0 ? v.toFixed(2) : v.toExponential(1);
}

export function SeriesChart({ points, marks = [], xLabel, yLabel, formatX, ariaLabel }: Props) {
  if (points.length === 0) return null;
  const xs = points.map((p) => p.x);
  const xPad = (Math.max(...xs) - Math.min(...xs)) * 0.04 || 0.5;
  const x0 = Math.min(...xs) - xPad, x1 = Math.max(...xs) + xPad;
  const lo = Math.min(0, ...points.map((p) => p.y - p.err));
  const hi = Math.max(...points.map((p) => p.y + p.err));
  const yPad = (hi - lo) * 0.06 || 1;
  const y0 = lo - yPad, y1 = hi + yPad;
  const sx = (v: number) => L + ((v - x0) / (x1 - x0)) * (W - L - R);
  const sy = (v: number) => H - B - ((v - y0) / (y1 - y0)) * (H - T - B);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} className="h-auto w-full text-slate-300">
      <rect x={L} y={T} width={W - L - R} height={H - T - B} fill="rgba(255,255,255,0.03)" />
      {ticks(y0, y1).map((v) => (
        <g key={`y${v}`}>
          <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke="currentColor" strokeOpacity={v === 0 ? 0.5 : 0.12} />
          <text x={L - 6} y={sy(v) + 4} textAnchor="end" fontSize="11" fill="currentColor">{compact(v)}</text>
        </g>
      ))}
      {ticks(x0, x1, 6).map((v) => (
        <text key={`x${v}`} x={sx(v)} y={H - B + 16} textAnchor="middle" fontSize="11" fill="currentColor">{formatX(v)}</text>
      ))}
      {marks.filter((m) => m.x > x0 && m.x < x1).map((m) => (
        <g key={m.label}>
          <line x1={sx(m.x)} x2={sx(m.x)} y1={T} y2={H - B} stroke="#fbbf24" strokeDasharray="4 4" strokeOpacity="0.8" />
          <text x={sx(m.x)} y={T - 5} textAnchor="middle" fontSize="11" fill="#fbbf24">{m.label}</text>
        </g>
      ))}
      {points.map((p, i) => (
        <g key={i} opacity={p.faded ? 0.35 : 1}>
          <title>{p.title}</title>
          <line x1={sx(p.x)} x2={sx(p.x)} y1={sy(p.y - p.err)} y2={sy(p.y + p.err)} stroke={p.color} strokeWidth="1.2" />
          <circle cx={sx(p.x)} cy={sy(p.y)} r="3.2" fill={p.color} />
        </g>
      ))}
      <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" fontSize="12" fill="currentColor">{xLabel}</text>
      <text transform={`translate(13 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" fontSize="12" fill="currentColor">{yLabel}</text>
    </svg>
  );
}

/** One colour per SPHEREx band, short to long wavelength. */
export const BAND_COLORS: Record<number, string> = {
  1: '#60a5fa', 2: '#22d3ee', 3: '#34d399', 4: '#facc15', 5: '#fb923c', 6: '#f87171',
};
