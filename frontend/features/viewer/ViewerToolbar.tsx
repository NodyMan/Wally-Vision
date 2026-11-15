'use client';
// #1's part of the toolbar: mode (blink / difference / deep sum), wavelength band, field of view.
// Band and field of view are hidden in Simple mode.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import type { BlinkMode, DetectorParam } from '@/lib/api/viewer';
import { useViewer } from '@/lib/store';
import { AllBandsButton } from './BandSlider';

const MODES: BlinkMode[] = ['frames', 'diff', 'sum'];
const DETECTORS: DetectorParam[] = ['all', 1, 2, 3, 4, 5, 6];
export const FOVS_ARCSEC = [120, 300, 900, 1800];   // 2′, 5′, 15′, 30′

const SELECT = 'h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 text-sm text-slate-100';
const FIELD = 'flex w-full flex-col gap-1 text-xs text-slate-400';

export function ViewerToolbar() {
  const t = useTranslations('viewer');
  const { mode, detector, fov, simpleMode, setMode, setDetector, setFov } = useViewer();
  const fovs = FOVS_ARCSEC.includes(fov) ? FOVS_ARCSEC : [...FOVS_ARCSEC, fov].sort((a, b) => a - b);

  return (
    <>
      <div role="group" aria-label={t('mode.label')} className="flex w-full overflow-hidden rounded-lg border border-slate-700">
        {MODES.map((m) => (
          <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}
                  className={`min-h-9 flex-1 px-2 py-1 text-sm leading-tight transition-colors ${mode === m ? 'bg-sky-500 font-semibold text-slate-950' : 'text-slate-200 hover:bg-slate-800'}`}>
            {t(`mode.${m}`)}
          </button>
        ))}
      </div>

      <AllBandsButton />

      {!simpleMode && (
        <>
          <label className={FIELD}>
            <span>{t('detector.label')}</span>
            <select className={SELECT} value={String(detector)}
                    onChange={(e) => setDetector(e.target.value === 'all' ? 'all' : (Number(e.target.value) as DetectorParam))}>
              {DETECTORS.map((d) => (
                <option key={d} value={String(d)}>{d === 'all' ? t('detector.all') : `D${d} · ${t(`detector.d${d}`)}`}</option>
              ))}
            </select>
          </label>

          <label className={FIELD} title={t('fov.hint')}>
            <span>{t('fov.label')}</span>
            <select className={SELECT} value={fov} onChange={(e) => setFov(Number(e.target.value))}>
              {fovs.map((f) => (
                <option key={f} value={f}>{t('fov.arcmin', { value: Math.round((f / 60) * 10) / 10 })}</option>
              ))}
            </select>
          </label>
        </>
      )}
    </>
  );
}
