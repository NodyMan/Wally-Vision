'use client';
// The frame of the viewer page with slots for #2 and #3 (contract: 00_COMMON.md §5).
//   desktop: [ player + playback controls ] [ side column: view settings, layers and actions ]
//   phone:   title, settings, player, controls, tabs — one column
// Developed with SI assistance (Claude); reviewed by team #1.
import { useRef, useState, type ReactNode } from 'react';
import { Activity, Globe, HelpCircle, LayoutGrid, Waves, type LucideIcon } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useViewer } from '@/lib/store';
import { ViewerStats } from './ViewerStats';

// How to draw over the frame (for #2's CatalogOverlay). The overlay box covers the player exactly.
// zoom = 1 fits the whole frame into the box; pan is the shift of the frame centre in CSS pixels.
// The simplest correct overlay is an SVG in frame pixels:
//   <svg viewBox={`-0.5 -0.5 ${sizePx.width} ${sizePx.height}`} className="h-full w-full"
//        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: 'center' }}>
// The -0.5 matters: an integer coordinate is the CENTRE of a pixel (COMMON §6), not its corner.
export interface OverlayContext {
  zoom: number;                          // 1..8, magnification relative to "whole frame fits the box"
  pan: { x: number; y: number };         // shift of the frame centre, CSS pixels
  sizePx: { width: number; height: number };  // frame size in SPHEREx pixels (grid.width/height)
}

export interface BottomTab {
  key: string;
  labelKey: string;                      // full i18n key, e.g. 'science.tabs.spectrum'
  node: ReactNode;
}

export interface ViewerLayoutProps {
  player: ReactNode;                                   // #1: BlinkPlayer (canvas)
  controls?: ReactNode;                                // #1: play/slider/zoom, shown under the canvas
  overlay?: (ctx: OverlayContext) => ReactNode;        // #2: SVG over the canvas (CatalogOverlay)
  toolbar?: ReactNode;                                 // #1: mode, band, field of view
  toolbarExtra?: ReactNode;                            // #2: catalog layers
  actions?: ReactNode;                                 // #3: share, embed, "I found something!"
  sidePanel?: ReactNode;                               // extra block at the bottom of the side column
  bottomTabs?: BottomTab[];                            // #3: "What am I looking at?"; #2: spectrum, light curve, sky map
  compact?: boolean;                                   // /embed: the player and its controls only
}

const CARD = 'card';

// icons of the navigation rail (left, desktop): one per bottom tab, plus "settings" for the side panel
const TAB_ICONS: Record<string, LucideIcon> = { what: HelpCircle, spectrum: Waves, lightcurve: Activity, sky: Globe };

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="hud-label">{title}</h2>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}

export function ViewerLayout({ player, controls, overlay, toolbar, toolbarExtra, actions, sidePanel,
                               bottomTabs = [], compact = false }: ViewerLayoutProps) {
  const t = useTranslations();
  const { zoom, pan, blink, target, mode } = useViewer();
  const [tab, setTab] = useState(bottomTabs[0]?.key);
  const tabsRef = useRef<HTMLElement>(null);
  const asideRef = useRef<HTMLElement>(null);
  const sizePx = { width: blink?.grid.width ?? 0, height: blink?.grid.height ?? 0 };
  const name = target?.name || blink?.target.name || (target ? t('viewer.title.unnamed') : t('viewer.title.empty'));
  const at = blink?.target ?? target;
  const openTab = (key: string) => {
    setTab(key);
    tabsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const stage = (
    <div className="flex min-w-0 flex-col gap-3">
      <section aria-label={t('viewer.player.label')}
               className="relative mx-auto aspect-square w-full max-w-[min(100%,74dvh)] overflow-hidden rounded-2xl bg-black shadow-xl shadow-slate-700/40">
        {player}
        {sizePx.width > 0 && (
          // which way is which on the sky: north up, east to the LEFT (as seen from inside the celestial sphere)
          <div role="img" aria-label={t('viewer.compass.label')}
               className="pointer-events-none absolute bottom-3 left-3 z-[1] h-12 w-12 text-[#7be36a]">
            <svg viewBox="0 0 48 48" className="h-full w-full" aria-hidden="true">
              <path d="M34 34 V10 M34 10 l-3.5 6 M34 10 l3.5 6 M34 34 H10 M10 34 l6 -3.5 M10 34 l6 3.5"
                    fill="none" stroke="currentColor" strokeWidth="1.5" />
              <text x="34" y="7" textAnchor="middle" fontSize="8" fill="currentColor">{t('viewer.compass.n')}</text>
              <text x="4" y="45" textAnchor="start" fontSize="8" fill="currentColor">{t('viewer.compass.e')}</text>
            </svg>
          </div>
        )}
        {overlay && sizePx.width > 0 && (
          <div className="pointer-events-none absolute inset-0">{overlay({ zoom, pan, sizePx })}</div>
        )}
      </section>
      {controls && <div className="mx-auto flex w-full max-w-[min(100%,74dvh)] flex-col gap-2">{controls}</div>}
    </div>
  );

  if (compact) return <div className="p-3">{stage}</div>;

  const rail = (
    <nav aria-label={t('viewer.rail.label')}
         className="card sticky top-24 hidden h-fit flex-col items-center gap-2 p-2 lg:flex">
      <button type="button" title={t('viewer.sections.view')} aria-label={t('viewer.sections.view')}
              onClick={() => asideRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500 text-slate-950">
        <LayoutGrid className="h-5 w-5" aria-hidden="true" />
      </button>
      {bottomTabs.map((b) => {
        const Icon = TAB_ICONS[b.key] ?? LayoutGrid;
        return (
          <button key={b.key} type="button" title={t(b.labelKey)} aria-label={t(b.labelKey)} onClick={() => openTab(b.key)}
                  className={`flex h-10 w-10 items-center justify-center rounded-xl border transition-colors ${
                    tab === b.key ? 'border-sky-300 bg-sky-950 text-sky-600' : 'border-slate-800 text-slate-400 hover:text-sky-600'}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
          </button>
        );
      })}
    </nav>
  );

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="hud-label">SPHEREx · {t(`viewer.mode.${mode}`)}</p>
          <h1 className="mt-1 truncate text-3xl font-light leading-tight tracking-tight text-white sm:text-5xl">{name}</h1>
          {at && (
            <p className="mt-1 text-sm text-slate-400 tabular-nums">
              RA {at.ra.toFixed(5)}° · Dec {at.dec.toFixed(5)}°{blink ? ` · ${Math.round(blink.fov_arcsec / 6) / 10}′` : ''}
            </p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </header>

      <ViewerStats />

      <div className="grid gap-5 lg:grid-cols-[3.5rem_minmax(0,1fr)_20rem]">
        {rail}
        <div className="order-2 lg:order-none">{stage}</div>

        <aside ref={asideRef} role="toolbar" aria-label={t('viewer.toolbar.label')} aria-orientation="vertical"
               className={`order-1 flex h-fit scroll-mt-24 flex-col gap-5 p-4 lg:order-none ${CARD}`}>
          {toolbar && <Section title={t('viewer.sections.view')}>{toolbar}</Section>}
          {toolbarExtra}
          {sidePanel && <div className="hidden lg:block">{sidePanel}</div>}
        </aside>
      </div>

      {/* on a phone the readout goes under the image, so the image is not pushed off the first screen */}
      {sidePanel && <div className={`p-4 lg:hidden ${CARD}`}>{sidePanel}</div>}

      {bottomTabs.length > 0 && (
        <section ref={tabsRef} className={`scroll-mt-24 ${CARD}`}>
          <div role="tablist" aria-label={t('viewer.tabs.label')}
               className="flex gap-1 overflow-x-auto border-b border-slate-800 p-2">
            {bottomTabs.map((b) => (
              <button key={b.key} type="button" role="tab" id={`tab-${b.key}`} aria-selected={tab === b.key}
                      aria-controls={`panel-${b.key}`} onClick={() => setTab(b.key)}
                      className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                        tab === b.key ? 'bg-sky-950 text-sky-600' : 'text-slate-400 hover:text-white'}`}>
                {t(b.labelKey)}
              </button>
            ))}
          </div>
          {bottomTabs.map((b) => (
            <div key={b.key} role="tabpanel" id={`panel-${b.key}`} aria-labelledby={`tab-${b.key}`}
                 hidden={tab !== b.key} className="p-5">
              {b.node}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

export { Section as ViewerSection };
