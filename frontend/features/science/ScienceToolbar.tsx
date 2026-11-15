'use client';
// Catalog switches for the `toolbarExtra` slot: Gaia, CatWISE, and how many years of motion the arrows show.
// Hidden in Simple mode (COMMON §5: everyone hides their own advanced controls).
// Developed with SI assistance (Claude); reviewed by team #1.
import { useTranslations } from 'next-intl';
import { isCandidate } from '@/lib/api/science';
import { useViewer } from '@/lib/store';
import { ViewerSection } from '@/features/viewer/ViewerLayout';
import { useCatalog } from './CatalogOverlay';

const YEARS = [1, 5, 10, 25];
const CHIP = 'flex h-9 flex-1 cursor-pointer items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-950 px-2.5 text-sm';

export function ScienceToolbar() {
  const t = useTranslations();
  const overlays = useViewer((s) => s.overlays);
  const setOverlays = useViewer((s) => s.setOverlays);
  const simpleMode = useViewer((s) => s.simpleMode);
  const blink = useViewer((s) => s.blink);
  const { data, loading, error } = useCatalog();
  if (simpleMode || !blink) return null;
  const on = overlays.gaia || overlays.catwise;
  const lone = data?.sources.filter(isCandidate).length ?? 0;

  return (
    <ViewerSection title={t('science.catalogs.label')}>
      <label className={CHIP}>
        <input type="checkbox" className="accent-cyan-400" checked={overlays.gaia}
               onChange={(e) => setOverlays({ gaia: e.target.checked })} />
        <span className="text-cyan-300">{t('science.catalogs.gaia')}</span>
      </label>
      <label className={CHIP}>
        <input type="checkbox" className="accent-amber-400" checked={overlays.catwise}
               onChange={(e) => setOverlays({ catwise: e.target.checked })} />
        <span className="text-amber-300">{t('science.catalogs.catwise')}</span>
      </label>
      {on && (
        <label className="flex w-full flex-col gap-1 text-xs text-slate-400">
          <span>{t('science.catalogs.years')}</span>
          <select value={overlays.pmYears} onChange={(e) => setOverlays({ pmYears: Number(e.target.value) })}
                  className="h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 text-sm text-slate-100">
            {YEARS.map((y) => <option key={y} value={y}>{t('science.catalogs.yearsValue', { years: y })}</option>)}
          </select>
        </label>
      )}
      {on && (
        <span aria-live="polite" className="w-full text-xs text-slate-400">
          {loading ? t('science.catalogs.loading')
            : error ? (t.has(`errors.${error}`) ? t(`errors.${error}`) : t('errors.server_error'))
            : data ? t('science.catalogs.count', { count: data.sources.length, lone }) : ''}
        </span>
      )}
    </ViewerSection>
  );
}
