'use client';
// Buttons under the canvas: previous / play / next, frame slider, speed, zoom, rings, diff view, band.
// In Simple mode only play and the slider stay (plan #1, H14–H20).
// Developed with SI assistance (Claude); reviewed by team #1.
import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';
import { BandSlider } from './BandSlider';
import { ZOOM_MAX, ZOOM_MIN } from './geometry';
import { bandsOf, SPEEDS_FPS, usePlayback, useSequence, type DiffView } from './playback';

const BTN = 'inline-flex h-9 min-w-9 items-center justify-center rounded-lg px-2 text-sm border border-slate-700 '
  + 'hover:border-sky-500/60 hover:text-white disabled:opacity-40 disabled:hover:bg-transparent';
const ON = 'border-sky-500/70 bg-sky-500/15 text-sky-600';

function Icon({ d }: { d: string }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current"><path d={d} /></svg>;
}
const PLAY = 'M8 5v14l11-7z';
const PAUSE = 'M6 5h4v14H6zM14 5h4v14h-4z';
const PREV = 'M6 6h2v12H6zM20 6v12L9.5 12z';
const NEXT = 'M16 6h2v12h-2zM4 6l10.5 6L4 18z';

function Group({ label, children }: { label: string; children: ReactNode }) {
  return <div role="group" aria-label={label} className="flex items-center gap-1">{children}</div>;
}

export function PlayerControls() {
  const t = useTranslations('viewer');
  const blink = useViewer((s) => s.blink);
  const detector = useViewer((s) => s.detector);
  const frameIndex = useViewer((s) => s.frameIndex);
  const zoom = useViewer((s) => s.zoom);
  const simpleMode = useViewer((s) => s.simpleMode);
  const setFrameIndex = useViewer((s) => s.setFrameIndex);
  const { playing, fps, rings, diffView, setPlaying, setFps, setRings, setDiffView } = usePlayback();
  const frames = useSequence();

  if (!blink) return null;
  const count = frames.length;
  const index = Math.min(frameIndex, Math.max(0, count - 1));
  const many = count > 1;
  const go = (i: number) => {
    setPlaying(false);
    setFrameIndex(((i % count) + count) % count);
  };
  const setZoom = (z: number) => {
    const s = useViewer.getState();
    s.setZoom(z);
    if (z <= ZOOM_MIN) s.setPan({ x: 0, y: 0 });
  };
  const pickDiffView = (v: DiffView) => {
    setDiffView(v);
    setFrameIndex(0);
  };
  const bands = bandsOf(blink);
  const hasRings = frames.some((f) => f.target_xy);

  return (
    <div className="flex flex-col gap-2 border border-slate-800 bg-slate-900/70 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Group label={t('controls.playback')}>
          {!simpleMode && (
            <button type="button" className={BTN} disabled={!many} aria-label={t('controls.prev')}
                    title={t('controls.prev')} onClick={() => go(index - 1)}><Icon d={PREV} /></button>
          )}
          <button type="button" className={`${BTN} px-3`} disabled={!many} aria-pressed={playing}
                  aria-label={playing ? t('controls.pause') : t('controls.play')}
                  title={playing ? t('controls.pause') : t('controls.play')}
                  onClick={() => setPlaying(!playing)}><Icon d={playing ? PAUSE : PLAY} /></button>
          {!simpleMode && (
            <button type="button" className={BTN} disabled={!many} aria-label={t('controls.next')}
                    title={t('controls.next')} onClick={() => go(index + 1)}><Icon d={NEXT} /></button>
          )}
        </Group>

        <label className="flex min-w-32 flex-1 items-center gap-2 text-xs">
          <span className="sr-only">{t('controls.frame')}</span>
          <input type="range" min={0} max={Math.max(0, count - 1)} step={1} value={index} disabled={!many}
                 onChange={(e) => go(Number(e.target.value))} className="w-full accent-sky-400"
                 aria-valuetext={frames[index] ? `${frames[index].date_iso} (${index + 1} / ${count})` : undefined} />
          <span className="whitespace-nowrap tabular-nums opacity-70">{count ? index + 1 : 0} / {count}</span>
        </label>

        {!simpleMode && (
          <>
            <label className="flex items-center gap-1 text-xs">
              <span>{t('controls.speed')}</span>
              <select value={fps} onChange={(e) => setFps(Number(e.target.value))}
                      className="h-9 rounded-lg bg-slate-800 px-2 text-sm border border-slate-700">
                {SPEEDS_FPS.map((v) => <option key={v} value={v}>{t('controls.fps', { fps: v })}</option>)}
              </select>
            </label>

            <Group label={t('controls.zoom')}>
              <button type="button" className={BTN} disabled={zoom <= ZOOM_MIN} aria-label={t('controls.zoomOut')}
                      title={t('controls.zoomOut')} onClick={() => setZoom(zoom / 1.5)}>−</button>
              <button type="button" className={`${BTN} tabular-nums`} disabled={zoom <= ZOOM_MIN}
                      aria-label={t('controls.zoomReset')} title={t('controls.zoomReset')}
                      onClick={() => setZoom(ZOOM_MIN)}>{zoom.toFixed(1)}×</button>
              <button type="button" className={BTN} disabled={zoom >= ZOOM_MAX} aria-label={t('controls.zoomIn')}
                      title={t('controls.zoomIn')} onClick={() => setZoom(zoom * 1.5)}>+</button>
            </Group>

            {hasRings && (
              <button type="button" className={`${BTN} ${rings ? ON : ''}`} aria-pressed={rings}
                      onClick={() => setRings(!rings)}>{t('controls.rings')}</button>
            )}
          </>
        )}
      </div>

      {detector === 'all' && bands.length > 1 && <BandSlider />}

      {blink.mode === 'diff' && (
        <div className="flex flex-wrap items-center gap-2">
          {blink.mode === 'diff' && (
            <Group label={t('diffView.label')}>
              {(['pair', 'epochs'] as const).map((v) => (
                <button key={v} type="button" className={`${BTN} px-3 ${diffView === v ? ON : ''}`}
                        aria-pressed={diffView === v} onClick={() => pickDiffView(v)}>{t(`diffView.${v}`)}</button>
              ))}
            </Group>
          )}
        </div>
      )}
    </div>
  );
}
