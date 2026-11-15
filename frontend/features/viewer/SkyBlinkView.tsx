'use client';
// The complete viewer: #1's player with #2's science layers and #3's platform pieces in the layout slots.
//   overlay      : catalog markers and proper-motion arrows (#2)
//   toolbarExtra : catalog switches (#2)
//   actions      : Share (#1), Embed and "I found something!" (#3)
//   bottomTabs   : What am I looking at? + tour (#3), Spectrum, Light curve, Sky map (#2)
// Developed with SI assistance (Claude); reviewed by team #1.
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Check, Share2 } from 'lucide-react';
import { ReportFindingButton } from '@/features/findings/ReportFindingButton';
import { WhatYouSeeTab } from '@/features/onboarding/WhatYouSeeTab';
import { AladinPanel } from '@/features/science/AladinPanel';
import { CatalogOverlay, useCatalogLoader } from '@/features/science/CatalogOverlay';
import { ScienceToolbar } from '@/features/science/ScienceToolbar';
import { LightCurvePanel, SpectrumPanel } from '@/features/science/SeriesPanels';
import { EmbedButton } from '@/features/settings/EmbedButton';
import type { PresetItem } from '@/lib/api/platform';
import presetsData from '@/lib/mocks/presets.json';
import { useViewer } from '@/lib/store';
import type { BottomTab } from './ViewerLayout';
import { ViewPage } from './ViewPage';

const PRESETS = presetsData as PresetItem[];
const NEAR_DEG = 0.01;   // the view centre is within 36 arcsec of a preset: it is that preset

function ShareButton() {
  const t = useTranslations('viewer.share');
  const [copied, setCopied] = useState(false);
  const share = async () => {
    const url = window.location.href;
    try {
      if (navigator.share && window.matchMedia('(pointer: coarse)').matches) {
        await navigator.share({ title: 'SkyBlink', url });
        return;
      }
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2200);
    } catch {
      // the share sheet was closed, or the clipboard is blocked: nothing to do
    }
  };
  return (
    <button type="button" onClick={share}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-sky-500/60 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400">
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
        : <Share2 className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />}
      <span aria-live="polite">{copied ? t('copied') : t('button')}</span>
    </button>
  );
}

export function SkyBlinkView() {
  useCatalogLoader();
  const target = useViewer((s) => s.target);
  const blink = useViewer((s) => s.blink);
  const selected = useViewer((s) => s.selected);
  const mode = useViewer((s) => s.mode);
  const fov = useViewer((s) => s.fov);

  const preset = target && PRESETS.find((p) => Math.abs(p.ra - target.ra) < NEAR_DEG && Math.abs(p.dec - target.dec) < NEAR_DEG);
  // a finding points at the clicked pixel, or at the target when nothing is clicked
  const at = selected ?? blink?.target ?? target;

  const tabs: BottomTab[] = [
    { key: 'what', labelKey: 'presets.whatYouSeeTitle',
      node: <WhatYouSeeTab presetSlug={preset?.slug} mode={mode} targetName={target?.name} autoOpenTour /> },
    { key: 'spectrum', labelKey: 'science.tabs.spectrum', node: <SpectrumPanel /> },
    { key: 'lightcurve', labelKey: 'science.tabs.lightcurve', node: <LightCurvePanel /> },
    { key: 'sky', labelKey: 'science.tabs.sky', node: <AladinPanel /> },
  ];

  return (
    <ViewPage
      overlay={(ctx) => <CatalogOverlay {...ctx} />}
      toolbarExtra={<ScienceToolbar />}
      actions={target && (
        <>
          <ShareButton />
          <EmbedButton ra={target.ra} dec={target.dec} fov={fov} mode={mode} name={target.name} />
          {at && (
            <ReportFindingButton key={`${at.ra.toFixed(5)}|${at.dec.toFixed(5)}`}
                                 defaultRa={Number(at.ra.toFixed(6))} defaultDec={Number(at.dec.toFixed(6))} />
          )}
        </>
      )}
      bottomTabs={tabs}
    />
  );
}
