'use client';
// Readout block of the side column: the facts behind the frames on screen, as an instrument would list them.
// Everything comes from the /api/blink response; nothing is computed or guessed here.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';
import { useSequence } from './playback';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-slate-800 py-1.5">
      <dt className="hud-label">{label}</dt>
      <dd className="hud-value text-right text-xs">{value}</dd>
    </div>
  );
}

export function ViewerReadout() {
  const t = useTranslations('viewer.readout');
  const blink = useViewer((s) => s.blink);
  const frameIndex = useViewer((s) => s.frameIndex);
  const selected = useViewer((s) => s.selected);
  const frames = useSequence();
  if (!blink || frames.length === 0) return null;

  const frame = frames[Math.min(frameIndex, frames.length - 1)];
  // epochs of the band on screen: one "epoch"/"diff_vs_median" frame per visit; pair and sum frames repeat them
  const band = blink.frames.filter((f) => f.detector === frame.detector);
  const first = band.reduce((a, f) => (f.date_iso < a ? f.date_iso : a), band[0].date_iso);
  const last = band.reduce((a, f) => (f.date_end_iso > a ? f.date_end_iso : a), band[0].date_end_iso);
  const masked = blink.flags_summary.bad_pixel_fraction;
  const motion = band.find((f) => f.motion)?.motion;

  return (
    <div className="flex flex-col gap-2">
      <h2 className="hud-label">{t('title')}</h2>
      <dl className="border-b border-slate-800">
        <Row label={t('dates')} value={`${first} → ${last}`} />
        <Row label={t('pixel')} value={`${blink.grid.pixel_scale_arcsec}″ · ${blink.grid.width}×${blink.grid.height}`} />
        <Row label={t('masked')} value={masked != null ? `${(masked * 100).toFixed(1)}%` : t('none')} />
        {motion && (
          <>
            <Row label={t('shift')}
                 value={`${motion.shift_arcsec.toFixed(1)} ± ${motion.shift_err_arcsec.toFixed(1)}″ · PA ${Math.round(motion.pa_deg)}°`} />
            <Row label={t('predicted')}
                 value={`${motion.expected_shift_arcsec.toFixed(1)}″ · PA ${Math.round(motion.expected_pa_deg)}°`} />
            {motion.reference_shift_arcsec != null && (
              <Row label={t('registration')}
                   value={t('registrationValue', { value: motion.reference_shift_arcsec.toFixed(2), count: motion.n_reference_stars })} />
            )}
          </>
        )}
        {selected && (
          <Row label={t('picked')} value={`${selected.x}, ${selected.y} · ${selected.ra.toFixed(4)}° ${selected.dec.toFixed(4)}°`} />
        )}
      </dl>
      {motion && (
        <p className="text-xs leading-relaxed text-slate-400">
          {t('shiftNote', { from: motion.pair[0], to: motion.pair[1] })}
          {motion.core_masked && ` ${t('coreMasked')}`}
        </p>
      )}
    </div>
  );
}
