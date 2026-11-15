'use client';
// Catalog sources drawn over the frame (the `overlay` slot of ViewerLayout): Gaia DR3 (visible light) and
// CatWISE2020 (infrared), each at its position for the SPHEREx epoch, with an arrow showing where its
// proper motion takes it in `pmYears` years. An infrared source that clearly moves and has no Gaia match
// gets a dashed ring: worth a look, NOT a discovery (COMMON §13). Faint infrared sources without a Gaia
// match are common (Gaia does not go that deep), so "no match" alone is not marked.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useEffect, useState } from 'react';
import { fetchCatalog, isCandidate, type CatalogResponse, type CatalogSource } from '@/lib/api/science';
import { ApiError } from '@/lib/api/viewer';
import { useViewer } from '@/lib/store';
import type { OverlayContext } from '@/features/viewer/ViewerLayout';
import { create } from 'zustand';

interface CatalogState { data: CatalogResponse | null; loading: boolean; error: string | null }
/** Shared so that the toolbar can show "loading" / "unavailable" next to the switches. */
export const useCatalog = create<CatalogState>(() => ({ data: null, loading: false, error: null }));

const COLORS = { gaia: '#22d3ee', catwise: '#f5b94f' } as const;
const MIN_ARROW_PX = 0.4;   // shorter arrows are noise at 6.15″ per pixel

/** Loads the catalog for the field on screen once a catalog layer is switched on. */
export function useCatalogLoader(): void {
  const blink = useViewer((s) => s.blink);
  const on = useViewer((s) => s.overlays.gaia || s.overlays.catwise);
  const ra = blink?.grid.wcs_header.CRVAL1;
  const dec = blink?.grid.wcs_header.CRVAL2;
  const fov = blink?.fov_arcsec;
  const gridId = blink?.grid.id;

  useEffect(() => {
    if (!on || typeof ra !== 'number' || typeof dec !== 'number' || !fov) {
      useCatalog.setState({ data: null, loading: false, error: null });
      return;
    }
    let live = true;
    useCatalog.setState({ data: null, loading: true, error: null });
    fetchCatalog(ra, dec, fov).then((data) => {
      if (!live) return;
      // a different grid would put every marker in the wrong place: better no overlay than a wrong one
      if (data.grid_id !== gridId) useCatalog.setState({ data: null, loading: false, error: 'catalog_unavailable' });
      else useCatalog.setState({ data, loading: false, error: null });
    }).catch((e: unknown) => {
      if (live) useCatalog.setState({ data: null, loading: false, error: e instanceof ApiError ? e.code : 'server_error' });
    });
    return () => { live = false; };
  }, [on, ra, dec, fov, gridId]);
}

function Source({ s, years }: { s: CatalogSource; years: number }) {
  const color = COLORS[s.catalog];
  const dx = s.dx_per_yr * years;
  const dy = s.dy_per_yr * years;
  const moves = Math.hypot(dx, dy) >= MIN_ARROW_PX;
  const lone = isCandidate(s);
  return (
    <g>
      <circle cx={s.x} cy={s.y} r={s.catalog === 'gaia' ? 0.45 : 0.75} fill="none" stroke={color} strokeWidth="1.25" opacity="0.9"
              vectorEffect="non-scaling-stroke" />
      {lone && <circle cx={s.x} cy={s.y} r={2.2} fill="none" stroke={color} strokeWidth="1.5" strokeDasharray="3 3"
                       vectorEffect="non-scaling-stroke" />}
      {moves && <line x1={s.x} y1={s.y} x2={s.x + dx} y2={s.y + dy} stroke={color} strokeWidth="2"
                      vectorEffect="non-scaling-stroke" markerEnd={`url(#arrow-${s.catalog})`} />}
    </g>
  );
}

export function CatalogOverlay({ zoom, pan, sizePx }: OverlayContext) {
  const overlays = useViewer((s) => s.overlays);
  const data = useCatalog((s) => s.data);
  const [uid] = useState(() => Math.random().toString(36).slice(2, 8));
  if (!data || (!overlays.gaia && !overlays.catwise)) return null;
  const shown = data.sources.filter((s) => (s.catalog === 'gaia' ? overlays.gaia : overlays.catwise));

  return (
    <svg viewBox={`-0.5 -0.5 ${sizePx.width} ${sizePx.height}`} className="h-full w-full" aria-hidden="true"
         style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: 'center' }}>
      <defs>
        {(['gaia', 'catwise'] as const).map((c) => (
          <marker key={c} id={`arrow-${c}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5"
                  orient="auto-start-reverse">
            <path d="M0 1 L9 5 L0 9 z" fill={COLORS[c]} />
          </marker>
        ))}
      </defs>
      <g data-uid={uid}>
        {shown.map((s) => <Source key={s.id} s={s} years={overlays.pmYears} />)}
      </g>
    </svg>
  );
}
