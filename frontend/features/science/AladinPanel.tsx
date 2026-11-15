'use client';
// "Sky map" tab: the same patch of sky in other surveys (Aladin Lite v3 from CDS, Strasbourg), for context.
// The script is loaded only when the visitor asks for the map, so the viewer itself stays light.
// Ported from the teammate's panel. Developed with SI assistance (Claude); reviewed by team #1.
import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';

// The CDS address (aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js) answered 404 on 15 Nov 2026, so the
// official npm build is used, pinned. It is an ES module (default export), loaded through a module script below.
const ALADIN_JS = 'https://cdn.jsdelivr.net/npm/aladin-lite@3.8.2/dist/aladin.js';
// CDS short IDs need the CDS MocServer and alasky tiles, which answered 404 on 15 Nov 2026; IRSA mirrors AllWISE, 2MASS
// and DSS2, so full IRSA URLs are used. IRSA also hosts a SPHEREx DR1 all-sky HiPS cube (SPHEREx/spherex_allsky_cube),
// but Aladin Lite 3.8.2 requests a frame that does not exist for it (blank map), so it is not offered yet.
const IRSA_HIPS = 'https://irsa.ipac.caltech.edu/data/hips';
const SURVEYS = [
  { id: `${IRSA_HIPS}/CDS/AllWISE/RGB-W4-W2-W1`, key: 'allwise' },
  { id: `${IRSA_HIPS}/CDS/2MASS/Color`, key: 'twomass' },
  { id: `${IRSA_HIPS}/CDS/DSS2/color`, key: 'dss' },
] as const;

type AladinApi = { init?: Promise<unknown>; aladin: (el: HTMLElement, opts: Record<string, unknown>) => unknown };
declare global { interface Window { A?: AladinApi } }

let loading: Promise<AladinApi> | null = null;
function loadAladin(): Promise<AladinApi> {
  loading ??= new Promise<AladinApi>((resolve, reject) => {
    const ready = 'skyblink-aladin-ready';
    const failed = 'skyblink-aladin-failed';
    const done = () => {
      window.removeEventListener(ready, done);
      window.removeEventListener(failed, fail);
      const A = window.A;
      if (!A) return fail();
      Promise.resolve(A.init).then(() => resolve(A), fail);
    };
    const fail = () => {
      window.removeEventListener(ready, done);
      window.removeEventListener(failed, fail);
      loading = null;
      reject(new Error('aladin'));
    };
    window.addEventListener(ready, done);
    window.addEventListener(failed, fail);
    const s = document.createElement('script');
    s.type = 'module';
    s.textContent = `import("${ALADIN_JS}").then((m) => { window.A = m.default; dispatchEvent(new Event("${ready}")); },`
      + ` () => dispatchEvent(new Event("${failed}")));`;
    document.head.appendChild(s);
  });
  return loading;
}

export function AladinPanel() {
  const t = useTranslations('science.sky');
  const blink = useViewer((s) => s.blink);
  const box = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [survey, setSurvey] = useState<string>(SURVEYS[0].id);
  const [failed, setFailed] = useState(false);
  const ra = blink?.target.ra;
  const dec = blink?.target.dec;
  const fov = blink?.fov_arcsec;

  useEffect(() => {
    if (!open || ra === undefined || dec === undefined || !fov) return;
    let live = true;
    loadAladin().then((A) => {
      if (!live || !box.current) return;
      box.current.innerHTML = '';
      A.aladin(box.current, { survey, fov: (fov / 3600) * 2, target: `${ra} ${dec}`, showReticle: true,
                               showFullscreenControl: false, showLayersControl: false, showProjectionControl: false });
    }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [open, ra, dec, fov, survey]);

  if (ra === undefined || dec === undefined) return <p className="text-sm opacity-70">{t('needTarget')}</p>;
  if (!open) {
    return (
      <div className="flex flex-col items-start gap-2">
        <p className="text-sm opacity-80">{t('intro')}</p>
        <button type="button" onClick={() => { setFailed(false); setOpen(true); }}
                className="inline-flex h-9 items-center rounded-lg px-3 text-sm border border-slate-700 hover:border-sky-500/60 hover:text-white">
          {t('load')}
        </button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div role="group" aria-label={t('survey')} className="flex flex-wrap gap-1">
        {SURVEYS.map((s) => (
          <button key={s.id} type="button" aria-pressed={survey === s.id} onClick={() => { setFailed(false); setSurvey(s.id); }}
                  className={`h-8 rounded-lg px-2 text-xs border border-slate-700 ${survey === s.id ? 'border-sky-500/70 bg-sky-500/15 text-sky-600' : 'hover:border-sky-500/60 hover:text-white'}`}>
            {t(s.key)}
          </button>
        ))}
      </div>
      {failed ? <p role="alert" className="text-sm text-red-700">{t('failed')}</p>
        : <div ref={box} className="h-72 w-full overflow-hidden rounded-xl bg-black" />}
    </div>
  );
}
