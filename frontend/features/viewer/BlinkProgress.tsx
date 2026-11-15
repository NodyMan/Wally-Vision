'use client';
// What the player box shows when there are no frames to draw: loading progress, an error, or a hint.
// A cold request takes 1–2 minutes (COMMON §6), so the stage text tells people what is happening.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';

const STAGES = ['queued', 'search', 'download', 'stack', 'done'];

export function BlinkProgress() {
  const t = useTranslations();
  const job = useViewer((s) => s.job);
  const error = useViewer((s) => s.error);
  const target = useViewer((s) => s.target);

  if (error) {
    // errors.<code> belongs to #3; until it exists (or for an unknown code) show the generic text
    const key = `errors.${error}`;
    return (
      <Centered>
        <p role="alert" className="max-w-xs text-center text-sm text-red-300">
          {t.has(key) ? t(key) : t('viewer.state.error')}
        </p>
      </Centered>
    );
  }
  if (!target) {
    return <Centered><p className="max-w-xs text-center text-sm opacity-70">{t('viewer.state.empty')}</p></Centered>;
  }
  if (!job) return null;

  // stage is "search", "stack" or "download:24" (24 = number of images)
  const [name, count] = (job.stage ?? 'queued').split(':');
  const stage = STAGES.includes(name) ? name : 'queued';
  const percent = Math.round(Math.min(1, Math.max(0, job.progress)) * 100);
  const text = t(`viewer.stage.${stage}`, { count: Number(count) || 0 });

  return (
    <Centered>
      <div className="w-64 max-w-[80%]">
        <div role="progressbar" aria-label={t('viewer.progress.label')} aria-valuemin={0} aria-valuemax={100}
             aria-valuenow={percent} aria-valuetext={text}
             className="h-2 overflow-hidden rounded-full bg-neutral-700">
          <div className="h-full rounded-full bg-sky-400 transition-[width] duration-500 motion-reduce:transition-none"
               style={{ width: `${Math.max(percent, 3)}%` }} />
        </div>
        <p aria-live="polite" className="mt-3 text-center text-sm">{text}</p>
        <p className="mt-1 text-center text-xs tabular-nums opacity-60">{percent}%</p>
      </div>
    </Centered>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  // on the black image: light text regardless of the page theme
  return <div className="absolute inset-0 flex items-center justify-center p-4 text-neutral-100">{children}</div>;
}
