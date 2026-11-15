'use client';
// Загружает blink для текущих target/fov/detector/mode, обновляет job (прогресс) и blink в сторе.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useEffect } from 'react';
import { ApiError, fetchBlink } from '@/lib/api/viewer';
import { useViewer } from '@/lib/store';

export function useBlink(): void {
  const { target, fov, detector, mode, setBlink, setJob, setError } = useViewer();

  useEffect(() => {
    if (!target) return;
    const ctrl = new AbortController();
    setJob({ status: 'queued', progress: 0, stage: 'search' });
    fetchBlink({ ra: target.ra, dec: target.dec, name: target.name, fov, detector, mode },
      (job) => setJob({ status: job.status, progress: job.progress, stage: job.stage }), ctrl.signal)
      .then(setBlink)
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setError(e instanceof ApiError ? e.code : 'server_error');
      });
    return () => ctrl.abort();
  }, [target, fov, detector, mode, setBlink, setJob, setError]);
}
