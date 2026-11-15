"use client";

import { useLocale, useTranslations } from "next-intl";
import presetsData from "@/lib/mocks/presets.json";
import type { Locale } from "@/i18n/routing";
import type { PresetItem } from "@/lib/api/platform";
import { Tour } from "./Tour";

type WhatYouSeeTabProps = {
  presetSlug?: string | null;
  mode?: "frames" | "diff" | "sum";
  targetName?: string;
  autoOpenTour?: boolean; // /view opens the tour on a first visit
};

/**
 * Tab content for #1's ViewerLayout `bottomTabs` slot ("What am I looking at?").
 */
export function WhatYouSeeTab({
  presetSlug,
  mode = "frames",
  targetName,
  autoOpenTour = false,
}: WhatYouSeeTabProps) {
  const t = useTranslations("presets");
  const locale = useLocale() as Locale;

  const presets = presetsData as PresetItem[];
  const matchedPreset = presetSlug
    ? presets.find((p) => p.slug === presetSlug)
    : undefined;

  const explanation = matchedPreset
    ? matchedPreset.what_you_see[locale] || matchedPreset.what_you_see.en
    : t(`modeFallback.${mode}`);

  const heading = matchedPreset
    ? matchedPreset.title[locale] || matchedPreset.title.en
    : targetName || t("whatYouSeeTitle");

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-xs font-medium uppercase tracking-wider text-sky-400">
            {t("whatYouSeeTitle")}
          </span>
          <h3 className="mt-0.5 text-base font-semibold text-white">{heading}</h3>
        </div>
        <Tour autoOpen={autoOpenTour} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{explanation}</p>
    </div>
  );
}
