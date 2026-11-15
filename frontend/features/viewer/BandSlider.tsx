'use client';
// Wavelength slider: one patch of sky, six SPHEREx bands from 0.75 µm (almost visible light) to 5.0 µm.
// Ordinary stars are brightest at short wavelengths; a cold brown dwarf like WISE 0855 is invisible there and
// appears only at the long end. Each band is a separate image with its own brightness scale (bands are never
// mixed), so the slider shows what is visible in each band, not absolute brightness ratios between bands.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';
import type { Detector } from '@/lib/api/viewer';
import { bandsOf, usePlayback } from './playback';

// SPHEREx detector ranges, µm (COMMON §0, SIA2 em_min/em_max)
const RANGE: Record<Detector, [number, number]> = {
  1: [0.75, 1.12], 2: [1.10, 1.65], 3: [1.63, 2.44], 4: [2.40, 3.85], 5: [3.81, 4.43], 6: [4.41, 5.01],
};

export function BandSlider() {
  const t = useTranslations('viewer.bands');
  const blink = useViewer((s) => s.blink);
  const detector = useViewer((s) => s.detector);
  const setFrameIndex = useViewer((s) => s.setFrameIndex);
  const band = usePlayback((s) => s.band);
  const setBand = usePlayback((s) => s.setBand);
  const bands = bandsOf(blink);
  if (detector !== 'all' || bands.length < 2) return null;

  const current = band && bands.includes(band) ? band : bands[0];
  const i = bands.indexOf(current);
  const [lo, hi] = RANGE[current];
  const pick = (k: number) => {
    setBand(bands[Math.max(0, Math.min(bands.length - 1, k))]);
    setFrameIndex(0);
  };

  return (
    <div className="flex flex-col gap-2 border border-slate-800 bg-slate-950 p-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="hud-label">{t('label')}</span>
        <span className="hud-value text-lg font-light">
          D{current} · {lo.toFixed(2)}–{hi.toFixed(2)} µm
        </span>
      </div>
      <input type="range" min={0} max={bands.length - 1} step={1} value={i}
             onChange={(e) => pick(Number(e.target.value))}
             aria-label={t('label')} aria-valuetext={`D${current}, ${lo.toFixed(2)}–${hi.toFixed(2)} µm`}
             className="w-full accent-sky-400" />
      <div className="flex justify-between">
        {bands.map((b) => (
          <button key={b} type="button" onClick={() => pick(bands.indexOf(b))} aria-pressed={b === current}
                  className={`hud-label px-1 ${b === current ? 'text-sky-400!' : 'hover:text-white!'}`}>
            {RANGE[b][0].toFixed(1)}
          </button>
        ))}
      </div>
      <p className="text-xs leading-relaxed text-slate-400">{t('note')}</p>
    </div>
  );
}

/** Button for the side column: open the same field as a deep sum in every band. */
export function AllBandsButton() {
  const t = useTranslations('viewer.bands');
  const detector = useViewer((s) => s.detector);
  const mode = useViewer((s) => s.mode);
  const setMode = useViewer((s) => s.setMode);
  const setDetector = useViewer((s) => s.setDetector);
  if (detector === 'all' && mode === 'sum') return null;
  return (
    <button type="button" onClick={() => { setMode('sum'); setDetector('all'); }}
            className="w-full border border-slate-700 bg-slate-950 px-3 py-2 text-left text-sm text-slate-100 transition-colors hover:border-sky-400">
      <span className="block">{t('open')}</span>
      <span className="hud-label block normal-case! tracking-normal!">{t('openHint')}</span>
    </button>
  );
}
