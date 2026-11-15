'use client';
// Plain-language notes under the player: what the rings mean, how to read a difference image,
// and warnings from the API (for example, epochs taken at different wavelengths).
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';
import { usePlayback, useSequence } from './playback';

export function ViewerNotes() {
  const t = useTranslations('viewer');
  const blink = useViewer((s) => s.blink);
  const frameIndex = useViewer((s) => s.frameIndex);
  const rings = usePlayback((s) => s.rings);
  const frames = useSequence();
  if (!blink) return null;

  const frame = frames[Math.min(frameIndex, frames.length - 1)];
  const shown = frames[0]?.detector;
  // a warning about another band says nothing about the frames on screen
  const codes = Array.from(new Set(blink.warnings
    .filter((w) => w.detector === undefined || w.detector === shown)
    .map((w) => w.code)));
  const hasAfter = rings && frames.some((f) => f.target_xy);
  const hasBefore = rings && frames.some((f) => f.target_xy_from);

  return (
    <div className="flex flex-col gap-1.5 px-1 text-xs">
      {(hasAfter || hasBefore) && (
        <p className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {hasBefore && (
            <span className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="h-3 w-3 rounded-full border-2 border-dashed border-slate-100" />
              {t('rings.before')}
            </span>
          )}
          {hasAfter && (
            <span className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="h-3 w-3 rounded-full border-2 border-sky-400" />
              {frame?.target_xy_from ? t('rings.after') : t('rings.expected')}
            </span>
          )}
        </p>
      )}
      {blink.mode === 'diff' && <p className="opacity-80">{t('mode.diffLegend')}</p>}
      {codes.map((code) => (
        <p key={code} className="text-amber-200">
          {t.has(`warnings.${code}`) ? t(`warnings.${code}`) : code}
        </p>
      ))}
      <p className="hud-label hidden normal-case! tracking-normal! md:block">{t('controls.hint')}</p>
    </div>
  );
}
