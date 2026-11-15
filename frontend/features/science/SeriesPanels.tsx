'use client';
// "Spectrum" and "Light curve" tabs (plan #2). Both measure real SPHEREx exposures at one sky position:
// the clicked pixel, or the target when nothing is clicked. A cold request downloads images from NASA and
// can take minutes, so nothing starts until the button is pressed, and progress is shown.
// Results are a PREVIEW (simple box photometry), and the panels say so.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  fetchLightCurve, fetchSpectrum, seriesCsv,
  type LightCurveResponse, type SeriesPoint, type SeriesRequest, type SpectrumResponse,
} from '@/lib/api/science';
import { ApiError, type Detector, type Job } from '@/lib/api/viewer';
import { useViewer } from '@/lib/store';
import { useSequence } from '@/features/viewer/playback';
import { BAND_COLORS, SeriesChart, type ChartPoint } from './SeriesChart';

const BTN = 'inline-flex h-9 items-center rounded-lg px-3 text-sm border border-slate-700 hover:border-sky-500/60 hover:text-white disabled:opacity-40';

interface Place extends SeriesRequest { picked: boolean }

/** Where to measure: the clicked pixel if there is one, otherwise the target at the centre of the field. */
function usePlace(): Place | null {
  const blink = useViewer((s) => s.blink);
  const target = useViewer((s) => s.target);
  const selected = useViewer((s) => s.selected);
  if (!blink || !target) return null;
  const at = selected ?? blink.target;
  return { ra: at.ra, dec: at.dec, cra: target.ra, cdec: target.dec, fov: blink.fov_arcsec, picked: !!selected };
}

type Run<T> = { state: 'idle' } | { state: 'loading'; progress: number; stage?: string }
  | { state: 'done'; data: T } | { state: 'error'; code: string };

/** Runs one request at a time; a result belongs to the place it was measured at and is hidden once the place changes. */
function useRun<T>(key: string) {
  const [held, setHeld] = useState<{ key: string; run: Run<T> }>({ key, run: { state: 'idle' } });
  const run: Run<T> = held.key === key ? held.run : { state: 'idle' };
  const setRun = (next: Run<T>) => setHeld({ key, run: next });
  const ctrl = useRef<AbortController | null>(null);
  useEffect(() => () => ctrl.current?.abort(), [key]);   // leaving this place cancels its request
  const start = (fn: (onProgress: (j: Job<T>) => void, signal: AbortSignal) => Promise<T>) => {
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setRun({ state: 'loading', progress: 0, stage: 'search' });
    fn((j) => { if (!c.signal.aborted) setRun({ state: 'loading', progress: j.progress, stage: j.stage }); }, c.signal)
      .then((data) => { if (!c.signal.aborted) setRun({ state: 'done', data }); })
      .catch((e: unknown) => {
        if (!c.signal.aborted) setRun({ state: 'error', code: e instanceof ApiError ? e.code : 'server_error' });
      });
  };
  return { run, start };
}

function Status<T>({ run }: { run: Run<T> }) {
  const t = useTranslations();
  if (run.state === 'loading') {
    const [name, count] = (run.stage ?? 'queued').split(':');
    const stage = ['queued', 'search', 'download', 'stack', 'done'].includes(name) ? name : 'queued';
    const percent = Math.round(run.progress * 100);
    return (
      <div className="max-w-sm">
        <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}
             aria-label={t('viewer.progress.label')} className="h-2 overflow-hidden rounded-full bg-slate-800">
          <div className="h-full rounded-full bg-sky-400" style={{ width: `${Math.max(percent, 3)}%` }} />
        </div>
        <p aria-live="polite" className="mt-2 text-sm">{t(`viewer.stage.${stage}`, { count: Number(count) || 0 })} · {percent}%</p>
      </div>
    );
  }
  if (run.state === 'error') {
    return <p role="alert" className="text-sm text-red-700">{t.has(`errors.${run.code}`) ? t(`errors.${run.code}`) : t('errors.server_error')}</p>;
  }
  return null;
}

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function PlaceLine({ place }: { place: Place }) {
  const t = useTranslations('science');
  return (
    <p className="text-xs opacity-80">
      {place.picked ? t('place.picked') : t('place.target')}{' '}
      <span className="tabular-nums">RA {place.ra.toFixed(5)}°, Dec {place.dec.toFixed(5)}°</span>
      {!place.picked && <span className="opacity-70"> · {t('place.hint')}</span>}
    </p>
  );
}

function title(p: SeriesPoint): string {
  return `${p.date_iso} · D${p.detector}${p.wavelength_um != null ? ` · ${p.wavelength_um.toFixed(3)} µm` : ''} · ${p.flux} ± ${p.err} MJy/sr`;
}

export function SpectrumPanel() {
  const t = useTranslations('science');
  const place = usePlace();
  const { run, start } = useRun<SpectrumResponse>(place ? `${place.ra}|${place.dec}|${place.cra}|${place.cdec}|${place.fov}` : '');
  if (!place) return <p className="text-sm opacity-70">{t('needTarget')}</p>;

  const data = run.state === 'done' ? run.data : null;
  const points: ChartPoint[] = (data?.points ?? []).filter((p) => p.wavelength_um != null).map((p) => ({
    x: p.wavelength_um as number, y: p.flux, err: p.err, color: BAND_COLORS[p.detector], faded: p.flagged, title: title(p),
  }));

  return (
    <div className="flex flex-col gap-3">
      <PlaceLine place={place} />
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={BTN} disabled={run.state === 'loading'}
                onClick={() => start((onProgress, signal) => fetchSpectrum(place, onProgress, signal))}>
          {t('spectrum.build')}
        </button>
        {data && (
          <button type="button" className={BTN}
                  onClick={() => download(`skyblink_spectrum_${place.ra.toFixed(5)}_${place.dec.toFixed(5)}.csv`, seriesCsv(data.points))}>
            {t('csv')}
          </button>
        )}
        {run.state === 'idle' && <span className="text-xs opacity-70">{t('spectrum.slow')}</span>}
      </div>
      <Status run={run} />
      {data && (
        <>
          <SeriesChart points={points} xLabel={t('spectrum.x')} yLabel={t('yLabel')} ariaLabel={t('spectrum.aria', { count: points.length })}
                       formatX={(v) => v.toFixed(1)}
                       marks={data.features.map((f) => ({ x: f.wavelength_um, label: t(`features.${f.key}.short`) }))} />
          <ul className="grid gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
            {data.features.map((f) => (
              <li key={f.key}><span className="text-amber-700">{t(`features.${f.key}.short`)} · {f.wavelength_um} µm</span> — {t(`features.${f.key}.text`)}</li>
            ))}
          </ul>
          <p className="text-xs text-amber-700">{t('spectrum.preview', { count: points.length })}</p>
        </>
      )}
    </div>
  );
}

export function LightCurvePanel() {
  const t = useTranslations('science');
  const place = usePlace();
  const frames = useSequence();
  const detector = frames[0]?.detector as Detector | undefined;
  const { run, start } = useRun<LightCurveResponse>(place ? `${place.ra}|${place.dec}|${place.cra}|${place.cdec}|${place.fov}|${detector}` : '');
  if (!place || !detector) return <p className="text-sm opacity-70">{t('needTarget')}</p>;

  const data = run.state === 'done' ? run.data : null;
  const points: ChartPoint[] = (data?.points ?? []).map((p) => ({
    x: p.date_mjd, y: p.flux, err: p.err, color: BAND_COLORS[p.detector], faded: p.flagged, title: title(p),
  }));
  // MJD → calendar date for the axis (MJD 40587 = 1970-01-01)
  const dateOf = (mjd: number) => new Date((mjd - 40587) * 86400000).toISOString().slice(0, 7);
  const span = data?.wavelength_span_um;

  return (
    <div className="flex flex-col gap-3">
      <PlaceLine place={place} />
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={BTN} disabled={run.state === 'loading'}
                onClick={() => start((onProgress, signal) => fetchLightCurve(place, detector, onProgress, signal))}>
          {t('lightcurve.build', { band: detector })}
        </button>
        {data && (
          <button type="button" className={BTN}
                  onClick={() => download(`skyblink_lightcurve_d${detector}_${place.ra.toFixed(5)}_${place.dec.toFixed(5)}.csv`, seriesCsv(data.points))}>
            {t('csv')}
          </button>
        )}
      </div>
      <Status run={run} />
      {data && (
        <>
          <SeriesChart points={points} xLabel={t('lightcurve.x')} yLabel={t('yLabel')} formatX={dateOf}
                       ariaLabel={t('lightcurve.aria', { count: points.length })} />
          <p className="text-xs text-amber-700">
            {span ? t('lightcurve.preview', { from: span[0].toFixed(2), to: span[1].toFixed(2) }) : t('lightcurve.previewNoWl')}
          </p>
          {data.points.some((p) => p.flagged) && <p className="text-xs opacity-80">{t('flagged')}</p>}
        </>
      )}
    </div>
  );
}
