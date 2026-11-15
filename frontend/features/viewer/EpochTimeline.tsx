'use client';
// Time reference strip under the player: every SPHEREx visit of this band on one date axis.
// Bar height = number of exposures in the visit; the visit(s) on screen are highlighted.
// Clicking a visit jumps to its frame. All values come from the /api/blink response.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';
import { usePlayback, useSequence } from './playback';

interface Visit { date: string; mjd: number; n: number }

function Big({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="hud-label">{label}</span>
      <span className="hud-value text-3xl font-light leading-none sm:text-4xl">{value}</span>
    </div>
  );
}

export function EpochTimeline() {
  const t = useTranslations('viewer.timeline');
  const blink = useViewer((s) => s.blink);
  const frameIndex = useViewer((s) => s.frameIndex);
  const setFrameIndex = useViewer((s) => s.setFrameIndex);
  const setPlaying = usePlayback((s) => s.setPlaying);
  const frames = useSequence();
  if (!blink || frames.length === 0) return null;

  const frame = frames[Math.min(frameIndex, frames.length - 1)];
  const seen = new Map<string, Visit>();
  for (const f of blink.frames) {
    if (f.detector !== frame.detector || f.kind === 'sum' || f.kind === 'diff_pair') continue;
    seen.set(f.date_iso, { date: f.date_iso, mjd: f.date_mjd, n: f.n_images });
  }
  const visits = [...seen.values()].sort((a, b) => a.mjd - b.mjd);
  if (visits.length === 0) return null;

  const t0 = visits[0].mjd;
  const span = Math.max(visits[visits.length - 1].mjd - t0, 1);
  const maxN = Math.max(...visits.map((v) => v.n));
  const active = frame.kind === 'sum' ? visits.map((v) => v.date)
    : frame.kind === 'diff_pair' && frame.pair ? frame.pair : [frame.date_iso];
  const exposures = visits.reduce((a, v) => a + v.n, 0);
  const jump = (date: string) => {
    const i = frames.findIndex((f) => f.kind !== 'diff_pair' && f.date_iso === date);
    if (i < 0) return;
    setPlaying(false);
    setFrameIndex(i);
  };
  const labelled = (i: number, v: Visit) => i === 0 || i === visits.length - 1 || active.includes(v.date);

  return (
    <section aria-label={t('label')} className="flex flex-wrap items-end gap-x-8 gap-y-4 border-t border-slate-800 pt-4">
      <Big label={t('visits')} value={String(visits.length).padStart(2, '0')} />
      <Big label={t('exposures')} value={String(exposures).padStart(3, '0')} />

      <div className="min-w-56 flex-1">
        <span className="hud-label">{t('label')}</span>
        {/* 6% side margins keep the first and last date labels inside the strip */}
        <div className="relative mt-1 h-20 border border-slate-800 bg-[linear-gradient(to_right,var(--color-slate-800)_1px,transparent_1px)] bg-[length:8.333%_100%]">
          {visits.map((v, i) => {
            const on = active.includes(v.date);
            const left = 6 + ((v.mjd - t0) / span) * 88;
            const canJump = frames.some((f) => f.kind !== 'diff_pair' && f.date_iso === v.date);
            return (
              <button key={v.date} type="button" disabled={!canJump} onClick={() => jump(v.date)}
                      aria-label={t('jump', { date: v.date, count: v.n })} aria-pressed={on} title={`${v.date} · ${v.n}`}
                      className="group absolute inset-y-0 w-6 -translate-x-1/2 disabled:cursor-default" style={{ left: `${left}%` }}>
                <span className={`absolute bottom-5 left-1/2 w-px -translate-x-1/2 ${on ? 'bg-sky-400' : 'bg-slate-300 group-hover:bg-white'}`}
                      style={{ height: `${18 + 34 * (v.n / maxN)}%` }} />
                <span className={`absolute bottom-5 left-1/2 h-1.5 w-1.5 -translate-x-1/2 translate-y-1/2 rounded-full ${on ? 'bg-sky-400' : 'bg-slate-300'}`} />
                {labelled(i, v) && (
                  <span className={`hud-value absolute bottom-0.5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] ${on ? 'text-sky-400!' : 'text-slate-400!'}`}>
                    {v.date.slice(0, 7)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
