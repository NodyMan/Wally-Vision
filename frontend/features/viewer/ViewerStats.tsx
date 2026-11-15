'use client';
// The row of stat tiles above the image (dashboard style): big number, small label, segmented bar.
// Every bar means something: visits = one segment per visit, exposures = exposures per visit,
// shift = measured vs catalogue prediction, wavelength = position inside SPHEREx's 0.75–5.0 µm range.
// All values come from the /api/blink response.
// Developed with SI assistance (Claude); reviewed by team #1.
import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { CalendarDays, Images, MoveUpRight, Waves } from 'lucide-react';
import { useViewer } from '@/lib/store';
import { useSequence } from './playback';

const SEGMENTS = 12;
const LAMBDA_MIN = 0.75;
const LAMBDA_MAX = 5.0;

function Bar({ fill }: { fill: number }) {
  const on = Math.round(Math.max(0, Math.min(1, fill)) * SEGMENTS);
  return (
    <div className="flex gap-1" aria-hidden="true">
      {Array.from({ length: SEGMENTS }, (_, i) => (
        <span key={i} className={`h-1.5 flex-1 rounded-full ${i < on ? 'bg-sky-500' : 'bg-slate-800'}`} />
      ))}
    </div>
  );
}

function Tile({ icon, label, value, unit, sub, fill }: {
  icon: ReactNode; label: string; value: string; unit?: string; sub: string; fill: number;
}) {
  return (
    <div className="card flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="flex items-center gap-2 text-sm text-slate-300">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-950 text-sky-600">{icon}</span>
          {label}
        </span>
        <span className="text-right">
          <span className="hud-value text-3xl font-light leading-none">{value}</span>
          {unit && <span className="ml-0.5 text-sm text-slate-400">{unit}</span>}
        </span>
      </div>
      <Bar fill={fill} />
      <span className="hud-label truncate">{sub}</span>
    </div>
  );
}

export function ViewerStats() {
  const t = useTranslations('viewer.stats');
  const blink = useViewer((s) => s.blink);
  const frameIndex = useViewer((s) => s.frameIndex);
  const frames = useSequence();
  if (!blink || frames.length === 0) return null;

  const frame = frames[Math.min(frameIndex, frames.length - 1)];
  const band = blink.frames.filter((f) => f.detector === frame.detector);
  const visits = new Map(band.filter((f) => f.kind !== 'sum' && f.kind !== 'diff_pair').map((f) => [f.date_iso, f.n_images]));
  const nVisits = visits.size || 1;
  const exposures = frame.kind === 'sum' ? frame.n_images : [...visits.values()].reduce((a, b) => a + b, 0);
  const perVisit = exposures / nVisits;
  const motion = band.find((f) => f.motion)?.motion;
  const wl = frame.target_wavelength_um;
  const [lo, hi] = frame.wavelength_range_um;

  return (
    <section aria-label={t('label')} className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile icon={<CalendarDays className="h-4 w-4" />} label={t('visits')} value={String(nVisits)}
            sub={`${band[0].date_iso.slice(0, 7)} → ${band[band.length - 1].date_end_iso.slice(0, 7)}`}
            fill={nVisits / Math.max(nVisits, 4)} />
      <Tile icon={<Images className="h-4 w-4" />} label={t('exposures')} value={String(exposures)}
            sub={t('perVisit', { value: perVisit.toFixed(1) })} fill={Math.min(1, perVisit / 8)} />
      {motion ? (
        <Tile icon={<MoveUpRight className="h-4 w-4" />} label={t('shift')} value={motion.shift_arcsec.toFixed(1)} unit="″"
              sub={t('shiftSub', { err: motion.shift_err_arcsec.toFixed(1), expected: motion.expected_shift_arcsec.toFixed(1) })}
              fill={motion.expected_shift_arcsec > 0 ? motion.shift_arcsec / motion.expected_shift_arcsec / 1.5 : 0} />
      ) : (
        <Tile icon={<MoveUpRight className="h-4 w-4" />} label={t('shift')} value="—" sub={t('notMeasured')} fill={0} />
      )}
      <Tile icon={<Waves className="h-4 w-4" />} label={t('wavelength')} value={wl != null ? wl.toFixed(2) : '—'} unit={wl != null ? 'µm' : undefined}
            sub={`D${frame.detector} · ${lo.toFixed(2)}–${hi.toFixed(2)} µm`}
            fill={wl != null ? (wl - LAMBDA_MIN) / (LAMBDA_MAX - LAMBDA_MIN) : 0} />
    </section>
  );
}
